from streamlit_autorefresh import st_autorefresh
import os
import pickle
import requests
import streamlit as st
import pandas as pd
from datetime import datetime
import pytz

tz = pytz.timezone('US/Pacific')

# Initialize session state
if 'data' not in st.session_state:
    try:
        with open("commute_data.pkl", "rb") as f:
            data = pickle.load(f)
        # Ensure timezone-aware timestamps
        for entry in data:
            if entry['timestamp'].tzinfo is None:
                entry['timestamp'] = entry['timestamp'].replace(tzinfo=tz)
        st.session_state['data'] = data
    except (FileNotFoundError, EOFError, pickle.UnpicklingError):
        st.session_state['data'] = []

if 'last_updated' not in st.session_state and st.session_state['data']:
    last_ts = st.session_state['data'][-1]['timestamp']
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=tz)
    st.session_state['last_updated'] = last_ts

# Configuration (non-editable)
api_key = st.secrets["GOOGLE_MAPS_API_KEY"]
source_address = st.secrets["SOURCE_ADDRESS"]
destination_address = st.secrets["DESTINATION_ADDRESS"]
refresh_interval = 300 # Configurable refresh interval in seconds (5 minutes)
# Tracking window hours (24h format)
morning_start, morning_end = 8, 11
# Tracking window hours (24h format)
evening_start, evening_end = 16, 19
# Helper to format hours into 12h with suffix
def _12h_format(hour: int) -> str:
    # Normalize 24 to 0 for correct midnight handling
    hour = hour % 24
    suffix = "AM" if hour < 12 else "PM"
    h12 = hour % 12
    if h12 == 0:
        h12 = 12
    return f"{h12} {suffix}"

# Formatted window labels
morning_label = f"{_12h_format(morning_start)}–{_12h_format(morning_end)}"
evening_label = f"{_12h_format(evening_start)}–{_12h_format(evening_end)}"

# Validate configuration
if not api_key or not source_address or not destination_address:
    st.warning("Missing configuration. Please check your API key and route settings.")
    st.stop()

# Determine tracking window and set source/destination accordingly
now = datetime.now(tz)
if morning_start <= now.hour < morning_end:
    # Morning window: Home → Office
    source = source_address
    destination = destination_address
    source_label, destination_label = "🏠 Home", "🏢 Office"
    is_tracking = True
elif evening_start <= now.hour < evening_end:
    # Evening window: Office → Home
    source = destination_address
    destination = source_address
    source_label, destination_label = "🏢 Office", "🏠 Home"
    is_tracking = True
else:
    # Outside tracking hours
    source = source_address
    destination = destination_address
    source_label, destination_label = "🏠 Home", "🏢 Office"
    is_tracking = False

# Main App
st.title("⏱ What's My Commute 🚗📍")
# Display most recent travel time at the top
today = datetime.now(tz).date()
filtered_data = [entry for entry in st.session_state['data'] if entry['timestamp'].date() == today]
latest_entry = max(filtered_data, key=lambda x: x['timestamp']) if filtered_data else None

def get_travel_time():
    now = datetime.now(tz)
    print(f"[{now}] Calling Google Routes API for travel time from '{source}' to '{destination}'")
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters"
    }
    payload = {
        "origin": {
            "address": source
        },
        "destination": {
            "address": destination
        },
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE"
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    duration_seconds = int(data['routes'][0]['duration'].rstrip('s'))
    duration_text = f"{duration_seconds // 60} min"

    st.session_state['data'].append({"timestamp": now, "duration": duration_text})
    st.session_state['last_updated'] = now
    with open("commute_data.pkl", "wb") as f:
        pickle.dump(st.session_state['data'], f)

# Handle case when no data is available yet
if latest_entry is None:
    if is_tracking:
        # Fetch first data immediately and rerun to display it
        get_travel_time()
        st.rerun()
    else:
        st.info(f"⏱ Commute tracking is active only between {morning_label} and {evening_label}. Refresh occurs every {refresh_interval // 60} minutes during these windows.")

if latest_entry:
    st.success(f"🟢 Most recent travel time: **{latest_entry['duration']}** at {latest_entry['timestamp'].strftime('%I:%M %p')}")

    if is_tracking:
        st_autorefresh(interval=refresh_interval*1000, key="datarefresh")
        st.info(f"🕑 Tracking active: Current route {source_label} → {destination_label}")

        # Check refresh interval before fetching data
        if 'last_updated' not in st.session_state:
            get_travel_time()
            st.rerun()
        else:
            time_since_last = (datetime.now(tz) - st.session_state['last_updated']).total_seconds()
            if time_since_last > refresh_interval:
                get_travel_time()
                st.rerun()
            else:
                st.info(f"⚡ Using cached data. 🔄 Next refresh in {int(refresh_interval - time_since_last)} seconds ⏳")

        # Filter data to include only today's entries
        today = datetime.now(tz).date()
        filtered_data = [entry for entry in st.session_state['data'] if entry['timestamp'].date() == today]

        # Ensure each entry has a route key
        for entry in filtered_data:
            if "route" not in entry:
                entry["route"] = f"{source_label} → {destination_label}"

        # Display the filtered data in a table
        if filtered_data:
            df = pd.DataFrame(filtered_data)
            df.rename(columns={"timestamp": "Time", "duration": "Duration", "route": "Route"}, inplace=True)
            df = df[["Route"] + [col for col in df.columns if col != "Route"]]
            df.sort_values(by="Time", ascending=False, inplace=True)
            df["Time"] = df["Time"].dt.strftime("%B %d, %Y %I:%M %p")
            # Show "Last updated at" above the table
            if 'last_updated' in st.session_state:
                last_updated = st.session_state['last_updated'].strftime("%B %d, %Y %I:%M %p")
                st.markdown(f"**Last updated at:** {last_updated}")
            st.dataframe(df, hide_index=True)
        else:
            st.info("No travel time data available for today.")
    else:
        st.info(f"⏱ Commute tracking is active only between {morning_label} and {evening_label}. Refresh occurs every {refresh_interval // 60} minutes during these windows.")

from importlib.util import source_hash

import streamlit as st
import googlemaps
import pandas as pd
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import os
import pickle

# Initialize session state
if 'data' not in st.session_state:
    if os.path.exists("commute_data.pkl"):
        with open("commute_data.pkl", "rb") as f:
            st.session_state['data'] = pickle.load(f)
        for entry in st.session_state['data']:
            if entry['timestamp'].tzinfo is None:
                entry['timestamp'] = entry['timestamp'].replace(tzinfo=pytz.timezone('US/Pacific'))
    else:
        st.session_state['data'] = []

if 'last_updated' not in st.session_state and st.session_state['data']:
    last_ts = st.session_state['data'][-1]['timestamp']
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=pytz.timezone('US/Pacific'))
    st.session_state['last_updated'] = last_ts

# Configuration (non-editable)
api_key = st.secrets["GOOGLE_MAPS_API_KEY"]
source_address = st.secrets["SOURCE_ADDRESS"]
destination_address = st.secrets["DESTINATION_ADDRESS"]
refresh_interval = 300  # Configurable refresh interval in seconds

# Swap source and destination if it's past 2 PM
now = datetime.now(pytz.timezone('US/Pacific'))
if now.hour >= 14:
    source_address, destination_address = destination_address, source_address
    source_label, destination_label = "🏢 Office", "🏠 Home"
else:
    source_label, destination_label = "🏠 Home", "🏢 Office"

# Static source and destination assignment
source = source_address
destination = destination_address

# Main App
st.title("⏱ What's My Commute 🚗📍")
# Display most recent travel time at the top
today = datetime.now(pytz.timezone('US/Pacific')).date()
filtered_data = [entry for entry in st.session_state['data'] if entry['timestamp'].date() == today]
latest_entry = max(filtered_data, key=lambda x: x['timestamp']) if filtered_data else None
if latest_entry:
    st.success(f"🟢 Most recent travel time: **{latest_entry['duration']}** at {latest_entry['timestamp'].strftime('%I:%M %p')}")
st_autorefresh(interval=refresh_interval*1000, key="datarefresh")
st.info(f"🕑 Note: After 2 PM, the source and destination are automatically swapped 🔄\n\nCurrent route: {source_label} → {destination_label}")

# Set up Google Maps client
if api_key and source and destination:
    gmaps = googlemaps.Client(key=api_key)

    def get_travel_time():
        now = datetime.now(pytz.timezone('US/Pacific'))
        print(f"[{now}] Calling Google Maps API for travel time from '{source}' to '{destination}'")
        directions = gmaps.directions(source, destination, mode="driving", departure_time=now)
        duration = directions[0]['legs'][0]['duration']['text']
        st.session_state['data'].append({"timestamp": now, "duration": duration})
        st.session_state['last_updated'] = now
        with open("commute_data.pkl", "wb") as f:
            pickle.dump(st.session_state['data'], f)

    # Check refresh interval before fetching data
    if 'last_updated' not in st.session_state:
        get_travel_time()
        st.rerun()
    else:
        time_since_last = (datetime.now(pytz.timezone('US/Pacific')) - st.session_state['last_updated']).total_seconds()
        if time_since_last > refresh_interval:
            get_travel_time()
            st.rerun()
        else:
            st.info(f"⚡ Using cached data. 🔄 Next refresh in {int(refresh_interval - time_since_last)} seconds ⏳")

    # Filter data to include only today's entries
    today = datetime.now(pytz.timezone('US/Pacific')).date()
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
    st.warning("Missing configuration. Please check your API key and route settings.")
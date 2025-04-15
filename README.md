# 🚗 What's My Commute

A simple Streamlit dashboard that uses the Google Maps API to track your daily commute time between two fixed addresses. It auto-refreshes every 5 minutes and stores historical data locally.

## 📦 Features

- Automatically switches origin and destination after 2 PM (to simulate commute back home).
- Displays the most recent travel time.
- Maintains a daily history of commute durations.
- Uses Google Maps Directions API.
- Refreshes automatically at a configurable interval.
- Stores data locally in a pickle file.

## 🏁 Requirements

- Python 3.7+
- A valid Google Maps API Key
- Streamlit
- Pandas
- streamlit-autorefresh
- googlemaps

## 🛠️ Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/whats-my-commute.git
   cd whats-my-commute
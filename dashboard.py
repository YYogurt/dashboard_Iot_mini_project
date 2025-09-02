import streamlit as st
import time
from pymongo import MongoClient
import os

MONGO_CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING")
MONGO_DB_NAME = "smartgarden"
MONGO_COLLECTION_NAME = "status"
DEVICE_ID = "main_status"

@st.cache_resource
def get_mongo_collection():
    if not MONGO_CONNECTION_STRING: return None
    try:
        mongo_client = MongoClient(MONGO_CONNECTION_STRING)
        return mongo_client[MONGO_DB_NAME][MONGO_COLLECTION_NAME]
    except Exception: return None

collection = get_mongo_collection()

def send_command_to_db(command_str: str):
    if collection is not None:
        collection.update_one({"_id": DEVICE_ID}, {"$set": {"command": command_str}})
        st.toast(f"Sent '{command_str}' command!")

st.set_page_config(page_title="IoT Smart Garden", layout="wide")
st.title("🌿 IoT Smart Garden Dashboard")

if collection is None:
    st.error("Database connection is not available.")
else:
    data = collection.find_one({"_id": DEVICE_ID})
    if data is None: data = {}
    
    video_stream_url = data.get("video_stream_url")

    left_col, right_col = st.columns([2, 1.5])
    with left_col:
        st.subheader("📊 System Status & Sensors")
        st.metric(label="Database Connection", value="🟢 Connected")
        st.write("---")
        city = data.get('city', 'N/A')
        st.write(f"**📍 Daily Forecast for {city}**")
        forecast_desc = data.get('forecast_description', 'No forecast available.')
        st.info(f"🌦️ {forecast_desc}")
        st.write("---")
        st.write("**📡 Live Sensor Data**")
        s1, s2, s3 = st.columns(3)
        s1.metric("🌡️ Air Temp", f"{data.get('air_temp', 0):.2f} °C")
        s1.metric("💧 Air Humidity", f"{data.get('air_humidity', 0):.2f} %")
        s2.metric("☀️ Light", f"{data.get('light_lux', 0):.2f} Lux")
        s2.metric("🌱 Soil", f"{data.get('soil_moisture', 0)} (raw)")
        s3.metric("🌊 Water", f"{data.get('water_level', 0)} (raw)")
        
    with right_col:
        st.subheader("📹 Live Feed & Control")
        if video_stream_url: st.image(video_stream_url, width=480)
        else: st.warning("Video stream URL not available in DB. Is the Pi running?")
        finger_count = data.get('finger_count', 'N/A')
        st.write(f"### 🖐️ Detected Fingers: {finger_count}")
        st.info("Show 2 fingers to toggle modes. Show 5 to force water.")
        st.write("---")
        system_mode = data.get('mode', 'N/A').upper()
        st.header(f"Mode: {system_mode}")
        if st.button("Toggle Mode"): send_command_to_db("TOGGLE_MODE")
        pump_status_text = "ON 🟢" if data.get("pump_on") else "OFF 🔴"
        st.write(f"### Pump Status: {pump_status_text}")
        st.write("**Manual Control (Only in MANUAL mode)**")
        btn_c1, btn_c2 = st.columns(2)
        is_manual_mode = (data.get('mode') == 'manual')
        if btn_c1.button("Turn Pump ON", disabled=not is_manual_mode): send_command_to_db("PUMP_ON")
        if btn_c2.button("Turn Pump OFF", disabled=not is_manual_mode): send_command_to_db("PUMP_OFF")
    time.sleep(2)
    st.rerun()
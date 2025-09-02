# dashboard.py (MongoDB Version - เพิ่ม Water Level)
import streamlit as st
import time
from pymongo import MongoClient
import os

# --- Configuration ---
MONGO_CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING")
MONGO_DB_NAME = "smartgarden"
MONGO_COLLECTION_NAME = "status"
PI_IP_ADDRESS = os.environ.get("PI_IP_ADDRESS")
VIDEO_STREAM_URL = f"http://{PI_IP_ADDRESS}:8080/video_feed" if PI_IP_ADDRESS else None

# --- MongoDB Connection ---
@st.cache_resource
def get_mongo_collection():
    if not MONGO_CONNECTION_STRING:
        st.error("MONGO_CONNECTION_STRING secret is not set!")
        return None
    try:
        mongo_client = MongoClient(MONGO_CONNECTION_STRING)
        db = mongo_client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        mongo_client.admin.command('ping')
        print("MongoDB connection successful.")
        return collection
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {e}")
        return None

collection = get_mongo_collection()

def send_command_to_db(command_str: str):
    if collection is not None:
        collection.update_one({"_id": "main_status"}, {"$set": {"command": command_str}})
        st.toast(f"Sent '{command_str}' command!")

# --- Main App ---
st.set_page_config(page_title="IoT Smart Garden", layout="wide")
st.title("🌿 IoT Smart Garden (MongoDB)")

if collection is None:
    st.error("Database connection is not available. Please check the secrets and app logs.")
else:
    data = collection.find_one({"_id": "main_status"})
    if data is None:
        data = {}

    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("Sensor Readings & Status")
        status_indicator = "🟢 Connected to DB" if data else "🟠 Connected, No Data Yet"
        st.metric(label="Database Connection", value=status_indicator)
        st.write("---")

        # --- ✨ แก้ไขส่วนนี้ ✨ ---
        s1, s2, s3 = st.columns(3)
        s1.metric("🌡️ Air Temperature", f"{data.get('air_temp', 0):.2f} °C")
        s1.metric("💧 Air Humidity", f"{data.get('air_humidity', 0):.2f} %")
        s2.metric("☀️ Light Intensity", f"{data.get('light_lux', 0):.2f} Lux")
        s2.metric("🌱 Soil Moisture", f"{data.get('soil_moisture', 0)} (raw)")
        s3.metric("🌊 Water Level", f"{data.get('water_level', 0)} (raw)")
        # ------------------------
        
        st.write("---")

        system_mode = data.get('mode', 'N/A').upper()
        st.header(f"Mode: {system_mode}")
        pump_status_text = "ON 🟢" if data.get("pump_on") else "OFF 🔴"
        st.write(f"### Pump Status: {pump_status_text}")

        st.write("**Manual Control (Only in MANUAL mode)**")
        btn_c1, btn_c2 = st.columns(2)
        is_manual_mode = (data.get('mode') == 'manual')

        if btn_c1.button("Turn Pump ON", key="pump_on", disabled=not is_manual_mode):
            send_command_to_db("PUMP_ON")

        if btn_c2.button("Turn Pump OFF", key="pump_off", disabled=not is_manual_mode):
            send_command_to_db("PUMP_OFF")

    with right_col:
        st.subheader("Live Feed")
        if VIDEO_STREAM_URL:
            st.image(VIDEO_STREAM_URL, caption="Live Feed (Viewable on same network)")
        else:
            st.warning("PI_IP_ADDRESS secret not set, video stream is disabled.")

    # Auto-refresh the page
    time.sleep(3)
    st.rerun()
# dashboard.py (Final Layout Version)
import streamlit as st
import time
from pymongo import MongoClient
import os

# --- Configuration ---
MONGO_CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING")
MONGO_DB_NAME = "smartgarden"
MONGO_COLLECTION_NAME = "status"
STREAM_HOST = os.environ.get("STREAM_HOST")
VIDEO_STREAM_URL = None

if STREAM_HOST:
    if "ngrok-free.app" in STREAM_HOST:
        VIDEO_STREAM_URL = f"https://{STREAM_HOST}/video_feed"
    else:
        VIDEO_STREAM_URL = f"http://{STREAM_HOST}:8080/video_feed"

# --- MongoDB Connection ---
@st.cache_resource
def get_mongo_collection():
    if not MONGO_CONNECTION_STRING: return None
    try:
        mongo_client = MongoClient(MONGO_CONNECTION_STRING)
        mongo_client.admin.command('ping')
        return mongo_client[MONGO_DB_NAME][MONGO_COLLECTION_NAME]
    except Exception: return None

collection = get_mongo_collection()

def send_command_to_db(command_str: str):
    if collection is not None:
        collection.update_one({"_id": "main_status"}, {"$set": {"command": command_str}})
        st.toast(f"Sent '{command_str}' command!")

# --- Main App ---
st.set_page_config(page_title="IoT Smart Garden", layout="wide")
st.title("🌿 IoT Smart Garden Dashboard")

if collection is None:
    st.error("Database connection is not available.")
else:
    data = collection.find_one({"_id": "main_status"})
    if data is None: data = {}

    # --- ✨ จัด Layout ใหม่ทั้งหมด ✨ ---
    left_col, right_col = st.columns([2, 1.5]) # ให้คอลัมน์ซ้ายใหญ่กว่าขวาเล็กน้อย

    # --- คอลัมน์ซ้าย: แสดงผลข้อมูลทั้งหมด ---
    with left_col:
        st.subheader("📊 System Status & Sensors")
        
        # --- สถานะการเชื่อมต่อ ---
        status_indicator = "🟢 Connected to DB" if data else "🟠 Connected, No Data Yet"
        st.metric(label="Database Connection", value=status_indicator)
        st.write("---")

        # --- พยากรณ์อากาศ ---
        city = data.get('city', 'N/A')
        st.write(f"**📍 Daily Forecast for {city}**")
        forecast_desc = data.get('forecast_description', 'No forecast available.')
        st.info(f"🌦️ {forecast_desc}")
        st.write("---")

        # --- ข้อมูลเซ็นเซอร์สด ---
        st.write("**📡 Live Sensor Data**")
        s1, s2, s3 = st.columns(3)
        s1.metric("🌡️ Air Temp", f"{data.get('air_temp', 0):.2f} °C")
        s1.metric("💧 Air Humidity", f"{data.get('air_humidity', 0):.2f} %")
        s2.metric("☀️ Light", f"{data.get('light_lux', 0):.2f} Lux")
        s2.metric("🌱 Soil", f"{data.get('soil_moisture', 0)} (raw)")
        s3.metric("🌊 Water", f"{data.get('water_level', 0)} (raw)")
        
    # --- คอลัมน์ขวา: กล้องและส่วนควบคุม ---
    with right_col:
        st.subheader("📹 Live Feed & Control")

        # --- แสดงวิดีโอ (กำหนดความกว้าง) ---
        if VIDEO_STREAM_URL:
            st.image(VIDEO_STREAM_URL, caption="Live Feed", width=480) # ย่อขนาดวิดีโอ
        else:
            st.warning("STREAM_HOST secret not set.")

        # --- ✨ แสดงจำนวนนิ้วที่ตรวจจับได้ ✨ ---
        finger_count = data.get('finger_count', 'N/A')
        st.write(f"### 🖐️ Detected Fingers: {finger_count}")
        st.info("Show 2 fingers to toggle modes.")
        st.write("---")

        # --- ✨ ย้ายส่วนควบคุมมาไว้ตรงนี้ ✨ ---
        system_mode = data.get('mode', 'N/A').upper()
        st.header(f"Mode: {system_mode}")
        
        pump_status_text = "ON 🟢" if data.get("pump_on") else "OFF 🔴"
        st.write(f"### Pump Status: {pump_status_text}")
        
        st.write("**Manual Control (Only in MANUAL mode)**")
        btn_c1, btn_c2 = st.columns(2)
        is_manual_mode = (data.get('mode') == 'manual')
        if btn_c1.button("Turn Pump ON", disabled=not is_manual_mode): send_command_to_db("PUMP_ON")
        if btn_c2.button("Turn Pump OFF", disabled=not is_manual_mode): send_command_to_db("PUMP_OFF")

    # Auto-refresh
    time.sleep(3)
    st.rerun()
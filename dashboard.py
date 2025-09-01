# โค้ดสำหรับ Dashboard ที่จะ Deploy ขึ้น Streamlit Cloud
# ภาษา: Python (ใช้ไลบรารี Streamlit)

import streamlit as st
import json
import time
import paho.mqtt.client as mqtt
import os

# --- Configuration ---
# !!! สำคัญ: ค่าเหล่านี้จะถูกดึงมาจาก Secrets บน Streamlit Cloud
MQTT_BROKER = os.environ.get("MQTT_BROKER")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
PI_IP_ADDRESS = os.environ.get("PI_IP_ADDRESS")
MQTT_TOPIC_COMMANDS = "onigiri/smartgarden/dashboard/commands"
MQTT_TOPIC_SENSORS = "onigiri/smartgarden/esp32/sensors"
# วิดีโอสตรีมจะยังคงต้องใช้ IP ของ Pi ซึ่งหมายความว่าต้องดูจากในเครือข่ายเดียวกัน
VIDEO_STREAM_URL = f"http://{PI_IP_ADDRESS}:8080/video_feed" if PI_IP_ADDRESS else None

# --- Functions ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Dashboard connected to MQTT Broker!")
        # Subscribe เพื่อรับข้อมูลสถานะล่าสุดจาก ESP32
        client.subscribe(MQTT_TOPIC_SENSORS)
        st.session_state.mqtt_connected = True
    else:
        print(f"Dashboard failed to connect, return code {rc}")
        st.session_state.mqtt_connected = False

def on_message(client, userdata, msg):
    # เมื่อมีข้อความใหม่เข้ามา ให้อัปเดตข้อมูลล่าสุดใน session_state
    try:
        payload = msg.payload.decode()
        print(f"Dashboard received message: {payload}")
        data = json.loads(payload)
        st.session_state.latest_data.update(data)
    except Exception as e:
        print(f"Error processing message in dashboard: {e}")

def format_metric(value, unit=""):
    return f"{value:.1f}{unit}" if isinstance(value, (int, float)) else "N/A"

# --- Main App ---
st.set_page_config(layout="wide", page_title="Smart Garden")
st.title("🌿 IoT Smart Garden Dashboard")

# --- Initialize Session State ---
if 'mqtt_client' not in st.session_state:
    st.session_state.mqtt_client = None
    st.session_state.mqtt_connected = False
    st.session_state.latest_data = {}

# --- Connect to MQTT ---
if not st.session_state.mqtt_client and MQTT_BROKER:
    st.session_state.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    st.session_state.mqtt_client.on_connect = on_connect
    st.session_state.mqtt_client.on_message = on_message
    try:
        st.session_state.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        st.session_state.mqtt_client.loop_start()
    except Exception as e:
        st.error(f"Could not connect to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}. Error: {e}")
        st.warning("Dashboard control features will be disabled. Please ensure ngrok is running and secrets are set correctly.")

# --- UI Layout ---
data = st.session_state.latest_data

st.subheader("Sensor Readings (Real-time)")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("💧 Soil Moisture", format_metric(data.get("soil_moisture")))
col2.metric("🌊 Water Level", format_metric(data.get("water_level")))
col3.metric("🌡️ Temperature", format_metric(data.get("temperature"), " °C"))
col4.metric("💧 Air Humidity", format_metric(data.get("humidity"), " %"))
col5.metric("💡 Light", format_metric(data.get("light_intensity"), " lux"))

st.write("---")
left_col, right_col = st.columns([2, 3])
with left_col:
    st.subheader("System Control & Status")
    if not st.session_state.get('mqtt_connected'): st.error("Disconnected from control system.")
    system_mode = data.get('mode', 'N/A').upper()
    st.header(f"Mode: {system_mode}")
    pump_status_text = "ON 🟢" if data.get("pump_on") else "OFF 🔴"
    st.write(f"### Pump Status: {pump_status_text}")
    st.write("**Manual Control (Only in MANUAL mode)**")
    btn_c1, btn_c2 = st.columns(2)
    is_manual_mode = (data.get('mode') == 'manual')
    disable_buttons = not st.session_state.get('mqtt_connected') or not is_manual_mode
    if btn_c1.button("Turn Pump ON", key="pump_on", disabled=disable_buttons):
        st.session_state.mqtt_client.publish(MQTT_TOPIC_COMMANDS_DASHBOARD, "PUMP_ON")
        st.toast("Sent 'Pump ON' command!")
    if btn_c2.button("Turn Pump OFF", key="pump_off", disabled=disable_buttons):
        st.session_state.mqtt_client.publish(MQTT_TOPIC_COMMANDS_DASHBOARD, "PUMP_OFF")
        st.toast("Sent 'Pump OFF' command!")
    st.info("🖐️ Show 2 fingers to the camera to toggle between AUTO and MANUAL modes.")
    st.write("---")
    st.subheader("Security")
    last_motion = data.get("last_motion_time", "None")
    st.write(f"**Last Motion Detected:** {last_motion}")
with right_col:
    st.subheader("Live Feed")
    if VIDEO_STREAM_URL:
        st.image(VIDEO_STREAM_URL, caption="Live Camera Feed (requires being on the same network as the Pi)")
    else:
        st.warning("PI_IP_ADDRESS secret not set. Live feed is unavailable.")
    st.caption(f"Detected Fingers: **{data.get('finger_count', 'N/A')}**")

# Since on_message updates state, we need to rerun to show the changes
time.sleep(1) 
st.rerun()

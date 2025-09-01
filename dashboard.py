# dashboard.py (เวอร์ชันทดสอบสุดท้ายกับ HiveMQ)
import streamlit as st
import json
import time
import paho.mqtt.client as mqtt
import os

# --- Configuration ---
# --- ✨ การเปลี่ยนแปลงสำคัญ ✨ ---
# ไม่ต้องใช้ Secrets แล้ว กำหนดค่าโดยตรงเพื่อทดสอบ
MQTT_BROKER = "broker.hivemq.com"
# Port สำหรับ WebSockets ของ HiveMQ คือ 8000
MQTT_PORT = 8000
PI_IP_ADDRESS = os.environ.get("PI_IP_ADDRESS") # ยังใช้ Secrets สำหรับวิดีโอได้

# แก้ไข Topic ให้ตรงกับ main_app.py
MQTT_TOPIC_COMMANDS_DASHBOARD = "supakorn/smartgarden/dashboard/commands"
MQTT_TOPIC_SENSORS = "supakorn/smartgarden/pi/status"
# ------------------------------------
VIDEO_STREAM_URL = f"http://{PI_IP_ADDRESS}:8080/video_feed" if PI_IP_ADDRESS else None

# --- Functions ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Dashboard connected to HiveMQ Broker!")
        client.subscribe(MQTT_TOPIC_SENSORS)
        st.session_state.mqtt_connected = True
    else:
        print(f"Dashboard failed to connect, return code {rc}")
        st.session_state.mqtt_connected = False
        st.session_state.connection_error_code = rc

def on_message(client, userdata, msg):
    try:
        st.session_state.latest_data = json.loads(msg.payload.decode())
    except Exception as e:
        print(f"Error processing message in dashboard: {e}")

# --- Main App ---
st.set_page_config(page_title="IoT Smart Garden", layout="wide")
st.title("🌿 IoT Smart Garden with Vision Control")

# --- Debug Info ---
st.subheader("🕵️‍♂️ Debug Info")
st.code(f"Broker: {MQTT_BROKER}")
st.code(f"Port: {MQTT_PORT}")

# Initialize session state variables
if 'mqtt_client' not in st.session_state:
    # **สำคัญมาก: ต้องใช้ WebSockets และ API V1**
    st.session_state.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, transport="websockets")
    st.session_state.mqtt_client.on_connect = on_connect
    st.session_state.mqtt_client.on_message = on_message
    st.session_state.mqtt_connected = False
    st.session_state.latest_data = {}
    st.session_state.connection_error_code = None
    if MQTT_BROKER:
        try:
            st.session_state.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            st.session_state.mqtt_client.loop_start()
        except Exception as e:
            st.error(f"Failed to initiate connection: {e}")

# --- UI Layout ---
left_col, right_col = st.columns(2)
data = st.session_state.get('latest_data', {})

with left_col:
    st.subheader("Sensor Readings & Status")
    status_indicator = "🟢 Connected" if st.session_state.mqtt_connected else "🔴 Disconnected"
    st.metric(label="MQTT Connection", value=status_indicator)
    if not st.session_state.mqtt_connected and st.session_state.connection_error_code:
        st.error(f"Connection failed with code: {st.session_state.connection_error_code}")
    st.write("---")
    s1, s2 = st.columns(2)
    s1.metric("🌡️ Air Temperature", f"{data.get('air_temp', 0):.2f} °C")
    s1.metric("💧 Air Humidity", f"{data.get('air_humidity', 0):.2f} %")
    s2.metric("☀️ Light Intensity", f"{data.get('light_lux', 0):.2f} Lux")
    s2.metric("🌱 Soil Moisture", f"{data.get('soil_moisture', 0)} (raw)")
    st.write("---")
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
    if btn_c2.button("Turn Pump OFF", key="pump_off", disabled=disable_buttons):
        st.session_state.mqtt_client.publish(MQTT_TOPIC_COMMANDS_DASHBOARD, "PUMP_OFF")
    st.info("🖐️ Show 2 fingers to the camera to toggle modes.")

with right_col:
    st.subheader("Live Feed")
    if VIDEO_STREAM_URL:
        st.image(VIDEO_STREAM_URL, caption="Live from Raspberry Pi (viewable on same network)")
    else:
        st.warning("PI_IP_ADDRESS secret not set. Video stream disabled.")
    st.caption(f"Detected Fingers: {data.get('finger_count', 'N/A')}")

# Auto-refresh
time.sleep(2)
st.rerun()
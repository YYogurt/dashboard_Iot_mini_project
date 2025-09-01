# โค้ดสำหรับ Dashboard ที่จะ Deploy ขึ้น Streamlit Cloud
# ภาษา: Python (ใช้ไลบรารี Streamlit)

import streamlit as st
import json
import time
import paho.mqtt.client as mqtt
import os

# --- Configuration ---
# !!! สำคัญ: ค่าเหล่านี้จะถูกดึงมาจาก Secrets บน Streamlit Cloud
# สำหรับ WebSockets:
# MQTT_BROKER จะเป็น URL จาก ngrok เช่น "random-name.ngrok-free.app"
# MQTT_PORT จะเป็น 443
MQTT_BROKER = os.environ.get("MQTT_BROKER")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 443)) # Port มาตรฐานสำหรับ WSS (Secure WebSockets)
PI_IP_ADDRESS = os.environ.get("PI_IP_ADDRESS")

# --- MQTT Topics ---
MQTT_TOPIC_COMMANDS_DASHBOARD = "onigiri/smartgarden/dashboard/commands"
MQTT_TOPIC_SENSORS = "onigiri/smartgarden/pi/status" # รับข้อมูลสถานะจาก Pi โดยตรง

# วิดีโอสตรีมจะยังคงต้องใช้ IP ของ Pi ซึ่งหมายความว่าต้องดูจากในเครือข่ายเดียวกัน
VIDEO_STREAM_URL = f"http://{PI_IP_ADDRESS}:8080/video_feed" if PI_IP_ADDRESS else None

# --- Functions ---
def on_connect(client, userdata, flags, rc, properties=None):
    """Callback function for when the client connects to the broker."""
    if rc == 0:
        print("Dashboard connected to MQTT Broker via WebSockets!")
        # Subscribe เพื่อรับข้อมูลสถานะล่าสุดจาก Pi
        client.subscribe(MQTT_TOPIC_SENSORS)
        st.session_state.mqtt_connected = True
    else:
        print(f"Dashboard failed to connect, return code {rc}")
        st.session_state.mqtt_connected = False

def on_message(client, userdata, msg):
    """Callback function for when a message is received from the broker."""
    try:
        # เก็บข้อมูลล่าสุดไว้ใน session_state
        st.session_state.latest_data = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        print(f"Could not decode JSON: {msg.payload}")
    except Exception as e:
        print(f"An error occurred in on_message: {e}")

def get_mqtt_client():
    """Creates and returns an MQTT client instance."""
    # --- ✨ การเปลี่ยนแปลงสำคัญอยู่ตรงนี้ ✨ ---
    # เพิ่ม transport="websockets" เพื่อบอกให้ Client เชื่อมต่อผ่าน WebSockets
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport="websockets")
    # ------------------------------------
    client.on_connect = on_connect
    client.on_message = on_message
    return client

# --- Main App ---
st.set_page_config(page_title="IoT Smart Garden", layout="wide")
st.title("🌿 IoT Smart Garden with Vision Control")

# Initialize session state variables
if 'mqtt_client' not in st.session_state:
    st.session_state.mqtt_client = get_mqtt_client()
    st.session_state.mqtt_connected = False
    st.session_state.latest_data = {}
    try:
        if MQTT_BROKER and MQTT_PORT:
            st.session_state.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            st.session_state.mqtt_client.loop_start()
        else:
            st.error("MQTT_BROKER or MQTT_PORT is not set in secrets.toml!")
    except Exception as e:
        st.error(f"Failed to connect to MQTT Broker: {e}")

# --- UI Layout ---
left_col, right_col = st.columns(2)
data = st.session_state.get('latest_data', {})

with left_col:
    st.subheader("Sensor Readings & Status")
    
    # Connection Status
    status_indicator = "🟢 Connected" if st.session_state.mqtt_connected else "🔴 Disconnected"
    st.metric(label="MQTT Connection", value=status_indicator, delta=None)
    st.write("---")

    # Sensor Data Display
    s1, s2 = st.columns(2)
    s1.metric("🌡️ Air Temperature", f"{data.get('air_temp', 0):.2f} °C")
    s1.metric("💧 Air Humidity", f"{data.get('air_humidity', 0):.2f} %")
    s2.metric("☀️ Light Intensity", f"{data.get('light_lux', 0):.2f} Lux")
    s2.metric("🌱 Soil Moisture", f"{data.get('soil_moisture', 0)} (raw)")
    
    st.write("---")
    
    # System Controls
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
        st.image(VIDEO_STREAM_URL, caption="Live from ESP32-CAM (viewable on the same network)")
    else:
        st.warning("Video stream URL is not configured. Please set PI_IP_ADDRESS in secrets.")

# Auto-refresh the page to update data
time.sleep(1)
st.rerun()
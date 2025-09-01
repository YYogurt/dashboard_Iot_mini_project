# dashboard.py (เวอร์ชันแก้ไข)
import streamlit as st
import json
import time
import paho.mqtt.client as mqtt
import os

# --- Configuration ---
MQTT_BROKER = os.environ.get("MQTT_BROKER")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 443)) # ใช้ 443 สำหรับ WSS
PI_IP_ADDRESS = os.environ.get("PI_IP_ADDRESS")
MQTT_TOPIC_COMMANDS_DASHBOARD = "onigiri/smartgarden/dashboard/commands"
# ✨ เปลี่ยน Topic ที่จะรับฟัง ให้เป็น Topic ใหม่จาก Pi ✨
MQTT_TOPIC_SENSORS = "onigiri/smartgarden/pi/status"
VIDEO_STREAM_URL = f"http://{PI_IP_ADDRESS}:8080/video_feed" if PI_IP_ADDRESS else None

# --- Functions ---
def on_connect(client, userdata, flags, rc, properties=None):
    """Callback function for when the client connects to the broker."""
    if rc == 0:
        print("Dashboard connected to MQTT Broker!")
        client.subscribe(MQTT_TOPIC_SENSORS)
        st.session_state.mqtt_connected = True
    else:
        print(f"Dashboard failed to connect, return code {rc}")
        st.session_state.mqtt_connected = False

def on_message(client, userdata, msg):
    """Callback function for when a message is received from the broker."""
    try:
        st.session_state.latest_data = json.loads(msg.payload.decode())
    except Exception as e:
        print(f"Error processing message in dashboard: {e}")

# --- Main App ---
st.set_page_config(page_title="IoT Smart Garden", layout="wide")
st.title("🌿 IoT Smart Garden with Vision Control")

# Initialize session state variables
if 'mqtt_client' not in st.session_state:
    st.session_state.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport="websockets")
    st.session_state.mqtt_client.on_connect = on_connect
    st.session_state.mqtt_client.on_message = on_message
    st.session_state.mqtt_connected = False
    st.session_state.latest_data = {}
    if MQTT_BROKER:
        try:
            st.session_state.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            st.session_state.mqtt_client.loop_start()
        except Exception as e:
            st.error(f"Failed to connect to MQTT Broker: {e}")
    else:
        st.warning("MQTT_BROKER secret is not set.")

# --- UI Layout ---
left_col, right_col = st.columns(2)
data = st.session_state.get('latest_data', {})

with left_col:
    st.subheader("Sensor Readings & Status")
    
    status_indicator = "🟢 Connected" if st.session_state.mqtt_connected and data else "🔴 Disconnected"
    st.metric(label="MQTT Connection", value=status_indicator, delta=None)
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
        st.image(VIDEO_STREAM_URL, caption="Live from Raspberry Pi")
    else:
        st.warning("Video stream URL is not configured.")
    st.caption(f"Detected Fingers: {data.get('finger_count', 'N/A')}")


# Auto-refresh the page to update data
if st.session_state.mqtt_connected:
    time.sleep(2)
    st.rerun()
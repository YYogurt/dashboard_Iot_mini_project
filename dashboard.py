# dashboard.py (เวอร์ชันสุดท้าย - test.mosquitto.org)
import streamlit as st
import json
import time
import paho.mqtt.client as mqtt
import os

# --- Configuration ---
# --- ✨ การเปลี่ยนแปลง ✨ ---
MQTT_BROKER = "test.mosquitto.org"
# Port สำหรับ Secure WebSockets (wss://) คือ 8081
MQTT_PORT = 8081
PI_IP_ADDRESS = os.environ.get("PI_IP_ADDRESS")

# Topic ที่มีชื่อเฉพาะของคุณ
MQTT_TOPIC_COMMANDS_DASHBOARD = "supakorn/smartgarden/dashboard/commands"
MQTT_TOPIC_SENSORS = "supakorn/smartgarden/pi/status"
# ------------------------------------
VIDEO_STREAM_URL = f"http://{PI_IP_ADDRESS}:8080/video_feed" if PI_IP_ADDRESS else None

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Dashboard connected to test.mosquitto.org!")
        client.subscribe(MQTT_TOPIC_SENSORS)
        st.session_state.mqtt_connected = True
    else:
        st.session_state.mqtt_connected = False
        st.session_state.connection_error_code = rc

def on_message(client, userdata, msg):
    try: st.session_state.latest_data = json.loads(msg.payload.decode())
    except Exception as e: print(f"Error processing message: {e}")

st.set_page_config(page_title="IoT Smart Garden", layout="wide")
st.title("🌿 IoT Smart Garden with Vision Control")

# Initialize and Connect
if 'mqtt_client' not in st.session_state:
    st.session_state.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, transport="websockets")
    # --- ✨ การเปลี่ยนแปลงสำคัญ ✨ ---
    # ตั้งค่า TLS/SSL เพื่อให้เชื่อมต่อแบบ wss:// ได้
    st.session_state.mqtt_client.tls_set()
    # ------------------------------------
    st.session_state.mqtt_client.on_connect = on_connect
    st.session_state.mqtt_client.on_message = on_message
    st.session_state.mqtt_connected = False
    st.session_state.latest_data = {}
    st.session_state.connection_error_code = None
    try:
        st.session_state.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        st.session_state.mqtt_client.loop_start()
    except Exception as e:
        st.error(f"Failed to initiate connection: {e}")

# (ส่วน UI ที่เหลือเหมือนเดิมทุกประการ)
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
    if VIDEO_STREAM_URL: st.image(VIDEO_STREAM_URL, caption="Live Feed")
    else: st.warning("PI_IP_ADDRESS secret not set.")
    st.caption(f"Detected Fingers: {data.get('finger_count', 'N/A')}")
time.sleep(2)
st.rerun()
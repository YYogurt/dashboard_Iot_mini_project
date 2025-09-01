import streamlit as st
import json
import time
import paho.mqtt.client as mqtt
import pymongo

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_COMMANDS = "onigiri/smartgarden/commands"
MONGO_CONNECTION_STRING = "mongodb+srv://onigiri:onigiri@labapi.inqpshm.mongodb.net/?retryWrites=true&w=majority&appName=LabAPI"
DEVICE_ID = "onigiri_garden_01"

try:
    mqtt_client = mqtt.Client()
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
except Exception as e:
    st.error(f"Could not connect to MQTT Broker: {e}")
    mqtt_client = None

try:
    mongo_client = pymongo.MongoClient(MONGO_CONNECTION_STRING)
    db = mongo_client['smartgarden_db']
    status_collection = db['device_status']
except Exception as e:
    st.error(f"Could not connect to MongoDB: {e}")
    status_collection = None

def load_data():
    if status_collection:
        data = status_collection.find_one({"device_id": DEVICE_ID})
        return data if data else {}
    return {}

def format_metric(value, unit=""):
    return f"{value:.1f}{unit}" if isinstance(value, (int, float)) else "N/A"

st.set_page_config(layout="wide")
st.title("🌿 IoT Smart Garden Dashboard")

data = load_data()
video_stream_url = data.get("video_stream_url") 

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💧 Soil Moisture", format_metric(data.get("soil_moisture")))
c2.metric("🌊 Water Level", format_metric(data.get("water_level")))
c3.metric("🌡️ Temperature", format_metric(data.get("temperature"), " °C"))
c4.metric("💧 Humidity", format_metric(data.get("humidity"), " %"))
c5.metric("💡 Light", format_metric(data.get("light_intensity"), " lux"))

st.write("---")

c_bot1, c_bot2 = st.columns(2)
pump_status_text = "ON 🟢" if data.get("pump_on") else "OFF 🔴"
c_bot1.header(f"Pump Status: {pump_status_text}")

btn_c1, btn_c2 = c_bot1.columns(2)
if btn_c1.button("Turn Pump ON", key="pump_on"):
    if mqtt_client: mqtt_client.publish(MQTT_TOPIC_COMMANDS, "PUMP_ON"); st.rerun()
        
if btn_c2.button("Turn Pump OFF", key="pump_off"):
    if mqtt_client: mqtt_client.publish(MQTT_TOPIC_COMMANDS, "PUMP_OFF"); st.rerun()

c_bot2.header(f"Detected Fingers: {data.get('finger_count', 'N/A')} 🖐️")

cam_c, raw_c = st.columns(2)
if video_stream_url:
    cam_c.image(video_stream_url, caption="Live Camera Feed", width='stretch')
else:
    cam_c.warning("Camera stream URL not found. Is the Raspberry Pi running?")
raw_c.subheader("Raw Data")
raw_c.json(data)

time.sleep(2)
st.rerun()
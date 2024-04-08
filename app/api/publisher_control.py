from fastapi import FastAPI
from fastapi_mqtt import FastMQTT, MQTTConfig
from pydantic import BaseModel
import jsonpickle
from ipaddress import IPv4Address

app = FastAPI()

mqtt_config = MQTTConfig()

mqtt = FastMQTT(config=mqtt_config)

mqtt.init_app(app)

import asyncio
import re
from datetime import datetime, date
from typing import List, Dict, Any
from ipaddress import IPv4Address

import logging

from fastapi import FastAPI, Depends
from fastapi_mqtt import FastMQTT, MQTTConfig
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlmodel import Session, SQLModel
from pydantic import BaseModel

from models.monitoring import Alarm, Device, Sensor, Employe, KeyFob, EntryLog, ValueType, Reading, Door, Guest

from database import engine


#Add the base logging config 
logging.basicConfig(filename='/home/sysadmin/code/iot_case_h5/app/logs/application.log',  # log to a file named 'app.log'
                    filemode='a',  # append to the log file if it exists, otherwise create it
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

#get the logger with the newly set config
_logger = logging.getLogger(__name__)

#Application 
app = FastAPI()


@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)



async def get_session():
    async with AsyncSession(engine) as session:
        yield session


# ------------------------------------------------------------ HTTP

@app.get("/api",response_class=HTMLResponse)
async def entry():
    return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Greenhouse API</title>
                <!-- Include Bootstrap CSS from CDN -->
                <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
            </head>
            <body class="bg-light">
                <div class="container py-5">
                    <h1 class="display-4 text-center mb-3">Welcome to the Greenhouse Temperature and Humidity API</h1>
                    <p class="lead text-center mb-5">Use the links below to navigate to the API documentation:</p>
                    <div class="row">
                        <div class="col-md-6 text-center mb-3">
                            <a href="/api/docs" class="btn btn-primary btn-lg">Swagger UI Documentation</a>
                        </div>
                        <div class="col-md-6 text-center mb-3">
                            <a href="/api/redoc" class="btn btn-secondary btn-lg">ReDoc Documentation</a>
                        </div>
                    </div>
                </div>
                <!-- jQuery first, then Popper.js, then Bootstrap JS -->
                <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.2/dist/umd/popper.min.js"></script>
                <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
            </body>
            </html>

    """


# ------------------------------------------------------------ MQTT

mqtt_config = MQTTConfig()

mqtt = FastMQTT(config=mqtt_config)

mqtt.init_app(app)

root = "/mqtt/root" 
temprature = f"{root}/room/+/+/temperature"
doors_keycard = f"{root}/room/+/doors/keycard"
doors_pin = f"{root}/room/+/doors/pin"

@mqtt.on_connect()
def connect(client, flags, rc, properties):
    mqtt.client.subscribe("/mqtt/#") # subscribing mqtt topic wildcard- multi-level
    print("connected: ", client, flags, rc, properties)

@mqtt.on_message()
async def message(client, topic, payload, qos, properties):
    parts = topic.split("/")

    if parts[-1] == temprature.split("/")[-1]:
        pattern = r"T: (\d+), H: (\d+)"
        match = re.match(pattern, payload.decode())

        if match:
            # Extract the temperature and humidity values
            temperature = int(match.group(1))
            humidity = int(match.group(2))
            device_id = parts[-3]
            sensor_id = parts[-2]

            # How do we know what value ID it is? 
            temp_reading = Reading(value_type_id=1,sensor_id=int(sensor_id), value=str(humidity))
            humid_reading = Reading(value_type_id=2,sensor_id=int(sensor_id), value=str(temperature))

            async for session in get_session():
                session.add(temp_reading)
                session.add(humid_reading)
                session.commit()
                session.refresh(temp_reading)
                session.refresh(humid_reading)
                await session.commit()

    if parts[-1] == doors_pin.split("/")[-1]:
        return_address = re.findall(r'(?<=\+).+', payload.decode())
        if return_address:
            mqtt.client.publish(message_or_topic = return_address[0], payload = b'1', qos=0,properties=properties)
    if parts[-1] == doors_keycard.split("/")[-1]:
        return_address = re.findall(r'(?<=\+).+', payload.decode())
        if return_address:
            mqtt.client.publish(message_or_topic = return_address[0], payload = b'0', qos=0,properties=properties)


@mqtt.on_disconnect()
def disconnect(client, packet, exc=None):
    print("Disconnected")

@mqtt.on_subscribe()
def subscribe(client, mid, qos, properties):
    print("subscribed", client, mid, qos, properties)

@app.get("/")
async def func():
    mqtt.client.publish("/mqtt", "Hello from fastApi") 
    return {"result": True, "message": "Published"}


@app.post("/get_all")
async def get_all():
    async with AsyncSession(engine, expire_on_commit=True) as session:
        
        reading = await session.execute(select(Reading))
        alarm = await session.execute(select(Alarm))
        device = await session.execute(select(Device))
        sensor = await session.execute(select(Sensor))
        employee = await session.execute(select(Employe))
        entry_log = await session.execute(select(EntryLog))
        valuetype = await session.execute(select(ValueType))
        guest = await session.execute(select(Guest))

        return {
            "reading" : reading.scalars().all(),
            "alarm" : alarm.scalars().all(),
            "device" : device.scalars().all(),
            "sensor" : sensor.scalars().all(),
            "employee" : employee.scalars().all(),
            "entry_log" : entry_log.scalars().all(),
            "valuetype" : valuetype.scalars().all(),
            "guest" : guest.scalars().all(),
        }
    
@app.post("/create_sample_data", response_model=Dict[str, str])
async def create_sample_data():
    async with AsyncSession(engine,expire_on_commit=True) as session:
        # Create sample data for Alarm
        alarm = Alarm(sensor_id=1, message="Sample message", severity="high", is_acknowledged=False, created_at=datetime.now())
        session.add(alarm)
        await session.commit()
        session.refresh(alarm)



        # Create sample data for Device
        device = Device(name="Sample Device", created_at=datetime.now())
        session.add(device)
        await session.commit()
        session.refresh(device)


        # Create sample data for Sensor
        sensor = Sensor(device_id=device.id, name="Sample Sensor", created_at=datetime.now())
        session.add(sensor)
        await session.commit()
        session.refresh(sensor)

                
                
        # Create sample data for ValueType
        value_type = ValueType(name="Sample temp", type="temp", created_at=datetime.now())
        session.add(value_type)
        await session.commit()
        session.refresh(value_type)


        # Create sample data for Reading
        reading = Reading(value_type_id=value_type.id, sensor_id=sensor.id, value="Sample Value", created_at=datetime.now())
        session.add(reading)
        await session.commit()
        session.refresh(reading)

        # Create sample data for Employe
        employe = Employe(name="Sample Employe", phone_number=1234567890, created_at=datetime.now())
        session.add(employe)
        await session.commit()
        session.refresh(employe)

        # Create sample data for Guest
        guest = Guest(name="Sample Guest", created_at=datetime.now())
        session.add(guest)
        await session.commit()
        session.refresh(guest)


        # Create sample data for KeyFob
        key_fob = KeyFob(is_active=True, key="Sample Key", valid_until=date.today(), created_at=datetime.now())
        session.add(key_fob)
        await session.commit()
        session.refresh(key_fob)


        # Create sample data for Door
        door = Door(name="Sample Door", accses_code="Sample Code")
        session.add(door)
        await session.commit()
        session.refresh(door)
        


        # Create sample data for EntryLog
        entry_log = EntryLog(is_active=True, sensor_id=sensor.id, key_fob_id=key_fob.id, door_id=door.id, created_at=datetime.now())
        session.add(entry_log)
        await session.commit()
        session.refresh(entry_log)




        await session.commit()

        return {
            "sample_data": "Database contians data"
        }

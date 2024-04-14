import re

import logging

from fastapi import FastAPI
from fastapi_mqtt import FastMQTT, MQTTConfig
from fastapi.responses import HTMLResponse

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel

from models.monitoring import (Base,Device, Sensor, Door, Reading, ValueType,
    Alarm, Employee, Guest, KeyFob, EntryLog)

from database import engine, async_session

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select



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
        # Drop all tables (make sure this is what you want!)
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        


# Dependency to get the async session
async def get_session():
    async with async_session() as session:
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


@mqtt.on_subscribe()
def subscribe(client, mid, qos, properties):
    print("subscribed", client, mid, qos, properties)

@app.get("/")
async def func():
    mqtt.client.publish("/mqtt", "Hello from fastApi") 
    return {"result": True, "message": "You have connected to Fastapi mqtt"}


@app.post("/create-sample-data", status_code=status.HTTP_201_CREATED)
async def create_sample_data(session: AsyncSession = Depends(get_session)):
    try:
        # Create sample value types
        temp_value_type = ValueType(name="Temperature", type="Celsius")
        humidity_value_type = ValueType(name="Humidity", type="Percentage")
        
        # Create sample devices, sensors, and doors
        sample_device = Device(name="Thermostat")
        sample_door = Door(name="Front Door", access_code="12345")
        sample_sensor = Sensor(name="Temperature Sensor", device=sample_device, door=sample_door)

        # Create sample readings
        temp_reading = Reading(value_type=temp_value_type, sensor=sample_sensor, value="22")
        humidity_reading = Reading(value_type=humidity_value_type, sensor=sample_sensor, value="45")

        # Create sample alarm
        sample_alarm = Alarm(sensor=sample_sensor, message="High temperature!", severity="High", is_acknowledged=False)

        # Create sample employees, guests, and key fobs
        sample_employee = Employee(name="Alice", phonenumber="1234567890")
        sample_guest = Guest(name="Bob")
        sample_key_fob = KeyFob(is_active=True, key="ABC123", valid_until=datetime.utcnow() + timedelta(days=1))

        # Link employee and guest to key fob
        sample_employee.key_fob = sample_key_fob
        sample_guest.key_fob = sample_key_fob

        # Create sample entry log
        sample_entry_log = EntryLog(sensor=sample_sensor, key_fob=sample_key_fob, date=datetime.utcnow())

        # Add all to session and commit
        session.add_all([
            temp_value_type, humidity_value_type, sample_device, sample_door, sample_sensor,
            temp_reading, humidity_reading, sample_alarm, sample_employee, sample_guest,
            sample_key_fob, sample_entry_log
        ])
        await session.commit()

        return {"message": "Sample data created successfully"}

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-sample-data")
async def get_sample_data(session: AsyncSession = Depends(get_session)):
    try:
        reading = await session.execute(select(Reading))
        alarm = await session.execute(select(Alarm))
        device = await session.execute(select(Device))
        sensor = await session.execute(select(Sensor))
        employee = await session.execute(select(Employee))
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
import re

import logging

from fastapi import FastAPI
from fastapi_mqtt import FastMQTT, MQTTConfig
from fastapi.responses import HTMLResponse

from models.monitoring import (Base,Device, Sensor, Door, Reading, ValueType,
    Alarm, Employee, Guest, KeyFob, EntryLog)

from schema.monitoring_schema import DeviceSchema, SensorSchema,SensorSchemaWithoutDoor ,DoorSchema

from database import engine, async_session


from sqlalchemy import desc
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi.middleware.cors import CORSMiddleware

import os
from dotenv import load_dotenv

# Load environment variables from the .env file
def load_env_file(file_path: str):
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'configFiles', file_path)
    load_dotenv(dotenv_path)

# Load environment variables from the .control.env file
load_env_file('.control.env')

# Define your variables with default values
Max_temp = int(os.getenv("Max_temp", 0))
Min_temp = int(os.getenv("Min_temp", 0))
Max_humid = int(os.getenv("Max_humid", 0))
Min_humid = int(os.getenv("Min_humid", 0))

# Load environment variables from the .env file
load_env_file('.env')

DEBUG = os.getenv("Debug_mode", False)

# Load environment variables from the mqtt.env file
load_env_file('mqtt.env')


#Add the base logging config 
logging.basicConfig(filename='/home/sysadmin/code/iot_case_h5/app/logs/application.log',  # log to a file named 'app.log'
                    filemode='a',  # append to the log file if it exists, otherwise create it
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

#get the logger with the newly set config
_logger = logging.getLogger(__name__)

#Application 
app = FastAPI(root_path="/api",docs_url="/docs", redoc_url="/redoc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        if DEBUG is True:
            # Drop all tables (make sure this is what you want!)
            await conn.run_sync(Base.metadata.drop_all)
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        return


# Dependency to get the async session
async def get_session():
    async with async_session() as session:
        yield session


# ------------------------------------------------------------ MQTT

mqtt_config = MQTTConfig(
    host=os.getenv("HOST", "localhost"),
    port=int(os.getenv("PORT", 1883)),
    username=os.getenv("USERNAME", ""),
    password=os.getenv("PASSWORD", ""),
    keepalive=int(os.getenv("KEEPALIVE", 60)),
    clean_session=bool(os.getenv("CLEAN_SESSION", True)),
    will_message=os.getenv("WILL_MESSAGE", "Disconnected"),
    reconnect_delay=int(os.getenv("RECONNECT_DELAY", 10)),
    reconnect_delay_max=int(os.getenv("RECONNECT_DELAY_MAX", 120))
)

mqtt = FastMQTT(config=mqtt_config)

mqtt.init_app(app)

@mqtt.on_connect()
def connect(client, flags, rc, properties):
    mqtt.client.subscribe("/mqtt/#") # subscribing mqtt topic wildcard- multi-level
    print("connected: ", client, flags, rc, properties)

@mqtt.on_message()
async def message(client, topic, payload, qos, properties):
    async def extract_temp_humidity(payload):
        pattern = r"T: (\d+), H: (\d+)"
        match = re.match(pattern, payload)
        if not match:
            raise ValueError("Invalid temperature/humidity format")
        temperature = int(match.group(1))
        humidity = int(match.group(2))
        return temperature, humidity
    
    async def create_alarm(sensor_id, message, severity,is_acknowledged=False):
        async with async_session() as session:
            alarm = Alarm(sensor_id = sensor_id, message=message,severity=severity, is_acknowledged=is_acknowledged)
            session.add(alarm)
            await session.commit()


    async def store_readings(temperature, humidity, device_id, sensor_id):
        temp_reading = Reading(value_type_id=1, sensor_id=int(sensor_id), value=str(temperature))
        humid_reading = Reading(value_type_id=2, sensor_id=int(sensor_id), value=str(humidity))

        if int(temp_reading.value) > Max_temp or int(temp_reading.value) < Min_temp:
            await create_alarm(sensor_id = int(sensor_id), message="Temp outside normal fuction",severity="warning", is_acknowledged=False )
        if int(humid_reading.value) > Max_humid or int(humid_reading.value) < Min_humid:
            await create_alarm(sensor_id = int(sensor_id), message="humid outside normal fuction",severity="warning", is_acknowledged=False )

        async with async_session() as session:
            session.add_all([temp_reading, humid_reading])
            await session.commit()

    async def parse_payload_keycard(payload):
        
        return_address = re.findall(r'(?<=\+).+', payload)
        keycard_code = re.findall(r'!(.*?)\+', payload)
        if return_address:
            return return_address,keycard_code[0]
        return None,None
    
    async def verify_keyfob_access(sensor_id,keycard_code):
        """
        Verifies that the keyfob exists and matches the door's access code.
        """
        async with async_session() as session:
            stmt = select(KeyFob).where(KeyFob.key == keycard_code, KeyFob.valid_until >= datetime.utcnow())
            result = await session.execute(stmt)
            keyfob = result.scalars().all()
            if not keyfob:
                _logger.warning(f"Error with {keyfob}")
                return None , False  # Error   
            keyfob = keyfob[0]
            _logger.warning(f"keyfob found: {keyfob}")


            if keyfob and keyfob.key == keycard_code and keyfob.is_active: 
                return keyfob.id, True # Access granted
            elif keyfob:
                return keyfob.id, False # Access Denied

        return None , False  # Error
        
    async def handle_keycard(payload, sensor_id):
        """
        Handles the keycard payload.
        """
        return_address,keycard_code = await parse_payload_keycard(payload)
        _logger.warning(f"return_address :: {return_address}")

        if return_address is not None and keycard_code is not None:

            keyfob_id,access_granted = await verify_keyfob_access(sensor_id,keycard_code)
            if not keyfob_id and not access_granted: 
                response_payload = b'0'
                mqtt.client.publish(message_or_topic = return_address[0], payload = response_payload, qos=0,properties=properties)
                _logger.error("keyfob_id not found")
                return

            # Create entry log only if access is granted
            await create_entry_log_keyfob(sensor_id,keyfob_id,access_granted)

                
            response_payload = b'1' if access_granted else b'0'
            mqtt.client.publish(message_or_topic = return_address[0], payload = response_payload, qos=0,properties=properties)




    async def create_entry_log_keyfob(sensor_id, key_fob_id, approved):
        """
        Creates an entry log with the given sensor ID and access method (keycard or pin).
        """
        async with async_session() as session:
            entry_log = EntryLog(
                sensor_id=int(sensor_id), 
                key_fob_id=int(key_fob_id), 
                date=datetime.utcnow(), 
                approved=bool(approved)
            )
            session.add(entry_log)
            await session.commit()

    async def create_entry_log_pin(sensor_id, approved):
        """
        Creates an entry log with the given sensor ID and access method (keycard or pin).
        """
        async with async_session() as session:
            entry_log = EntryLog(
                sensor_id=int(sensor_id), 
                date=datetime.utcnow(), 
                approved=bool(approved)
            )
            session.add(entry_log)
            await session.commit()


    async def parse_payload_pin(payload):
        
        return_address = re.findall(r'(?<=\+).+', payload)
        keycard_code = re.findall(r'!(.*?)\+', payload)
        if return_address:
            return return_address,keycard_code[0]
        return None,None
    
    async def verify_pin(sensor_id,pincode):
        """
        Verifies that the keyfob exists and matches the door's access code.
        """
        async with async_session() as session:
            # Assuming each sensor is associated with one door
            _logger.warning(f"sensor_id to qury : {sensor_id}")
            stmt = select(Sensor).where(Sensor.id == int(sensor_id)).options(selectinload(Sensor.door))
            result = await session.execute(stmt)
            sensor = result.scalars().all()
            sensor : Sensor = sensor[0]

            if sensor and sensor.door.access_code == pincode:
                return True

        return False  # Access denied
    
    async def handle_pin(payload, sensor_id):
        """
        Handles the keycard payload.
        """
        return_address,pin_code = await parse_payload_pin(payload)
        _logger.warning(f"return_address :: {return_address}, pin_code {pin_code}")

        if return_address is not None and pin_code is not None:
            access_granted = await verify_pin(sensor_id,pin_code)
            await create_entry_log_pin(sensor_id,access_granted)
                
            response_payload = b'1' if access_granted else b'0'
            mqtt.client.publish(message_or_topic = return_address[0], payload = response_payload, qos=0,properties=properties)


    parts = topic.split("/")
    payload_decoded = payload.decode()
    _logger.warning(f"parts : {parts}, payload_load {payload_decoded}")

    # Temperature and Humidity Example
    if parts[-1] == "temperature":
        try:
            temperature, humidity = await extract_temp_humidity(payload_decoded)
            await store_readings(temperature, humidity, parts[-3], parts[-2])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Doors Keycard Example
    elif parts[-1] == "keycard":
        await handle_keycard(payload_decoded, parts[-2])

    # Doors Pin Example
    elif parts[-1] == "pin":
        await handle_pin(payload_decoded, parts[-2])
        


@mqtt.on_subscribe()
def subscribe(client, mid, qos, properties):
    print("subscribed", client, mid, qos, properties)


# ------------------------------------------------------------ HTTP
@app.get("/", response_class=HTMLResponse)
async def root():
    mqtt.client.publish("/mqtt", "Hello from fastApi") 
    return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>MQTT Sub api</title>
            <!-- Include Bootstrap CSS from CDN -->
            <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <h1 class="display-4 text-center mb-3">MQTT Sub api</h1>
                <p class="lead text-center mb-5">Use the links below to navigate to the API documentation:</p>
                <div class="row">
                    <div class="col-md-6 text-center mb-3">
                        <a href="/api/redoc" class="btn btn-secondary btn-lg">ReDoc Documentation</a>
                    </div>
                    <div class="col-md-6 text-center mb-3">
                        <a href="/api/docs" class="btn btn-primary btn-lg">Swagger UI Documentation</a>
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


@app.post("/create-sample-data", status_code=status.HTTP_200_OK)
async def create_sample_data(session: AsyncSession = Depends(get_session)):
    try:
        # Create sample value types
        temp_value_type = ValueType(name="Temperature", type="Celsius")
        humidity_value_type = ValueType(name="Humidity", type="Percentage")
        
        # Create sample devices, sensors, and doors
        sample_device = Device(name="Thermostat")
        sample_sensor = Sensor(name="Temperature Sensor", device=sample_device)
        
        # Door control
        sample_door = Door(name="Front Door", access_code="12345")
        sample_device2 = Device(name="Door controller")
        sample_sensor2 = Sensor(name="Door key card", device=sample_device2, door=sample_door)
        sample_sensor3 = Sensor(name="Door pin", device=sample_device2, door=sample_door)

        sample_door2 = Door(name="Front Door", access_code="12345")
        sample_device3 = Device(name="Door controller wifi")
        sample_sensor4 = Sensor(name="Door key card", device=sample_device3, door=sample_door2)

        # Create sample readings
        temp_reading = Reading(value_type=temp_value_type, sensor=sample_sensor, value="22")
        humidity_reading = Reading(value_type=humidity_value_type, sensor=sample_sensor, value="45")

        # Create sample alarm
        sample_alarm = Alarm(sensor=sample_sensor, message="High temperature!", severity="High", is_acknowledged=False)

        # Create sample employees, guests, and key fobs
        sample_employee = Employee(name="Alice", phonenumber="1234567890")
        sample_guest = Guest(name="Bob")
        sample_key_fob_employee = KeyFob(is_active=True, key="4be8eff", valid_until=datetime.utcnow() + timedelta(days=30))
        sample_key_fob_guest = KeyFob(is_active=False, key="928a3dbf", valid_until=datetime.utcnow() + timedelta(days=1))

        # Link employee and guest to key fob
        sample_employee.key_fob = sample_key_fob_employee
        sample_guest.key_fob = sample_key_fob_guest

        # Create sample entry log
        sample_entry_log = EntryLog(sensor=sample_sensor, key_fob=sample_key_fob_employee, date=datetime.utcnow(), approved=True)
        sample_entry_log = EntryLog(sensor=sample_sensor, key_fob=sample_key_fob_guest, date=datetime.utcnow(), approved=True)

        # Add all to session and commit
        session.add_all([
            temp_value_type, humidity_value_type, sample_device, sample_door, sample_sensor,
            temp_reading, humidity_reading, sample_alarm, sample_employee, sample_guest,
            sample_key_fob_employee,sample_key_fob_guest, sample_entry_log,sample_sensor2,sample_device2,sample_sensor3,sample_sensor4
        ])
        await session.commit()

        return {"message": "Sample data created successfully"}

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_all")
async def get_all(session: AsyncSession = Depends(get_session)):

    reading = await session.execute(select(Reading))
    alarm = await session.execute(select(Alarm))
    device = await session.execute(select(Device))
    sensor = await session.execute(select(Sensor))
    employee = await session.execute(select(Employee))
    entry_log = await session.execute(select(EntryLog))
    valuetype = await session.execute(select(ValueType))
    guest = await session.execute(select(Guest))
    keyfob = await session.execute(select(KeyFob))
    door = await session.execute(select(Door))

    return {
        "reading" : reading.scalars().all(),
        "alarm" : alarm.scalars().all(),
        "device" : device.scalars().all(),
        "sensor" : sensor.scalars().all(),
        "employee" : employee.scalars().all(),
        "entry_log" : entry_log.scalars().all(),
        "valuetype" : valuetype.scalars().all(),
        "guest" : guest.scalars().all(),
        "keyfob" : keyfob.scalars().all(),
        "door" : door.scalars().all(),
    }


@app.get("/get_temp")
async def get_temp(amount : int ,session: AsyncSession = Depends(get_session)):
    reading = await session.execute(select(Reading).where(Reading.value_type_id == 1).options(selectinload(Reading.sensor)).options(selectinload(Reading.value_type)).order_by(desc(Reading.created_date)).fetch(amount))
    
    return {
        "reading" : reading.scalars().all(),
    }

@app.get("/get_humid")
async def get_humid(amount : int ,session: AsyncSession = Depends(get_session)):
    reading = await session.execute(select(Reading).where(Reading.value_type_id == 2).options(selectinload(Reading.sensor)).options(selectinload(Reading.value_type)).order_by(desc(Reading.created_date)).fetch(amount))

    return {
        "reading" : reading.scalars().all(),
    }

@app.get("/get_entry_logs")
async def get_entry_logs(amount : int,  approved:bool,session: AsyncSession = Depends(get_session)):
    logs = await session.execute(select(EntryLog).where(EntryLog.approved == approved).options(selectinload(EntryLog.sensor)).order_by(desc(EntryLog.created_date)).fetch(amount))
    
    return {
        "logs" : logs.scalars().all(),
    }

@app.get("/get_alarm")
async def get_alarm(amount : int,  is_acknowledged:bool,session: AsyncSession = Depends(get_session)):
    alarm = await session.execute(select(Alarm).where(Alarm.is_acknowledged == is_acknowledged).options(selectinload(Alarm.sensor)).order_by(desc(Alarm.created_date)).fetch(amount))
    
    return {
        "alarm" : alarm.scalars().all(),
    }


@app.get("/get_all_basic")
async def get_all_basic(session: AsyncSession = Depends(get_session)):
    device = await session.execute(select(Device))
    sensor = await session.execute(select(Sensor))
    employee = await session.execute(select(Employee))
    guest = await session.execute(select(Guest))
    keyfob = await session.execute(select(KeyFob))
    door = await session.execute(select(Door))

    return {
        "device" : device.scalars().all(),
        "sensor" : sensor.scalars().all(),
        "employee" : employee.scalars().all(),
        "guest" : guest.scalars().all(),
        "keyfob" : keyfob.scalars().all(),
        "door" : door.scalars().all(),
    }

# Define endpoint to create a device
@app.post("/devices/")
async def create_device(device_data: DeviceSchema, session: AsyncSession = Depends(get_session)):
    device_name = device_data.name
    device = Device(name=device_name)
    session.add(device)
    await session.commit()
    return device

@app.post("/sensors/")
async def create_sensor(sensor: SensorSchema, session: AsyncSession = Depends(get_session)):
    sensor_data = sensor.dict()
    sensor_name = sensor_data.get("name")
    device_id = sensor_data.get("device_id")
    door_id = sensor_data.get("door_id")
    new_sensor = Sensor(name=sensor_name, device_id=device_id, door_id=door_id)
    session.add(new_sensor)
    await session.commit()
    return new_sensor

@app.post("/doors/")
async def create_door(door: DoorSchema, session: AsyncSession = Depends(get_session)):
    door_data = door.dict()
    door_name = door_data.get("name")
    access_code = door_data.get("access_code")
    new_door = Door(name=door_name, access_code=access_code)
    session.add(new_door)
    await session.commit()
    return new_door

@app.post("/sensors-without-door/")
async def create_sensor_without_door(sensor: SensorSchemaWithoutDoor, session: AsyncSession = Depends(get_session)):
    sensor_data = sensor.dict()
    sensor_name = sensor_data.get("name")
    device_id = sensor_data.get("device_id")
    new_sensor = Sensor(name=sensor_name, device_id=device_id)
    session.add(new_sensor)
    await session.commit()
    return new_sensor
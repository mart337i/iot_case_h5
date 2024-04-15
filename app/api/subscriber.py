import re

import logging

from fastapi import FastAPI
from fastapi_mqtt import FastMQTT, MQTTConfig
from fastapi.responses import HTMLResponse

from models.monitoring import (Base,Device, Sensor, Door, Reading, ValueType,
    Alarm, Employee, Guest, KeyFob, EntryLog)

from schema.monitoring_schema import DeviceCreate, DoorCreate, SensorCreate, ValueTypeCreate, EmployeeCreate, SensorCreate, SensorWithDoorCreate, BaseDeviceCreate , DeviceWithDoorCreate
from database import engine, async_session

from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload , selectinload



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
        # await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        # await conn.run_sync(Base.metadata.create_all)
        return


# Dependency to get the async session
async def get_session():
    async with async_session() as session:
        yield session


# ------------------------------------------------------------ MQTT

mqtt_config = MQTTConfig(
    host="localhost",  # e.g., "localhost" or "broker.hivemq.com"
    port=1883,  # Common ports are 1883 for non-TLS or 8883 for TLS
    username="",  # If required by your broker
    password="",  # If required by your broker
    keepalive=60,  # Keep alive interval in seconds
    clean_session=True,  # Set False if you want the broker to remember your client state
    will_message="Disconnected",  # The last will message to be sent
    reconnect_delay=10,  # Delay in seconds between reconnections
    reconnect_delay_max=120,  # Maximum delay in seconds between reconnections
)

mqtt = FastMQTT(config=mqtt_config)

mqtt.init_app(app)

# root = "/mqtt/root" 
# temprature = f"{root}/room/+/+/temperature"
# doors_keycard = f"{root}/room/+/doors/keycard"
# doors_pin = f"{root}/room/+/doors/pin"

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

    async def store_readings(temperature, humidity, device_id, sensor_id):
        temp_reading = Reading(value_type_id=1, sensor_id=int(sensor_id), value=str(temperature))
        humid_reading = Reading(value_type_id=2, sensor_id=int(sensor_id), value=str(humidity))
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
            # Assuming each sensor is associated with one door
            _logger.warning(f"sensor_id to qury : {sensor_id}")
            stmt = select(Sensor).where(Sensor.id == int(sensor_id)).options(selectinload(Sensor.door))
            result = await session.execute(stmt)
            sensor = result.scalars().all()
            sensor : Sensor = sensor[0]


            stmt = select(KeyFob).where(KeyFob.key == keycard_code, KeyFob.valid_until >= datetime.utcnow())
            result = await session.execute(stmt)
            keyfob = result.scalars().all()
            keyfob = keyfob[0]
            _logger.warning(f"keyfob found: {keyfob}")


            if keyfob and keyfob.key == keycard_code and keyfob.is_active: 
                _logger.warning(f"{keyfob.id} {sensor.door.access_code}")
                return keyfob.id, True # Access granted

        return None , False  # Access denied
        
    async def handle_keycard(payload, sensor_id):
        """
        Handles the keycard payload.
        """
        return_address,keycard_code = await parse_payload_keycard(payload)
        _logger.warning(f"return_address :: {return_address}")

        if return_address is not None and keycard_code is not None:
            try:
                keyfob_id,access_granted = await verify_keyfob_access(sensor_id,keycard_code)
                if access_granted:
                    # Create entry log only if access is granted
                    await create_entry_log_keyfob(sensor_id,keyfob_id,access_granted)
                    
                response_payload = b'1' if access_granted else b'0'
                mqtt.client.publish(message_or_topic = return_address[0], payload = response_payload, qos=0,properties=properties)
            except Exception as e:
                response_payload = b'0'
                mqtt.client.publish(message_or_topic = return_address[0], payload = response_payload, qos=0,properties=properties)
                _logger.error(f"{e}")



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
    async def create_entry_log_pin(sensor_id, key_fob_id, approved):
        """
        Creates an entry log with the given sensor ID and access method (keycard or pin).
        """
        async with async_session() as session:
            entry_log = EntryLog(
                sensor_id=sensor_id, 
                key_fob_id=key_fob_id, 
                date=datetime.utcnow(), 
                approved=approved
            )
            session.add(entry_log)
            await session.commit()

    parts = topic.split("/")
    payload_decoded = payload.decode()
    _logger.warning(f"parts : {parts}, payload_load {payload_decoded}")

    # Temperature and Humidity Example
    if parts[-1] == "temperature":
        try:
            temperature, humidity = extract_temp_humidity(payload_decoded)
            await store_readings(temperature, humidity, parts[-3], parts[-2])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Doors Keycard Example
    elif parts[-1] == "keycard":
        await handle_keycard(payload_decoded, parts[-2])

    # Doors Pin Example
    elif parts[-1] == "pin":
        # await pin(payload_decoded, parts[-2])
        pass


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
                        <a href="/docs" class="btn btn-primary btn-lg">Swagger UI Documentation</a>
                    </div>
                    <div class="col-md-6 text-center mb-3">
                        <a href="/redoc" class="btn btn-secondary btn-lg">ReDoc Documentation</a>
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
        sample_sensor2 = Sensor(name="Door sensor", device=sample_device2, door=sample_door)

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
            sample_key_fob_employee,sample_key_fob_guest, sample_entry_log,sample_sensor2,sample_device2
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
    }

    

@app.post("/create-device", status_code=status.HTTP_200_OK)
async def create_device(device_data: DeviceCreate, session: AsyncSession = Depends(get_session)):
    device = Device(name=device_data.name)
    sensor = Sensor(name=device_data.sensor.name, device=device)
    session.add(device)
    session.add(sensor)
    await session.commit()
    return {"message": "Device with sensor created successfully", "device_id": device.id, "sensor_id": sensor.id}

@app.post("/create-device-with-door", status_code=status.HTTP_200_OK)
async def create_device_with_door(device_data: DeviceWithDoorCreate, session: AsyncSession = Depends(get_session)):
    device = Device(name=device_data.name)
    door = Door(name=device_data.door.name, access_code=device_data.door.access_code)
    sensor = Sensor(name=device_data.sensor.name, device=device, door=door)
    session.add(device)
    session.add(door)
    session.add(sensor)
    await session.commit()
    return {
        "message": "Device with sensor and door created successfully",
        "device_id": device.id,
        "sensor_id": sensor.id,
        "door_id": door.id
    }

@app.post("/create-sensor-with-door", status_code=status.HTTP_200_OK)
async def create_sensor_with_door(sensor_data: SensorWithDoorCreate, session: AsyncSession = Depends(get_session)):
    device = select(Device).where(Device.id == sensor_data.device_id)
    result = await session.execute(device)
    device = result.scalar_one_or_none()
    if device is None: 
        return status.HTTP_404_NOT_FOUND
    
    door = Door(name=sensor_data.door.name, access_code=sensor_data.door.access_code)
    sensor = Sensor(name=sensor_data.name, device=device, door=door)

    session.add(door)
    session.add(sensor)
    await session.commit()
    return {
        "sensor_id": sensor.id,
        "door_id": door.id
    }

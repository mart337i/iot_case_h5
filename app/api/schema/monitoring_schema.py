from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ReadingCreate(BaseModel):
    value_type_id: int
    value: str

class AlarmCreate(BaseModel):
    message: str
    severity: str
    is_acknowledged: bool

class DoorCreate(BaseModel):
    name: str
    access_code: str

class SensorCreate(BaseModel):
    name: str
    door: Optional[DoorCreate] = None
    readings: List[ReadingCreate]
    alarms: List[AlarmCreate]

class DoorSensorCreate(BaseModel):
    name: str
    door: Optional[DoorCreate] = None

class DeviceCreate(BaseModel):
    name: str
    sensors: List[SensorCreate]

class ValueTypeCreate(BaseModel):
    name: str
    type: str

class KeyFobCreate(BaseModel):
    is_active: bool
    key: str
    valid_until: datetime

class EmployeeCreate(BaseModel):
    name: str
    phonenumber: str
    key_fob: KeyFobCreate

class GuestCreate(BaseModel):
    name: str
    key_fob: KeyFobCreate


class DeviceWithDoorCreate(BaseModel):
    name: str
    sensor: SensorCreate
    door: DoorCreate

class SensorWithDoorCreate(BaseModel):
    device_id : int
    sensor: DoorSensorCreate

class BaseDeviceCreate(BaseModel):
    name : int

class InitialDataCreate(BaseModel):
    devices: List[DeviceCreate]
    value_types: List[ValueTypeCreate]
    employees: List[EmployeeCreate]
    guests: List[GuestCreate]

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DeviceSchema(BaseModel):
    name: str

    class Config:
        orm_mode = True

# Pydantic schema for Sensor
class SensorSchema(BaseModel):
    name: str
    device_id: int
    door_id: Optional[int]

    class Config:
        orm_mode = True

class SensorSchemaWithoutDoor(BaseModel):
    name: str
    device_id: int

    class Config:
        orm_mode = True

# Pydantic schema for Door
class DoorSchema(BaseModel):
    name: str
    access_code: str

    class Config:
        orm_mode = True

class KeyFobSchema(BaseModel):
    is_active: bool
    key: str
    # valid_until: Optional[datetime]

class EmployeeSchema(BaseModel):
    name: str
    phonenumber: str
    key_fob: KeyFobSchema

class GuestSchema(BaseModel):
    name: str
    key_fob: KeyFobSchema


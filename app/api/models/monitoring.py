from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Define the base class
Base = declarative_base()

# Define the tables as classes
class Device(Base):
    __tablename__ = 'devices'
    id = Column(Integer, primary_key=True)
    name = Column(String)

    sensors = relationship("Sensor", back_populates="device")

class Sensor(Base):
    __tablename__ = 'sensors'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    device_id = Column(Integer, ForeignKey('devices.id'))
    door_id = Column(Integer, ForeignKey('doors.id'))

    device = relationship("Device", back_populates="sensors")
    door = relationship("Door", back_populates="sensors")
    readings = relationship("Reading", back_populates="sensor")
    entry_logs = relationship("EntryLog", back_populates="sensor")
    alarms = relationship("Alarm", back_populates="sensor")

class Door(Base):
    __tablename__ = 'doors'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    access_code = Column(String)

    sensors = relationship("Sensor", back_populates="door")

class Reading(Base):
    __tablename__ = 'readings'
    id = Column(Integer, primary_key=True)
    value_type_id = Column(Integer, ForeignKey('value_types.id'))
    sensor_id = Column(Integer, ForeignKey('sensors.id'))
    value = Column(String)

    sensor = relationship("Sensor", back_populates="readings")
    value_type = relationship("ValueType", back_populates="readings")

class ValueType(Base):
    __tablename__ = 'value_types'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(String)

    readings = relationship("Reading", back_populates="value_type")

class Alarm(Base):
    __tablename__ = 'alarms'
    id = Column(Integer, primary_key=True)
    sensor_id = Column(Integer, ForeignKey('sensors.id'))
    message = Column(String)
    severity = Column(String)
    is_acknowledged = Column(Boolean)

    sensor = relationship("Sensor", back_populates="alarms")

class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    phonenumber = Column(String)
    key_fob_id = Column(Integer, ForeignKey('key_fobs.id'))

    key_fob = relationship("KeyFob", back_populates="employee")

class Guest(Base):
    __tablename__ = 'guests'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    key_fob_id = Column(Integer, ForeignKey('key_fobs.id'))

    key_fob = relationship("KeyFob", back_populates="guest")

class KeyFob(Base):
    __tablename__ = 'key_fobs'
    id = Column(Integer, primary_key=True)
    is_active = Column(Boolean)
    key = Column(String)
    valid_until = Column(DateTime)

    employee = relationship("Employee", back_populates="key_fob")
    guest = relationship("Guest", back_populates="key_fob")
    entry_logs = relationship("EntryLog", back_populates="key_fob")

class EntryLog(Base):
    __tablename__ = 'entry_logs'
    id = Column(Integer, primary_key=True)
    sensor_id = Column(Integer, ForeignKey('sensors.id'))
    key_fob_id = Column(Integer, ForeignKey('key_fobs.id'))
    date = Column(DateTime)
    approved = Column(Boolean)

    sensor = relationship("Sensor", back_populates="entry_logs")
    key_fob = relationship("KeyFob", back_populates="entry_logs")
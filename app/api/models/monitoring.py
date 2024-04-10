from datetime import datetime, date
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel, Column, DateTime, text, Relationship
from sqlalchemy import func

from sqlalchemy.dialects.postgresql import UUID as UUIDSA

#-----------------Notes-----------------
# Optional[int] on id fields indicate that it is done by the database.
#
#
#---------------------------------------

class Alarm(SQLModel, table=True):
    __tablename__ = "alarm"
    id: Optional[int] = Field(default=None, primary_key=True)
    sensor_id: int
    message: str
    severity : str
    is_acknowledged: bool
    
    # BOILERPLATE CODE for all tables 
    created_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True), onupdate=func.now(), nullable=True
        )
    )
    uid: Optional[UUID] = Field(
        sa_column=Column(
            UUIDSA(as_uuid=True),
            server_default=text("gen_random_uuid()")
        ), default=None
    )

class Device(SQLModel, table=True):
    __tablename__ = "device"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

    created_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True), onupdate=func.now(), nullable=True
        )
    )
    uid: Optional[UUID] = Field(
        sa_column=Column(
            UUIDSA(as_uuid=True),
            server_default=text("gen_random_uuid()")
        ), default=None
    )

class Sensor(SQLModel, table=True):
    __tablename__ = "sensor"
    id: Optional[int] = Field(default=None, primary_key=True)
    device_id : int | None = Field(default=None, foreign_key="device.id")
    name: str

    created_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True), onupdate=func.now(), nullable=True
        )
    )
    uid: Optional[UUID] = Field(
        sa_column=Column(
            UUIDSA(as_uuid=True),
            server_default=text("gen_random_uuid()")
        ), default=None
    )

class Reading(SQLModel, table=True):
    __tablename__ = "reading"
    id: Optional[int] = Field(default=None, primary_key=True)
    value_type_id : int | None = Field(default=None, foreign_key="value_type.id")
    sensor_id : int | None = Field(default=None, foreign_key="sensor.id")
    value : str

    created_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True), onupdate=func.now(), nullable=True
        )
    )
    uid: Optional[UUID] = Field(
        sa_column=Column(
            UUIDSA(as_uuid=True),
            server_default=text("gen_random_uuid()")
        ), default=None
    )

class ValueType(SQLModel, table=True):
    __tablename__ = "value_type"
    id: Optional[int] = Field(default=None, primary_key=True)
    name : str
    type : str
    
    created_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True), server_onupdate=func.now(), nullable=True
        )
    )
    uid: Optional[UUID] = Field(
        sa_column=Column(
            UUIDSA(as_uuid=True),
            server_default=text("gen_random_uuid()")
        ), default=None
    )


# ----------------------------------------------------------------------- # Auth

class Employe(SQLModel, table=True):
    __tablename__ = "employe"
    id: Optional[int] = Field(default=None, primary_key=True)
    name : str
    phone_number : int
    key_fob_id: int | None = Field(default=None, foreign_key="Key_fob.id")


    created_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True), onupdate=func.now(), nullable=True
        )
    )
    uid: Optional[UUID] = Field(
        sa_column=Column(
            UUIDSA(as_uuid=True),
            server_default=text("gen_random_uuid()")
        ), default=None
    )

class Guest(SQLModel, table=True):
    __tablename__ = "guest"
    id: Optional[int] = Field(default=None, primary_key=True)
    name : str
    key_fob_id: int | None = Field(default=None, foreign_key="Key_fob.id")


    created_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True), onupdate=func.now(), nullable=True
        )
    )
    uid: Optional[UUID] = Field(
        sa_column=Column(
            UUIDSA(as_uuid=True),
            server_default=text("gen_random_uuid()")
        ), default=None
    )

class KeyFob(SQLModel, table=True):
    __tablename__ = "Key_fob"
    id: Optional[int] = Field(default=None, primary_key=True)
    is_active : bool
    key : str
    valid_until : date
    created_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True), onupdate=func.now(), nullable=True
        )
    )
    uid: Optional[UUID] = Field(
        sa_column=Column(
            UUIDSA(as_uuid=True),
            server_default=text("gen_random_uuid()")
        ), default=None
    )


class EntryLog(SQLModel, table=True):
    __tablename__ = "entry_log"
    id: Optional[int] = Field(default=None, primary_key=True)
    is_active : bool
    sensor_id: int | None = Field(default=None, foreign_key="sensor.id")
    key_fob_id: int | None = Field(default=None, foreign_key="Key_fob.id")
    door_id : int | None = Field(default=None, foreign_key="door.id")
    created_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True), onupdate=func.now(), nullable=True
        )
    )
    uid: Optional[UUID] = Field(
        sa_column=Column(
            UUIDSA(as_uuid=True),
            server_default=text("gen_random_uuid()")
        ), default=None
    )


class Door(SQLModel, table=True):
    __tablename__ = "door"
    id: Optional[int] = Field(default=None, primary_key=True)
    name : str
    accses_code : str






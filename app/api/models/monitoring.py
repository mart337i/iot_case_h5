from datetime import datetime
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
    __tablename__ = "alarms"
    __table_args__ = {'extend_existing': True}
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
    __tablename__ = "devicees"
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
    __tablename__ = "sensors"
    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: int
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
    __tablename__ = "readings"
    id: Optional[int] = Field(default=None, primary_key=True)
    value_type_id : int
    sensor_id : int
    value : any

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
    type : any
    
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
    __tablename__ = "employees"
    id: Optional[int] = Field(default=None, primary_key=True)
    name : str
    phone_number = int

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
    __tablename__ = "Key_fobs"
    id: Optional[int] = Field(default=None, primary_key=True)
    employe_id : int | None = Field(default=None, foreign_key="employee.id")
    is_active : bool
    key : str
    entryLog: list["EntryLog"] = Relationship()
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
    key_fob_id : int | None = Field(default=None, foreign_key="keyfob.id")    
    is_active : bool
    key : str
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







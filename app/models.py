from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Table, Text
from sqlalchemy.orm import relationship
from .database import Base
import enum

room_equipment = Table(
    'room_equipment',
    Base.metadata,
    Column('room_id', Integer, ForeignKey('rooms.id', ondelete='CASCADE'), primary_key=True),
    Column('equipment_id', Integer, ForeignKey('equipment.id', ondelete='CASCADE'), primary_key=True),
    Column('count', Integer, default=1, nullable=False),
    Column('condition', String, default='исправно'),
)

class BookingStatus(str, enum.Enum):
    ACTIVE = "активно"
    CANCELLED = "отменено"

class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True, index=True)
    capacity = Column(Integer, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    bookings = relationship("Booking", back_populates="room", cascade="all, delete-orphan")
    equipment = relationship("Equipment", secondary=room_equipment, back_populates="rooms")

class Equipment(Base):
    __tablename__ = "equipment"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    rooms = relationship("Room", secondary=room_equipment, back_populates="equipment")

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete='CASCADE'), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    user_name = Column(String(100), nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.ACTIVE, nullable=False)
    
    room = relationship("Room", back_populates="bookings")
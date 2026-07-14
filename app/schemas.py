from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional, List
from datetime import datetime, timezone

class EquipmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None

class EquipmentCreate(EquipmentBase):
    pass

class Equipment(EquipmentBase):
    id: int
    
    class Config:
        from_attributes = True

class RoomEquipmentBase(BaseModel):
    equipment_id: int = Field(gt=0)
    count: int = Field(default=1, ge=1)
    condition: str = Field(default="исправно", min_length=1)

class RoomEquipmentCreate(RoomEquipmentBase):
    pass

class RoomEquipment(RoomEquipmentBase):
    equipment: Equipment
    
    class Config:
        from_attributes = True

class RoomBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    capacity: int = Field(gt=0, le=1000)
    description: Optional[str] = None

class RoomCreate(RoomBase):
    equipment: List[RoomEquipmentCreate] = Field(default_factory=list)

class RoomUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    capacity: Optional[int] = Field(None, gt=0, le=1000)
    description: Optional[str] = None
    equipment: Optional[List[RoomEquipmentCreate]] = None

class Room(RoomBase):
    id: int
    equipment: List[Equipment] = Field(default_factory=list)
    
    class Config:
        from_attributes = True

class RoomWithDetails(Room):
    equipment_with_count: List[RoomEquipment] = Field(default_factory=list)
    
    class Config:
        from_attributes = True

class BookingBase(BaseModel):
    room_id: int = Field(gt=0)
    start_time: datetime
    end_time: datetime
    user_name: str = Field(min_length=2, max_length=100)

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v, info):
        """Проверка: конечная дата должна быть позже начальной"""
        start = info.data.get('start_time')
        if start is not None:
            v_naive = v.replace(tzinfo=None) if v.tzinfo is not None else v
            start_naive = start.replace(tzinfo=None) if start.tzinfo is not None else start
            if v_naive <= start_naive:
                raise ValueError('Конечная дата должна быть позже начальной')
        return v

class BookingCreate(BookingBase):
    """Схема для СОЗДАНИЯ бронирования (с проверкой на прошлое)"""
    
    @field_validator('start_time')
    @classmethod
    def validate_start_time(cls, v):
        """Проверка: нельзя бронировать в прошлом (только для создания)"""
        v_naive = v.replace(tzinfo=None) if v.tzinfo is not None else v
        now_naive = datetime.now()
        if v_naive < now_naive:
            raise ValueError('Нельзя бронировать в прошлом')
        return v


class Booking(BookingBase):
    """Схема для ОТВЕТА (без проверки на прошлое)"""
    id: int
    status: str
    
    class Config:
        from_attributes = True


class BookingWithRoom(Booking):
    """Бронирование с полной информацией о комнате"""
    room: Room
    
    class Config:
        from_attributes = True
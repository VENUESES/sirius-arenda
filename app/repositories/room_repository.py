from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import Room, Equipment, room_equipment, Booking, BookingStatus
from app.schemas import RoomCreate, RoomUpdate
from app.repositories.base import BaseRepository
from sqlalchemy import func

class RoomRepository(BaseRepository[Room, RoomCreate, RoomUpdate]):
    
    def __init__(self, db: Session):
        super().__init__(Room, db)
    
    def get_with_equipment(self, room_id: int) -> Optional[Room]:
        return self.db.query(Room).filter(Room.id == room_id).first()
    
    def get_by_name(self, name: str) -> Optional[Room]:
        return self.db.query(Room).filter(Room.name == name).first()
    
    def get_by_capacity(self, min_capacity: int, max_capacity: Optional[int] = None) -> List[Room]:
        query = self.db.query(Room).filter(Room.capacity >= min_capacity)
        if max_capacity:
            query = query.filter(Room.capacity <= max_capacity)
        return query.all()
    
    def get_available_rooms(
        self,
        start_time,
        end_time,
        capacity: Optional[int] = None,
        equipment_names: Optional[List[str]] = None
    ) -> List[Room]:
        booked = self.db.query(Booking.room_id).filter(
            and_(
                Booking.status == BookingStatus.ACTIVE,
                Booking.start_time < end_time,
                Booking.end_time > start_time
            )
        ).subquery()
        
        query = self.db.query(Room).filter(Room.id.not_in(booked))
        
        if capacity is not None:
            query = query.filter(Room.capacity >= capacity)
        
        if equipment_names is not None:
            eq_rooms = self.db.query(room_equipment.c.room_id).join(
                Equipment
            ).filter(
                Equipment.name.in_(equipment_names)
            ).group_by(
                room_equipment.c.room_id
            ).having(
                func.count(Equipment.id) == len(equipment_names)
            ).subquery()
            
            query = query.filter(Room.id.in_(eq_rooms))
        
        return query.all()
    
    def create_with_equipment(self, room_data: RoomCreate) -> Room:
        room = Room(
            name=room_data.name,
            capacity=room_data.capacity,
            description=room_data.description
        )
        self.db.add(room)
        self.db.flush()
        
        for eq_data in room_data.equipment:
            equipment = self.db.query(Equipment).filter(
                Equipment.id == eq_data.equipment_id
            ).first()
            if not equipment:
                self.db.rollback()
                raise ValueError(f"Equipment {eq_data.equipment_id} not found")
            
            self.db.execute(
                room_equipment.insert().values(
                    room_id=room.id,
                    equipment_id=eq_data.equipment_id,
                    count=eq_data.count,
                    condition=eq_data.condition
                )
            )
        
        self.db.commit()
        self.db.refresh(room)
        return room
    
    def update_with_equipment(self, room_id: int, room_data: RoomUpdate) -> Optional[Room]:
        room = self.get(room_id)
        if not room:
            return None
        
        if room_data.name is not None:
            room.name = room_data.name
        if room_data.capacity is not None:
            room.capacity = room_data.capacity
        if room_data.description is not None:
            room.description = room_data.description
        
        if room_data.equipment is not None:
            self.db.execute(
                room_equipment.delete().where(room_equipment.c.room_id == room_id)
            )
            
            for eq_data in room_data.equipment:
                equipment = self.db.query(Equipment).filter(
                    Equipment.id == eq_data.equipment_id
                ).first()
                if not equipment:
                    self.db.rollback()
                    raise ValueError(f"Equipment {eq_data.equipment_id} not found")
                
                self.db.execute(
                    room_equipment.insert().values(
                        room_id=room_id,
                        equipment_id=eq_data.equipment_id,
                        count=eq_data.count,
                        condition=eq_data.condition
                    )
                )
        
        self.db.commit()
        self.db.refresh(room)
        return room
from typing import Optional, List
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import Booking, Room, BookingStatus
from app.schemas import BookingCreate
from app.repositories.base import BaseRepository

class BookingRepository(BaseRepository[Booking, BookingCreate, BookingCreate]):
    
    def __init__(self, db: Session):
        super().__init__(Booking, db)
    
    def get_by_room_and_date(self, room_id: int, booking_date: date) -> List[Booking]:
        """Получить бронирования комнаты на день"""
        start = datetime.combine(booking_date, datetime.min.time())
        end = datetime.combine(booking_date, datetime.max.time())
        
        return self.db.query(Booking).filter(
            and_(
                Booking.room_id == room_id,
                Booking.start_time >= start,
                Booking.start_time <= end,
                Booking.status == BookingStatus.ACTIVE
            )
        ).order_by(Booking.start_time).all()
    
    def check_availability(self, room_id: int, start_time: datetime, end_time: datetime) -> bool:
        """Проверить, свободна ли комната в указанное время"""
        conflict = self.db.query(Booking).filter(
            and_(
                Booking.room_id == room_id,
                Booking.status == BookingStatus.ACTIVE,
                Booking.start_time < end_time,
                Booking.end_time > start_time
            )
        ).first()
        return conflict is None
    
    def get_conflicting_bookings(
        self,
        room_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[Booking]:
        """Получить все активные бронирования, которые пересекаются с указанным временем"""
        return self.db.query(Booking).filter(
            and_(
                Booking.room_id == room_id,
                Booking.status == BookingStatus.ACTIVE,
                Booking.start_time < end_time,
                Booking.end_time > start_time
            )
        ).order_by(Booking.start_time).all()
    def get_user_bookings(
        self,
        user_name: str,
        status: Optional[BookingStatus] = None
    ) -> List[Booking]:
        """Получить все бронирования пользователя"""
        query = self.db.query(Booking).filter(Booking.user_name == user_name)
        
        if status:
            query = query.filter(Booking.status == status)
        
        return query.order_by(Booking.start_time.desc()).all()
    
    def get_upcoming_bookings(self, room_id: Optional[int] = None) -> List[Booking]:
        """Получить предстоящие активные бронирования"""
        query = self.db.query(Booking).filter(
            and_(
                Booking.status == BookingStatus.ACTIVE,
                Booking.start_time > datetime.now()
            )
        )
        
        if room_id:
            query = query.filter(Booking.room_id == room_id)
        
        return query.order_by(Booking.start_time).all()
    
    def create_with_check(self, booking_data: BookingCreate) -> Optional[Booking]:
        """Создать бронирование с проверкой доступности"""
        room = self.db.query(Room).filter(Room.id == booking_data.room_id).first()
        if not room:
            raise ValueError("Room not found")
        
        if not self.check_availability(
            booking_data.room_id,
            booking_data.start_time,
            booking_data.end_time
        ):
            return None
        
        booking = Booking(**booking_data.model_dump())
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking
    
    def cancel(self, booking_id: int) -> Optional[Booking]:
        """Отменить бронирование"""
        booking = self.get(booking_id)
        if not booking:
            return None
        
        if booking.status == BookingStatus.CANCELLED:
            return booking
        
        booking.status = BookingStatus.CANCELLED
        self.db.commit()
        self.db.refresh(booking)
        return booking
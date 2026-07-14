from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional, List

from app.database import get_db
from app.repositories import BookingRepository, RoomRepository
from app.schemas import BookingCreate, Booking, BookingWithRoom
from app.models import BookingStatus

router = APIRouter(prefix="/bookings", tags=["Бронирования"])


@router.get("/", response_model=List[Booking])
def get_all_bookings(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    user_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Получить список всех бронирований.
    Поддерживает фильтрацию по статусу и имени пользователя.
    """
    repo = BookingRepository(db)
    
    if status:
        try:
            status_enum = BookingStatus(status)
            return repo.get_multi(skip=skip, limit=limit, filters={"status": status_enum})
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неверный статус. Допустимые: активно, отменено"
            )
    
    if user_name:
        return repo.get_user_bookings(user_name)
    
    return repo.get_multi(skip=skip, limit=limit)



@router.get("/{booking_id}", response_model=BookingWithRoom)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db)
):
    """
    Получить детальную информацию о бронировании с данными о комнате.
    """
    repo = BookingRepository(db)
    booking = repo.get(booking_id)
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Бронирование с ID {booking_id} не найдено"
        )
    
    return booking



@router.post("/", response_model=Booking, status_code=201)
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db)
):
    """
    Создать новое бронирование с проверкой доступности.
    Проверки:
    - Дата не должна быть в прошлом
    - Конечная дата должна быть позже начальной
    - Комната должна существовать
    - Комната не должна быть занята
    """
    if booking.start_time < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя бронировать в прошлом"
        )
    
    if booking.start_time >= booking.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Конечная дата должна быть позже начальной"
        )
    
    room_repo = RoomRepository(db)
    room = room_repo.get(booking.room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Комната с ID {booking.room_id} не найдена"
        )
    
    repo = BookingRepository(db)
    if not repo.check_availability(booking.room_id, booking.start_time, booking.end_time):
        conflicts = repo.get_conflicting_bookings(
            booking.room_id,
            booking.start_time,
            booking.end_time
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Комната уже занята на это время",
                "conflicts": [
                    {
                        "id": b.id,
                        "start_time": b.start_time.isoformat(),
                        "end_time": b.end_time.isoformat(),
                        "user_name": b.user_name
                    }
                    for b in conflicts
                ]
            }
        )
    
    new_booking = repo.create_with_check(booking)
    if not new_booking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Не удалось создать бронирование"
        )
    
    return new_booking



@router.delete("/{booking_id}", response_model=Booking)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db)
):
    """
    Отменить бронирование по ID.
    Статус меняется на "отменено".
    """
    repo = BookingRepository(db)
    
    booking = repo.cancel(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Бронирование с ID {booking_id} не найдено"
        )
    
    return booking



@router.get("/rooms/{room_id}/bookings", response_model=List[Booking])
def get_room_bookings(
    room_id: int,
    date: str,
    db: Session = Depends(get_db)
):
    """
    Получить все активные бронирования для комнаты на выбранную дату.
    """
    from datetime import date as date_type
    
    repo = BookingRepository(db)
    room_repo = RoomRepository(db)
    
    room = room_repo.get(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Комната с ID {room_id} не найдена"
        )
    
    try:
        booking_date = date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат даты. Используйте YYYY-MM-DD"
        )
    
    return repo.get_by_room_and_date(room_id, booking_date)
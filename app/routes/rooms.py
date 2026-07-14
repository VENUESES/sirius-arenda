from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.repositories.room_repository import RoomRepository
from app.repositories.equipment_repository import EquipmentRepository
from app.schemas import RoomCreate, RoomUpdate, Room, RoomWithDetails

router = APIRouter(prefix="/rooms", tags=["Комнаты"])

@router.get("/", response_model=List[Room])
def get_rooms(
    skip: int = Query(
        0, 
        ge=0, 
        description="Смещение для разделения на части (целое число ≥ 0)"
    ),
    limit: int = Query(
        100, 
        ge=1, 
        le=100, 
        description="Лимит записей (целое число от 1 до 100)"
    ),
    capacity: Optional[int] = Query(
        None, 
        ge=1, 
        le=1000,
        description="Минимальная вместимость (целое число ≥ 1 и ≤ 1000)"
    ),
    equipment: Optional[str] = Query(
        None, 
        description="Список оборудования через запятую (например: проектор,доска)"
    ),
    require_all: bool = Query(
        True, 
        description="Требовать всё оборудование или хотя бы одно"
    ),
    db: Session = Depends(get_db)
):
    """
    Получить список всех комнат с возможностью фильтрации:
    - По вместимости (capacity)
    - По оборудованию (equipment=проектор,доска)
    - require_all=true - нужны все указанные типы оборудования
    - require_all=false - достаточно любого
    """
    repo = RoomRepository(db)   
    
    if equipment:
        eq_list = [e.strip() for e in equipment.split(",")]
        return repo.get_with_equipment_names(eq_list, require_all)
    
    if capacity:
        return repo.get_by_capacity(capacity)
    
    return repo.get_multi(skip=skip, limit=limit)

@router.get("/available", response_model=List[RoomWithDetails])
def get_available_rooms(
    start: datetime = Query(..., description="Начало интервала (YYYY-MM-DDTHH:MM:SS)"),
    end: datetime = Query(..., description="Конец интервала (YYYY-MM-DDTHH:MM:SS)"),
    capacity: Optional[int] = Query(None, ge=1, description="Минимальная вместимость"),
    equipment: Optional[str] = Query(None, description="Список оборудования через запятую"),
    db: Session = Depends(get_db)
):
    """
    Поиск свободных комнат на указанное время.
    Возвращает комнаты, у которых нет пересекающихся бронирований.
    """
    if start >= end:
        raise HTTPException(
            status_code=400,
            detail="start_time must be before end_time"
        )
    
    repo = RoomRepository(db)
    eq_list = [e.strip() for e in equipment.split(",")] if equipment else None
    
    rooms = repo.get_available_rooms(start, end, capacity, eq_list)
    return rooms

@router.get("/{room_id}", response_model=RoomWithDetails)
def get_room(
    room_id: int,
    db: Session = Depends(get_db)
):
    """
    Получить детальную информацию о комнате
    """
    repo = RoomRepository(db)
    room = repo.get_with_equipment(room_id)
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return room

@router.post("/", response_model=RoomWithDetails, status_code=201)
def create_room(
    room: RoomCreate,
    db: Session = Depends(get_db)
):
    """
    Создать новую комнату с оборудованием
    """
    repo = RoomRepository(db)
    equipment_repo = EquipmentRepository(db)
    
    existing = repo.get_by_name(room.name)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Room with name '{room.name}' already exists"
        )
    
    if room.equipment:
        for eq_data in room.equipment:
            equipment = equipment_repo.get(eq_data.equipment_id)
            if not equipment:
                raise HTTPException(
                    status_code=404,
                    detail=f"Equipment with id {eq_data.equipment_id} not found"
                )
    
    try:
        return repo.create_with_equipment(room)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{room_id}", response_model=RoomWithDetails)
def update_room(
    room_id: int,
    room: RoomUpdate,
    db: Session = Depends(get_db)
):
    """
    Обновить данные о комнате и оборудовании
    """
    repo = RoomRepository(db)
    equipment_repo = EquipmentRepository(db)
    
    existing = repo.get(room_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.name and room.name != existing.name:
        name_exists = repo.get_by_name(room.name)
        if name_exists:
            raise HTTPException(
                status_code=409,
                detail=f"Room with name '{room.name}' already exists"
            )
    
    if room.equipment:
        for eq_data in room.equipment:
            equipment = equipment_repo.get(eq_data.equipment_id)
            if not equipment:
                raise HTTPException(
                    status_code=404,
                    detail=f"Equipment with id {eq_data.equipment_id} not found"
                )
    
    try:
        updated = repo.update_with_equipment(room_id, room)
        if not updated:
            raise HTTPException(status_code=404, detail="Room not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{room_id}", status_code=204)
def delete_room(
    room_id: int,
    db: Session = Depends(get_db)
):
    """
    Удалить комнату. Все связанные бронирования также будут удалены.
    """
    repo = RoomRepository(db)
    
    from app.repositories.booking_repository import BookingRepository
    booking_repo = BookingRepository(db)
    upcoming = booking_repo.get_upcoming_bookings(room_id)
    
    if upcoming:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete room with {len(upcoming)} active bookings"
        )
    
    if not repo.delete(room_id):
        raise HTTPException(status_code=404, detail="Room not found")
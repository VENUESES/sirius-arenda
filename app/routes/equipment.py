from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.repositories.equipment_repository import EquipmentRepository
from app.schemas import EquipmentCreate, Equipment

router = APIRouter(prefix="/equipment", tags=["Оборудование"])

@router.get("/", response_model=List[Equipment])
def get_equipment(
    skip: int = Query(0, ge=0, description="Смещение"),
    limit: int = Query(100, ge=1, le=100, description="Лимит"),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    db: Session = Depends(get_db)
):
    """
    Получить список всего оборудования с возможностью фильтрации.
    """
    repo = EquipmentRepository(db)
    
    if search:
        all_equipment = repo.get_multi(skip=skip, limit=limit)
        return [e for e in all_equipment if search.lower() in e.name.lower()]
    
    return repo.get_multi(skip=skip, limit=limit)

@router.post("/", response_model=Equipment, status_code=201)
def create_equipment(
    equipment: EquipmentCreate,
    db: Session = Depends(get_db)
):
    """
    Создать новое оборудование.
    """
    repo = EquipmentRepository(db)
    
    existing = repo.get_by_name(equipment.name)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Equipment '{equipment.name}' already exists"
        )
    
    return repo.create(equipment)

@router.get("/{equipment_id}", response_model=Equipment)
def get_equipment_by_id(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    """
    Получить детальную информацию об оборудовании.
    """
    repo = EquipmentRepository(db)
    equipment = repo.get(equipment_id)
    
    if not equipment:
        raise HTTPException(
            status_code=404,
            detail=f"Equipment with id {equipment_id} not found"
        )
    
    return equipment

@router.put("/{equipment_id}", response_model=Equipment)
def update_equipment(
    equipment_id: int,
    equipment: EquipmentCreate,
    db: Session = Depends(get_db)
):
    """
    Обновить данные об оборудовании.
    """
    repo = EquipmentRepository(db)
    
    existing = repo.get(equipment_id)
    if not existing:
        raise HTTPException(
            status_code=404,
            detail=f"Equipment with id {equipment_id} not found"
        )
    
    if equipment.name != existing.name:
        name_exists = repo.get_by_name(equipment.name)
        if name_exists:
            raise HTTPException(
                status_code=409,
                detail=f"Equipment '{equipment.name}' already exists"
            )
    
    updated = repo.update(equipment_id, equipment)
    return updated
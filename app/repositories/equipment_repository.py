from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import Equipment
from app.schemas import EquipmentCreate
from app.repositories.base import BaseRepository

class EquipmentRepository(BaseRepository[Equipment, EquipmentCreate, EquipmentCreate]):
    
    def __init__(self, db: Session):
        super().__init__(Equipment, db)
    
    def get_by_name(self, name: str) -> Optional[Equipment]:
        return self.db.query(Equipment).filter(Equipment.name == name).first()
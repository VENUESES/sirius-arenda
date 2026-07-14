from .rooms import router as rooms_router
from .bookings import router as bookings_router
from .equipment import router as equipment_router

__all__ = ["rooms_router", "bookings_router", "equipment_router"]
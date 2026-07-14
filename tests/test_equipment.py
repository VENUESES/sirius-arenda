import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_create_equipment():
    """Тест создания оборудования"""
    response = client.post("/equipment/", json={
        "name": "проектор",
        "description": "Full HD проектор"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "проектор"
    assert data["description"] == "Full HD проектор"
    assert data["id"] is not None

def test_create_duplicate_equipment():
    """Тест: нельзя создать оборудование с дублирующимся названием"""
    response1 = client.post("/equipment/", json={
        "name": "доска",
        "description": "Магнитная доска"
    })
    assert response1.status_code == 201
    
    response2 = client.post("/equipment/", json={
        "name": "доска",
        "description": "Другая доска"
    })
    assert response2.status_code == 409


def test_get_equipment_list():
    """Тест получения списка оборудования"""
    client.post("/equipment/", json={"name": "проектор", "description": "Full HD"})
    client.post("/equipment/", json={"name": "доска", "description": "Магнитная"})
    client.post("/equipment/", json={"name": "конференц-связь", "description": "Audio/Video"})
    
    response = client.get("/equipment/")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) >= 3
    names = [item["name"] for item in data]
    assert "проектор" in names
    assert "доска" in names
    assert "конференц-связь" in names
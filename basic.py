"""
Tests básicos para Chiknow
Ejecutar con: pytest tests/
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app import models

# Base de datos de test en memoria
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_temp.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Crea una sesión de base de datos de prueba"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Cliente de prueba de FastAPI"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# ============================================================================
# TESTS BÁSICOS
# ============================================================================

def test_health_check(client):
    """Test del endpoint de salud"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_home_page(client):
    """Test de la página principal"""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Chiknow" in response.content

def test_api_hsk_vacia(client):
    """Test de API HSK sin datos"""
    response = client.get("/api/hsk")
    assert response.status_code == 200
    assert response.json() == []

def test_crear_palabra_hsk(db_session):
    """Test de creación de palabra HSK"""
    palabra = models.HSK(
        id=1,
        numero=1,
        nivel=1,
        hanzi="你好",
        pinyin="nǐ hǎo",
        espanol="hola"
    )
    db_session.add(palabra)
    db_session.commit()
    
    result = db_session.query(models.HSK).filter(models.HSK.id == 1).first()
    assert result is not None
    assert result.hanzi == "你好"
    assert result.nivel == 1

def test_api_hsk_con_datos(client, db_session):
    """Test de API HSK con datos"""
    # Crear palabra de prueba
    palabra = models.HSK(
        id=1, numero=1, nivel=1,
        hanzi="你好", pinyin="nǐ hǎo", espanol="hola"
    )
    db_session.add(palabra)
    db_session.commit()
    
    # Probar API
    response = client.get("/api/hsk")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["hanzi"] == "你好"

def test_agregar_al_diccionario(client, db_session):
    """Test de agregar palabra al diccionario"""
    # Crear palabra
    palabra = models.HSK(id=1, numero=1, nivel=1, hanzi="你", pinyin="nǐ", espanol="tú")
    db_session.add(palabra)
    db_session.commit()
    
    # Agregar a diccionario
    response = client.post("/api/diccionario/add/1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    
    # Verificar que se creó entrada
    diccionario = db_session.query(models.Diccionario).filter(
        models.Diccionario.hsk_id == 1
    ).first()
    assert diccionario is not None
    
    # Verificar que se crearon 6 tarjetas
    tarjetas = db_session.query(models.Tarjeta).filter(
        models.Tarjeta.hsk_id == 1
    ).all()
    assert len(tarjetas) == 6

def test_eliminar_del_diccionario(client, db_session):
    """Test de eliminar palabra del diccionario"""
    # Crear palabra y entrada
    palabra = models.HSK(id=1, numero=1, nivel=1, hanzi="你", pinyin="nǐ", espanol="tú")
    diccionario = models.Diccionario(id=1, hsk_id=1, activo=True)
    db_session.add_all([palabra, diccionario])
    db_session.commit()
    
    # Eliminar
    response = client.delete("/api/diccionario/remove/1")
    assert response.status_code == 200
    
    # Verificar eliminación
    result = db_session.query(models.Diccionario).filter(
        models.Diccionario.id == 1
    ).first()
    assert result is None

def test_busqueda_hsk(client, db_session):
    """Test de búsqueda en HSK"""
    # Crear varias palabras
    palabras = [
        models.HSK(id=1, numero=1, nivel=1, hanzi="你", pinyin="nǐ", espanol="tú"),
        models.HSK(id=2, numero=2, nivel=1, hanzi="好", pinyin="hǎo", espanol="bien, bueno"),
        models.HSK(id=3, numero=3, nivel=1, hanzi="我", pinyin="wǒ", espanol="yo"),
    ]
    db_session.add_all(palabras)
    db_session.commit()
    
    # Buscar por hanzi
    response = client.get("/api/hsk/search?query=你")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["hanzi"] == "你"
    
    # Buscar por pinyin
    response = client.get("/api/hsk/search?query=hao")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    
    # Buscar por español
    response = client.get("/api/hsk/search?query=bien")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

def test_notas(client, db_session):
    """Test de sistema de notas"""
    # Crear palabra
    palabra = models.HSK(id=1, numero=1, nivel=1, hanzi="你", pinyin="nǐ", espanol="tú")
    db_session.add(palabra)
    db_session.commit()
    
    # Crear nota
    response = client.post(
        "/api/hsk/1/nota",
        json={"nota": "Esta es una nota de prueba"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    
    # Obtener nota
    response = client.get("/api/hsk/1/nota")
    assert response.status_code == 200
    data = response.json()
    assert data["nota"] == "Esta es una nota de prueba"
    
    # Eliminar nota
    response = client.delete("/api/hsk/1/nota")
    assert response.status_code == 200

# ============================================================================
# TESTS DE INTEGRACIÓN SM2
# ============================================================================

def test_sm2_session_flow(client, db_session):
    """Test del flujo completo de sesión SM2"""
    # 1. Crear palabra y agregarla al diccionario
    palabra = models.HSK(id=1, numero=1, nivel=1, hanzi="你", pinyin="nǐ", espanol="tú")
    diccionario = models.Diccionario(id=1, hsk_id=1, activo=True)
    tarjeta = models.Tarjeta(
        id=1, hsk_id=1, diccionario_id=1,
        mostrado1="你", mostrado2="nǐ", audio=True, requerido="tú", activa=True
    )
    db_session.add_all([palabra, diccionario, tarjeta])
    db_session.commit()
    
    # 2. Iniciar sesión
    response = client.post("/api/sm2/session/start")
    assert response.status_code == 200
    session_data = response.json()
    session_id = session_data["session_id"]
    
    # 3. Obtener tarjetas pendientes
    response = client.get("/api/sm2/cards/due?limite=20")
    assert response.status_code == 200
    cards = response.json()
    assert len(cards) > 0
    
    # 4. Responder tarjeta
    response = client.post(
        "/api/sm2/review",
        json={
            "tarjeta_id": 1,
            "session_id": session_id,
            "quality": 2,  # Easy
            "respuesta_usuario": "tú"
        }
    )
    assert response.status_code == 200
    review_data = response.json()
    assert review_data["success"] == True
    
    # 5. Finalizar sesión
    response = client.post(f"/api/sm2/session/end/{session_id}")
    assert response.status_code == 200

def test_sm2_statistics(client, db_session):
    """Test de estadísticas SM2"""
    response = client.get("/api/sm2/statistics")
    assert response.status_code == 200
    stats = response.json()
    assert "total_tarjetas" in stats
    assert "tarjetas_estudiadas" in stats
    assert "tarjetas_pendientes_hoy" in stats

# ============================================================================
# TESTS DE CONFIGURACIÓN
# ============================================================================

def test_database_config():
    """Test de configuración de base de datos"""
    from app.config import config
    
    assert config.DB_ENVIRONMENT in ["local", "produccion"]
    db_url = config.get_database_url()
    assert db_url is not None
    assert len(db_url) > 0

def test_models_structure():
    """Test de estructura de modelos"""
    # Verificar que todos los modelos tienen __tablename__
    models_to_check = [
        models.HSK, models.Notas, models.Diccionario, models.Tarjeta,
        models.Ejemplo, models.HSKEjemplo, models.SM2Session,
        models.SM2Progress, models.SM2Review
    ]
    
    for model in models_to_check:
        assert hasattr(model, '__tablename__')
        assert model.__tablename__ is not None

# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
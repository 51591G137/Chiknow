"""
Configuración global de pytest para Chiknow
"""
import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base


# Configuración de base de datos de prueba
TEST_DATABASE_URL = "sqlite:///./test_chiknow.db"


@pytest.fixture(scope="session")
def test_engine():
    """Motor de base de datos para tests"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Factory para crear sesiones de prueba"""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session(test_engine, test_session_factory):
    """
    Sesión de base de datos para cada test
    Se crea y destruye para cada test
    """
    # Crear todas las tablas
    Base.metadata.create_all(bind=test_engine)
    
    # Crear sesión
    session = test_session_factory()
    
    yield session
    
    # Limpiar
    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def reset_cache():
    """Limpia el caché antes de cada test"""
    from app.cache import invalidate_cache
    invalidate_cache()
    yield
    invalidate_cache()


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Configura logging para tests"""
    import logging
    
    # Reducir nivel de logging durante tests
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("app").setLevel(logging.WARNING)
    
    yield


@pytest.fixture
def mock_now_utc(monkeypatch):
    """Mock para now_utc() que retorna tiempo fijo"""
    from datetime import datetime, timezone
    from app import utils
    
    fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    def mock_now():
        return fixed_time
    
    monkeypatch.setattr(utils, "now_utc", mock_now)
    return fixed_time


# Markers personalizados
def pytest_configure(config):
    """Configuración de pytest"""
    config.addinivalue_line(
        "markers", "slow: marca tests que son lentos"
    )
    config.addinivalue_line(
        "markers", "integration: tests de integración"
    )
    config.addinivalue_line(
        "markers", "unit: tests unitarios"
    )


# Hooks de pytest
def pytest_collection_modifyitems(config, items):
    """Modifica items de colección antes de correr tests"""
    for item in items:
        # Agregar marker 'integration' a tests en test_api.py y test_sm2.py
        if "test_api" in item.nodeid or "test_sm2" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Agregar marker 'unit' a otros tests
        elif any(name in item.nodeid for name in ["test_utils", "test_schemas", "test_cache"]):
            item.add_marker(pytest.mark.unit)


# Fixtures para datos de prueba comunes
@pytest.fixture
def sample_hsk_word_data():
    """Datos de muestra para palabra HSK"""
    return {
        "numero": 1,
        "nivel": 1,
        "hanzi": "你",
        "pinyin": "nǐ",
        "espanol": "tú"
    }


@pytest.fixture
def sample_review_data():
    """Datos de muestra para review"""
    return {
        "tarjeta_id": 1,
        "session_id": 1,
        "quality": 2
    }


@pytest.fixture
def sample_nota_data():
    """Datos de muestra para nota"""
    return {
        "nota": "Esta es una nota de prueba"
    }


# Cleanup al final de la sesión
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_database():
    """Limpia base de datos de prueba al final"""
    yield
    
    # Eliminar archivo de base de datos de prueba si existe
    if os.path.exists("test_chiknow.db"):
        try:
            os.remove("test_chiknow.db")
        except:
            pass
    
    if os.path.exists("test.db"):
        try:
            os.remove("test.db")
        except:
            pass
    
    if os.path.exists("test_sm2.db"):
        try:
            os.remove("test_sm2.db")
        except:
            pass

"""
Tests de integración para el sistema SM2
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from app.main import app
from app.database import Base, get_db
from app import models, service


# Base de datos de prueba
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_sm2.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """Cliente de prueba"""
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Sesión de base de datos"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def word_in_diccionario(client, db_session):
    """Palabra agregada al diccionario con tarjetas"""
    # Crear palabra HSK
    word = models.HSK(
        numero=1,
        nivel=1,
        hanzi="你",
        pinyin="nǐ",
        espanol="tú"
    )
    db_session.add(word)
    db_session.commit()
    db_session.refresh(word)
    
    # Agregar al diccionario (genera tarjetas)
    response = client.post(f"/api/diccionario/add/{word.id}")
    assert response.status_code == 200
    
    return word


class TestSM2SessionEndpoints:
    """Tests para endpoints de sesión SM2"""
    
    def test_start_session(self, client):
        """Iniciar sesión de estudio"""
        response = client.post("/api/sm2/session/start")
        assert response.status_code == 200
        
        data = response.json()
        assert "session_id" in data
        assert "fecha_inicio" in data
        assert isinstance(data["session_id"], int)
    
    def test_end_session(self, client):
        """Finalizar sesión de estudio"""
        # Iniciar sesión
        start_response = client.post("/api/sm2/session/start")
        session_id = start_response.json()["session_id"]
        
        # Finalizar sesión
        response = client.post(f"/api/sm2/session/end/{session_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["session_id"] == session_id
        assert "tarjetas_estudiadas" in data
        assert data["tarjetas_estudiadas"] == 0  # No estudiamos nada


class TestSM2CardsEndpoints:
    """Tests para endpoints de tarjetas SM2"""
    
    def test_get_due_cards_empty(self, client):
        """Obtener tarjetas pendientes cuando no hay"""
        response = client.get("/api/sm2/cards/due")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_due_cards_with_new_cards(self, client, word_in_diccionario):
        """Obtener tarjetas pendientes con tarjetas nuevas"""
        response = client.get("/api/sm2/cards/due")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 6  # 6 tarjetas de la palabra
        
        # Verificar estructura de tarjeta
        card = data[0]
        assert "tarjeta_id" in card
        assert "tipo" in card
        assert "hanzi" in card
        assert "es_nueva" in card
        assert card["es_nueva"] is True
    
    def test_get_due_cards_with_limit(self, client, word_in_diccionario):
        """Obtener tarjetas con límite"""
        response = client.get("/api/sm2/cards/due?limite=3")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) <= 3


class TestSM2ReviewEndpoint:
    """Tests para endpoint de review"""
    
    def test_review_card_quality_0(self, client, word_in_diccionario):
        """Review con quality 0 (Again)"""
        # Iniciar sesión
        session_response = client.post("/api/sm2/session/start")
        session_id = session_response.json()["session_id"]
        
        # Obtener tarjeta
        cards_response = client.get("/api/sm2/cards/due?limite=1")
        card = cards_response.json()[0]
        
        # Review
        review_data = {
            "tarjeta_id": card["tarjeta_id"],
            "session_id": session_id,
            "quality": 0
        }
        response = client.post("/api/sm2/review", json=review_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["es_correcta"] is False
        assert data["nuevo_intervalo"] == 1
        assert data["nuevo_estado"] == "aprendiendo"
    
    def test_review_card_quality_1(self, client, word_in_diccionario):
        """Review con quality 1 (Hard)"""
        session_response = client.post("/api/sm2/session/start")
        session_id = session_response.json()["session_id"]
        
        cards_response = client.get("/api/sm2/cards/due?limite=1")
        card = cards_response.json()[0]
        
        review_data = {
            "tarjeta_id": card["tarjeta_id"],
            "session_id": session_id,
            "quality": 1
        }
        response = client.post("/api/sm2/review", json=review_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["es_correcta"] is True
        assert data["nuevo_intervalo"] >= 1
    
    def test_review_card_quality_2(self, client, word_in_diccionario):
        """Review con quality 2 (Easy)"""
        session_response = client.post("/api/sm2/session/start")
        session_id = session_response.json()["session_id"]
        
        cards_response = client.get("/api/sm2/cards/due?limite=1")
        card = cards_response.json()[0]
        
        review_data = {
            "tarjeta_id": card["tarjeta_id"],
            "session_id": session_id,
            "quality": 2
        }
        response = client.post("/api/sm2/review", json=review_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["es_correcta"] is True
        assert data["nuevo_intervalo"] >= 1
    
    def test_review_card_invalid_quality(self, client, word_in_diccionario):
        """Review con quality inválido"""
        session_response = client.post("/api/sm2/session/start")
        session_id = session_response.json()["session_id"]
        
        cards_response = client.get("/api/sm2/cards/due?limite=1")
        card = cards_response.json()[0]
        
        # Quality inválido (> 2)
        review_data = {
            "tarjeta_id": card["tarjeta_id"],
            "session_id": session_id,
            "quality": 5
        }
        response = client.post("/api/sm2/review", json=review_data)
        assert response.status_code == 422  # Validation error


class TestSM2Algorithm:
    """Tests para el algoritmo SM2"""
    
    def test_sm2_progression_easy_path(self, client, word_in_diccionario):
        """Progresión SM2 con respuestas Easy"""
        session_response = client.post("/api/sm2/session/start")
        session_id = session_response.json()["session_id"]
        
        cards_response = client.get("/api/sm2/cards/due?limite=1")
        card = cards_response.json()[0]
        tarjeta_id = card["tarjeta_id"]
        
        # Primera revisión - Easy (quality 2)
        review_data = {
            "tarjeta_id": tarjeta_id,
            "session_id": session_id,
            "quality": 2
        }
        response1 = client.post("/api/sm2/review", json=review_data)
        data1 = response1.json()
        
        assert data1["nuevo_intervalo"] == 1
        assert data1["nuevo_estado"] == "aprendiendo"
        
        # El intervalo debe ir aumentando con cada revisión Easy
        interval1 = data1["nuevo_intervalo"]
        
        # Segunda revisión (simular que pasó el tiempo)
        # En producción, la tarjeta no aparecería hasta que pase el intervalo
        # Pero para testing podemos forzarla
    
    def test_sm2_progression_again_resets(self, client, word_in_diccionario):
        """Quality 0 (Again) reinicia progreso"""
        session_response = client.post("/api/sm2/session/start")
        session_id = session_response.json()["session_id"]
        
        cards_response = client.get("/api/sm2/cards/due?limite=1")
        card = cards_response.json()[0]
        tarjeta_id = card["tarjeta_id"]
        
        # Primera revisión - Easy
        review_easy = {
            "tarjeta_id": tarjeta_id,
            "session_id": session_id,
            "quality": 2
        }
        client.post("/api/sm2/review", json=review_easy)
        
        # Segunda revisión - Again (olvido)
        review_again = {
            "tarjeta_id": tarjeta_id,
            "session_id": session_id,
            "quality": 0
        }
        response = client.post("/api/sm2/review", json=review_again)
        data = response.json()
        
        # Debe reiniciar a intervalo 1
        assert data["nuevo_intervalo"] == 1
        assert data["nuevo_estado"] == "aprendiendo"


class TestSM2Statistics:
    """Tests para estadísticas SM2"""
    
    def test_get_statistics_empty(self, client):
        """Estadísticas cuando no hay datos"""
        response = client.get("/api/sm2/statistics")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_tarjetas"] == 0
        assert data["tarjetas_estudiadas"] == 0
        assert data["tarjetas_nuevas"] == 0
    
    def test_get_statistics_with_cards(self, client, word_in_diccionario):
        """Estadísticas con tarjetas"""
        response = client.get("/api/sm2/statistics")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_tarjetas"] == 6
        assert data["tarjetas_nuevas"] == 6
    
    def test_get_statistics_after_review(self, client, word_in_diccionario):
        """Estadísticas después de revisar"""
        # Iniciar sesión y revisar una tarjeta
        session_response = client.post("/api/sm2/session/start")
        session_id = session_response.json()["session_id"]
        
        cards_response = client.get("/api/sm2/cards/due?limite=1")
        card = cards_response.json()[0]
        
        review_data = {
            "tarjeta_id": card["tarjeta_id"],
            "session_id": session_id,
            "quality": 2
        }
        client.post("/api/sm2/review", json=review_data)
        
        # Obtener estadísticas
        response = client.get("/api/sm2/statistics")
        data = response.json()
        
        assert data["total_revisiones"] == 1
    
    def test_get_progress_detailed(self, client, word_in_diccionario):
        """Progreso detallado"""
        response = client.get("/api/sm2/progress")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 6  # Al menos 6 tarjetas
        
        # Verificar estructura
        if len(data) > 0:
            card_progress = data[0]
            assert "tarjeta_id" in card_progress
            assert "facilidad" in card_progress
            assert "repeticiones" in card_progress
            assert "estado" in card_progress


class TestSM2Integration:
    """Tests de integración completa SM2"""
    
    def test_complete_study_session(self, client, word_in_diccionario):
        """Sesión de estudio completa"""
        # 1. Iniciar sesión
        session_response = client.post("/api/sm2/session/start")
        session_id = session_response.json()["session_id"]
        
        # 2. Obtener tarjetas pendientes
        cards_response = client.get("/api/sm2/cards/due?limite=3")
        cards = cards_response.json()
        assert len(cards) <= 3
        
        # 3. Revisar cada tarjeta
        for card in cards:
            review_data = {
                "tarjeta_id": card["tarjeta_id"],
                "session_id": session_id,
                "quality": 2  # Todas correctas
            }
            review_response = client.post("/api/sm2/review", json=review_data)
            assert review_response.status_code == 200
        
        # 4. Finalizar sesión
        end_response = client.post(f"/api/sm2/session/end/{session_id}")
        data = end_response.json()
        
        assert data["tarjetas_estudiadas"] == len(cards)
        assert data["correctas"] == len(cards)
        assert data["incorrectas"] == 0
        assert data["porcentaje_acierto"] == 100.0
    
    def test_mixed_quality_session(self, client, word_in_diccionario):
        """Sesión con calidades mixtas"""
        session_response = client.post("/api/sm2/session/start")
        session_id = session_response.json()["session_id"]
        
        cards_response = client.get("/api/sm2/cards/due?limite=3")
        cards = cards_response.json()
        
        qualities = [0, 1, 2]  # Again, Hard, Easy
        
        for i, card in enumerate(cards[:3]):
            review_data = {
                "tarjeta_id": card["tarjeta_id"],
                "session_id": session_id,
                "quality": qualities[i % 3]
            }
            client.post("/api/sm2/review", json=review_data)
        
        end_response = client.post(f"/api/sm2/session/end/{session_id}")
        data = end_response.json()
        
        # 1 incorrecta (quality 0), 2 correctas (quality 1 y 2)
        assert data["incorrectas"] == 1
        assert data["correctas"] == 2


class TestSM2EdgeCases:
    """Tests de casos límite SM2"""
    
    def test_review_nonexistent_card(self, client):
        """Revisar tarjeta inexistente"""
        session_response = client.post("/api/sm2/session/start")
        session_id = session_response.json()["session_id"]
        
        review_data = {
            "tarjeta_id": 999999,
            "session_id": session_id,
            "quality": 2
        }
        response = client.post("/api/sm2/review", json=review_data)
        assert response.status_code == 400
    
    def test_multiple_reviews_same_card(self, client, word_in_diccionario):
        """Múltiples reviews de la misma tarjeta"""
        session_response = client.post("/api/sm2/session/start")
        session_id = session_response.json()["session_id"]
        
        cards_response = client.get("/api/sm2/cards/due?limite=1")
        card = cards_response.json()[0]
        
        # Primera review
        review_data = {
            "tarjeta_id": card["tarjeta_id"],
            "session_id": session_id,
            "quality": 2
        }
        response1 = client.post("/api/sm2/review", json=review_data)
        data1 = response1.json()
        
        # Segunda review de la misma tarjeta
        response2 = client.post("/api/sm2/review", json=review_data)
        data2 = response2.json()
        
        # Ambas deben tener éxito
        assert data1["success"] is True
        assert data2["success"] is True
        
        # Pero el intervalo debe aumentar
        assert data2["nuevo_intervalo"] >= data1["nuevo_intervalo"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

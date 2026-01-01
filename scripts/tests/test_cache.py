"""
Tests unitarios para app/schemas.py - VERSIÓN CORREGIDA
"""
import pytest
from pydantic import ValidationError
from app.schemas import (
    ReviewRequest, NotaRequest, SearchQuery, HSKWordCreate,
    EjemploCreate, PaginationParams
)


class TestReviewRequest:
    """Tests para ReviewRequest schema"""
    
    def test_valid_review_request(self):
        """Crea ReviewRequest válido"""
        data = {
            "tarjeta_id": 1,
            "session_id": 1,
            "quality": 2
        }
        request = ReviewRequest(**data)
        
        assert request.tarjeta_id == 1
        assert request.session_id == 1
        assert request.quality == 2
        assert request.hanzi_fallados is None
        assert request.frase_fallada is False
    
    def test_quality_must_be_between_0_and_2(self):
        """Quality debe estar entre 0 y 2"""
        # Válido: 0, 1, 2
        for quality in [0, 1, 2]:
            data = {"tarjeta_id": 1, "session_id": 1, "quality": quality}
            request = ReviewRequest(**data)
            assert request.quality == quality
        
        # Inválido: -1, 3, 10
        for quality in [-1, 3, 10]:
            with pytest.raises(ValidationError) as exc_info:
                ReviewRequest(tarjeta_id=1, session_id=1, quality=quality)
            assert "quality" in str(exc_info.value)
    
    def test_tarjeta_id_must_be_positive(self):
        """tarjeta_id debe ser positivo"""
        with pytest.raises(ValidationError):
            ReviewRequest(tarjeta_id=0, session_id=1, quality=1)
        
        with pytest.raises(ValidationError):
            ReviewRequest(tarjeta_id=-1, session_id=1, quality=1)
    
    def test_session_id_must_be_positive(self):
        """session_id debe ser positivo"""
        with pytest.raises(ValidationError):
            ReviewRequest(tarjeta_id=1, session_id=0, quality=1)
    
    def test_respuesta_usuario_is_optional(self):
        """respuesta_usuario es opcional"""
        data = {"tarjeta_id": 1, "session_id": 1, "quality": 2}
        request = ReviewRequest(**data)
        assert request.respuesta_usuario is None
        
        data["respuesta_usuario"] = "mi respuesta"
        request = ReviewRequest(**data)
        assert request.respuesta_usuario == "mi respuesta"
    
    def test_respuesta_usuario_max_length(self):
        """respuesta_usuario tiene longitud máxima de 500 - rechaza si excede"""
        long_text = "a" * 600
        data = {
            "tarjeta_id": 1,
            "session_id": 1,
            "quality": 2,
            "respuesta_usuario": long_text
        }
        # Debe rechazar texto demasiado largo
        with pytest.raises(ValidationError) as exc_info:
            ReviewRequest(**data)
        assert "respuesta_usuario" in str(exc_info.value)
        
        # Texto de exactamente 500 caracteres debe pasar
        valid_data = data.copy()
        valid_data["respuesta_usuario"] = "a" * 500
        request = ReviewRequest(**valid_data)
        assert len(request.respuesta_usuario) == 500
    
    def test_hanzi_fallados_validation(self):
        """hanzi_fallados se limita a 20 elementos - rechaza si excede"""
        many_hanzi = ["我"] * 25
        data = {
            "tarjeta_id": 1,
            "session_id": 1,
            "quality": 0,
            "hanzi_fallados": many_hanzi
        }
        # Debe rechazar lista demasiado larga
        with pytest.raises(ValidationError):
            ReviewRequest(**data)
        
        # Exactamente 20 debe pasar
        valid_data = data.copy()
        valid_data["hanzi_fallados"] = ["我"] * 20
        request = ReviewRequest(**valid_data)
        assert len(request.hanzi_fallados) == 20


class TestNotaRequest:
    """Tests para NotaRequest schema"""
    
    def test_valid_nota_request(self):
        """Crea NotaRequest válido"""
        request = NotaRequest(nota="Esta es una nota")
        assert request.nota == "Esta es una nota"
    
    def test_nota_is_required(self):
        """nota es requerida"""
        with pytest.raises(ValidationError):
            NotaRequest()
    
    def test_nota_min_length(self):
        """nota debe tener al menos 1 carácter"""
        with pytest.raises(ValidationError):
            NotaRequest(nota="")
    
    def test_nota_max_length(self):
        """nota tiene longitud máxima de 2000 - rechaza si excede"""
        long_nota = "a" * 2500
        # Debe rechazar nota demasiado larga
        with pytest.raises(ValidationError) as exc_info:
            NotaRequest(nota=long_nota)
        assert "nota" in str(exc_info.value)
        
        # Exactamente 2000 debe pasar
        valid_nota = "a" * 2000
        request = NotaRequest(nota=valid_nota)
        assert len(request.nota) == 2000
    
    def test_nota_trimmed(self):
        """nota se recorta (trim)"""
        request = NotaRequest(nota="  nota con espacios  ")
        assert request.nota == "nota con espacios"


class TestSearchQuery:
    """Tests para SearchQuery schema"""
    
    def test_valid_search_query(self):
        """Crea SearchQuery válido"""
        query = SearchQuery(query="你好")
        assert query.query == "你好"
    
    def test_query_is_required(self):
        """query es requerido"""
        with pytest.raises(ValidationError):
            SearchQuery()
    
    def test_query_min_length(self):
        """query debe tener al menos 1 carácter"""
        with pytest.raises(ValidationError):
            SearchQuery(query="")
    
    def test_query_max_length(self):
        """query tiene longitud máxima de 100 - rechaza si excede"""
        long_query = "a" * 150
        # Debe rechazar query demasiado largo
        with pytest.raises(ValidationError) as exc_info:
            SearchQuery(query=long_query)
        assert "query" in str(exc_info.value)
        
        # Exactamente 100 debe pasar
        valid_query = "a" * 100
        query = SearchQuery(query=valid_query)
        assert len(query.query) == 100
    
    def test_dangerous_characters_rejected(self):
        """Rechaza caracteres SQL peligrosos"""
        dangerous_queries = [
            "hello; DROP TABLE",
            "test--comment",
            "/* comment */",
            "xp_cmdshell",
            "DELETE FROM"
        ]
        
        for dangerous in dangerous_queries:
            with pytest.raises(ValidationError) as exc_info:
                SearchQuery(query=dangerous)
            assert "no permitida" in str(exc_info.value).lower()
    
    def test_safe_queries_accepted(self):
        """Acepta queries seguros"""
        safe_queries = ["你好", "hello", "nǐ hǎo", "test123", "José"]
        
        for safe in safe_queries:
            query = SearchQuery(query=safe)
            assert query.query == safe


class TestHSKWordCreate:
    """Tests para HSKWordCreate schema"""
    
    def test_valid_hsk_word(self):
        """Crea HSKWordCreate válido"""
        data = {
            "numero": 1,
            "nivel": 1,
            "hanzi": "你",
            "pinyin": "nǐ",
            "espanol": "tú"
        }
        word = HSKWordCreate(**data)
        
        assert word.numero == 1
        assert word.nivel == 1
        assert word.hanzi == "你"
    
    def test_nivel_must_be_between_1_and_6(self):
        """nivel debe estar entre 1 y 6"""
        for nivel in [1, 2, 3, 4, 5, 6]:
            data = {
                "numero": 1,
                "nivel": nivel,
                "hanzi": "你",
                "pinyin": "nǐ",
                "espanol": "tú"
            }
            word = HSKWordCreate(**data)
            assert word.nivel == nivel
        
        # Inválido
        with pytest.raises(ValidationError):
            HSKWordCreate(numero=1, nivel=0, hanzi="你", pinyin="nǐ", espanol="tú")
        
        with pytest.raises(ValidationError):
            HSKWordCreate(numero=1, nivel=7, hanzi="你", pinyin="nǐ", espanol="tú")
    
    def test_numero_must_be_positive(self):
        """numero debe ser positivo"""
        with pytest.raises(ValidationError):
            HSKWordCreate(numero=0, nivel=1, hanzi="你", pinyin="nǐ", espanol="tú")
    
    def test_optional_fields(self):
        """Campos opcionales funcionan correctamente"""
        data = {
            "numero": 1,
            "nivel": 1,
            "hanzi": "你",
            "pinyin": "nǐ",
            "espanol": "tú",
            "hanzi_alt": "妳",
            "pinyin_alt": "nǐ",
            "categoria": "pronombre"
        }
        word = HSKWordCreate(**data)
        
        assert word.hanzi_alt == "妳"
        assert word.pinyin_alt == "nǐ"
        assert word.categoria == "pronombre"


class TestEjemploCreate:
    """Tests para EjemploCreate schema"""
    
    def test_valid_ejemplo(self):
        """Crea EjemploCreate válido"""
        data = {
            "hanzi": "我喝茶",
            "pinyin": "wǒ hē chá",
            "espanol": "Yo bebo té",
            "hanzi_ids": [1, 2, 3]
        }
        ejemplo = EjemploCreate(**data)
        
        assert ejemplo.hanzi == "我喝茶"
        assert ejemplo.nivel == 1  # default
        assert ejemplo.complejidad == 1  # default
    
    def test_hanzi_ids_required(self):
        """hanzi_ids es requerido"""
        with pytest.raises(ValidationError):
            EjemploCreate(
                hanzi="我喝茶",
                pinyin="wǒ hē chá",
                espanol="Yo bebo té"
            )
    
    def test_hanzi_ids_min_items(self):
        """hanzi_ids debe tener al menos 1 elemento"""
        with pytest.raises(ValidationError):
            EjemploCreate(
                hanzi="我喝茶",
                pinyin="wǒ hē chá",
                espanol="Yo bebo té",
                hanzi_ids=[]
            )
    
    def test_hanzi_ids_max_items(self):
        """hanzi_ids se limita a 20 elementos - rechaza si excede"""
        many_ids = list(range(1, 25))
        data = {
            "hanzi": "我喝茶",
            "pinyin": "wǒ hē chá",
            "espanol": "Yo bebo té",
            "hanzi_ids": many_ids
        }
        # Debe rechazar lista demasiado larga
        with pytest.raises(ValidationError):
            EjemploCreate(**data)
        
        # Exactamente 20 debe pasar
        valid_data = data.copy()
        valid_data["hanzi_ids"] = list(range(1, 21))
        ejemplo = EjemploCreate(**valid_data)
        assert len(ejemplo.hanzi_ids) == 20
    
    def test_hanzi_ids_must_be_positive(self):
        """Todos los IDs deben ser positivos"""
        with pytest.raises(ValidationError) as exc_info:
            EjemploCreate(
                hanzi="我喝茶",
                pinyin="wǒ hē chá",
                espanol="Yo bebo té",
                hanzi_ids=[1, -1, 3]
            )
        assert "positivos" in str(exc_info.value)


class TestPaginationParams:
    """Tests para PaginationParams schema"""
    
    def test_valid_pagination(self):
        """Crea PaginationParams válido"""
        params = PaginationParams(skip=10, limit=50)
        assert params.skip == 10
        assert params.limit == 50
        assert params.offset == 10  # alias
    
    def test_default_values(self):
        """Usa valores por defecto correctos"""
        params = PaginationParams()
        assert params.skip == 0
        assert params.limit == 100
    
    def test_skip_must_be_non_negative(self):
        """skip debe ser >= 0"""
        params = PaginationParams(skip=0)
        assert params.skip == 0
        
        with pytest.raises(ValidationError):
            PaginationParams(skip=-1)
    
    def test_limit_bounds(self):
        """limit debe estar entre 1 y 500"""
        # Válido
        params = PaginationParams(limit=1)
        assert params.limit == 1
        
        params = PaginationParams(limit=500)
        assert params.limit == 500
        
        # Inválido
        with pytest.raises(ValidationError):
            PaginationParams(limit=0)
        
        with pytest.raises(ValidationError):
            PaginationParams(limit=501)
    
    def test_offset_property(self):
        """Propiedad offset es alias de skip"""
        params = PaginationParams(skip=25)
        assert params.offset == params.skip


class TestSchemasIntegration:
    """Tests de integración entre schemas"""
    
    def test_review_with_hanzi_fallados(self):
        """ReviewRequest con hanzi_fallados funciona correctamente"""
        data = {
            "tarjeta_id": 1,
            "session_id": 1,
            "quality": 0,
            "hanzi_fallados": ["我", "你", "他"],
            "frase_fallada": True,
            "respuesta_usuario": "我 ni 他"
        }
        request = ReviewRequest(**data)
        
        assert len(request.hanzi_fallados) == 3
        assert request.frase_fallada is True
        assert request.respuesta_usuario is not None
    
    def test_ejemplo_with_pagination(self):
        """EjemploCreate con paginación"""
        ejemplo = EjemploCreate(
            hanzi="我喝茶",
            pinyin="wǒ hē chá",
            espanol="Yo bebo té",
            hanzi_ids=[1, 2, 3]
        )
        
        pagination = PaginationParams(skip=0, limit=10)
        
        assert ejemplo.hanzi_ids == [1, 2, 3]
        assert pagination.limit == 10


# Fixtures
@pytest.fixture
def valid_review_data():
    """Datos válidos para ReviewRequest"""
    return {
        "tarjeta_id": 1,
        "session_id": 1,
        "quality": 2
    }


@pytest.fixture
def valid_hsk_data():
    """Datos válidos para HSKWordCreate"""
    return {
        "numero": 1,
        "nivel": 1,
        "hanzi": "你",
        "pinyin": "nǐ",
        "espanol": "tú"
    }


class TestSchemasWithFixtures:
    """Tests usando fixtures"""
    
    def test_create_multiple_reviews(self, valid_review_data):
        """Crea múltiples ReviewRequest con mismos datos"""
        requests = [ReviewRequest(**valid_review_data) for _ in range(5)]
        assert len(requests) == 5
        assert all(r.quality == 2 for r in requests)
    
    def test_modify_hsk_data(self, valid_hsk_data):
        """Modifica datos HSK y crea diferentes palabras"""
        words = []
        for i in range(3):
            data = valid_hsk_data.copy()
            data["numero"] = i + 1
            words.append(HSKWordCreate(**data))
        
        assert len(words) == 3
        assert [w.numero for w in words] == [1, 2, 3]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
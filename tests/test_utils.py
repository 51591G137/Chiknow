"""
Tests unitarios para app/utils.py
"""
import pytest
from datetime import datetime, timezone, timedelta
from app.utils import now_utc, normalize_text, sanitize_input, format_interval_display


class TestNowUtc:
    """Tests para la función now_utc()"""
    
    def test_returns_datetime_with_timezone(self):
        """Verifica que retorna datetime con timezone UTC"""
        result = now_utc()
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
    
    def test_returns_current_time(self):
        """Verifica que retorna tiempo actual (dentro de 1 segundo)"""
        before = datetime.now(timezone.utc)
        result = now_utc()
        after = datetime.now(timezone.utc)
        
        assert before <= result <= after
    
    def test_consistent_timezone(self):
        """Verifica que múltiples llamadas usan el mismo timezone"""
        time1 = now_utc()
        time2 = now_utc()
        
        assert time1.tzinfo == time2.tzinfo
        assert time1.tzinfo == timezone.utc


class TestNormalizeText:
    """Tests para la función normalize_text()"""
    
    def test_removes_accents_spanish(self):
        """Remueve acentos en español"""
        assert normalize_text("José María") == "Jose Maria"
        assert normalize_text("niño") == "nino"
        assert normalize_text("México") == "Mexico"
    
    def test_removes_accents_pinyin(self):
        """Remueve tonos en pinyin"""
        assert normalize_text("nǐ hǎo") == "ni hao"
        assert normalize_text("xièxie") == "xiexie"
        assert normalize_text("Běijīng") == "Beijing"
    
    def test_preserves_non_accented_text(self):
        """Preserva texto sin acentos"""
        assert normalize_text("hello world") == "hello world"
        assert normalize_text("123 abc") == "123 abc"
    
    def test_handles_empty_string(self):
        """Maneja string vacío"""
        assert normalize_text("") == ""
    
    def test_handles_none(self):
        """Maneja None"""
        assert normalize_text(None) == ""
    
    def test_preserves_chinese_characters(self):
        """Preserva caracteres chinos (no tienen acentos diacríticos)"""
        assert normalize_text("你好") == "你好"
        assert normalize_text("中文") == "中文"


class TestSanitizeInput:
    """Tests para la función sanitize_input()"""
    
    def test_trims_whitespace(self):
        """Elimina espacios al inicio y final"""
        assert sanitize_input("  hello  ") == "hello"
        assert sanitize_input("\n\ttest\n") == "test"
    
    def test_limits_length(self):
        """Limita longitud al máximo especificado"""
        long_text = "a" * 1000
        result = sanitize_input(long_text, max_length=100)
        assert len(result) == 100
    
    def test_default_max_length(self):
        """Usa max_length por defecto de 500"""
        long_text = "a" * 600
        result = sanitize_input(long_text)
        assert len(result) == 500
    
    def test_removes_dangerous_characters(self):
        """Remueve caracteres peligrosos"""
        assert sanitize_input("hello\x00world") == "helloworld"
        assert sanitize_input("test\r\n\n\nmore") == "testmore"
    
    def test_handles_empty_string(self):
        """Maneja string vacío"""
        assert sanitize_input("") == ""
    
    def test_handles_none(self):
        """Maneja None"""
        assert sanitize_input(None) == ""
    
    def test_preserves_normal_text(self):
        """Preserva texto normal sin modificar"""
        text = "Hello, this is a normal text!"
        assert sanitize_input(text) == text


class TestFormatIntervalDisplay:
    """Tests para la función format_interval_display()"""
    
    def test_less_than_one_day(self):
        """Formatea intervalos menores a 1 día"""
        assert format_interval_display(0) == "<1d"
    
    def test_days(self):
        """Formatea días"""
        assert format_interval_display(1) == "1d"
        assert format_interval_display(15) == "15d"
        assert format_interval_display(29) == "29d"
    
    def test_months(self):
        """Formatea meses"""
        assert format_interval_display(30) == "1m"
        assert format_interval_display(60) == "2m"
        assert format_interval_display(180) == "6m"
        assert format_interval_display(364) == "12m"
    
    def test_years(self):
        """Formatea años"""
        assert format_interval_display(365) == "1y"
        assert format_interval_display(730) == "2y"
        assert format_interval_display(1095) == "3y"
    
    def test_boundary_cases(self):
        """Casos límite"""
        assert format_interval_display(29) == "29d"
        assert format_interval_display(30) == "1m"
        assert format_interval_display(364) == "12m"
        assert format_interval_display(365) == "1y"


class TestUtilsIntegration:
    """Tests de integración entre funciones de utils"""
    
    def test_normalize_and_sanitize_together(self):
        """normalize_text y sanitize_input trabajan juntos"""
        text = "  José María\x00  "
        normalized = normalize_text(text)
        sanitized = sanitize_input(normalized)
        assert sanitized == "Jose Maria"
    
    def test_timezone_consistency_in_operations(self):
        """Múltiples operaciones mantienen timezone consistente"""
        times = [now_utc() for _ in range(10)]
        assert all(t.tzinfo == timezone.utc for t in times)
        
        # Verificar que están en orden cronológico (o muy cerca)
        for i in range(len(times) - 1):
            assert times[i] <= times[i + 1]


# Fixtures para tests
@pytest.fixture
def sample_texts():
    """Textos de muestra para tests"""
    return {
        "spanish": "José, María y Ángel",
        "pinyin": "nǐ hǎo, xièxie",
        "chinese": "你好世界",
        "mixed": "Hello 世界 nǐ hǎo José",
        "empty": "",
        "whitespace": "   \n\t   "
    }


class TestUtilsWithFixtures:
    """Tests usando fixtures"""
    
    def test_normalize_all_samples(self, sample_texts):
        """Normaliza todos los textos de muestra"""
        results = {
            key: normalize_text(text) 
            for key, text in sample_texts.items()
        }
        
        assert results["spanish"] == "Jose, Maria y Angel"
        assert results["pinyin"] == "ni hao, xiexie"
        assert results["chinese"] == "你好世界"
        assert "Jose" in results["mixed"]
    
    def test_sanitize_all_samples(self, sample_texts):
        """Sanitiza todos los textos de muestra"""
        results = {
            key: sanitize_input(text)
            for key, text in sample_texts.items()
        }
        
        assert results["spanish"] == "José, María y Ángel"
        assert results["empty"] == ""
        assert results["whitespace"] == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

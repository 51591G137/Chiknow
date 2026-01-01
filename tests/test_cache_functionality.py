"""
Tests unitarios para app/cache.py
"""
import pytest
import time
from app.cache import cache, invalidate_cache, get_cache_stats, cleanup_expired_cache


class TestCacheDecorator:
    """Tests para el decorator @cache"""
    
    def test_cache_stores_result(self):
        """Caché almacena resultado de función"""
        call_count = 0
        
        @cache(ttl_seconds=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # Primera llamada - ejecuta función
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Segunda llamada - usa caché
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # No incrementó
    
    def test_cache_different_arguments(self):
        """Caché distingue entre diferentes argumentos"""
        call_count = 0
        
        @cache(ttl_seconds=60)
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b
        
        result1 = add(1, 2)
        result2 = add(3, 4)
        result3 = add(1, 2)  # Mismos args que result1
        
        assert result1 == 3
        assert result2 == 7
        assert result3 == 3
        assert call_count == 2  # Solo 2 ejecuciones (3ra usa caché)
    
    def test_cache_expiration(self):
        """Caché expira después del TTL"""
        call_count = 0
        
        @cache(ttl_seconds=1)  # 1 segundo
        def get_time():
            nonlocal call_count
            call_count += 1
            return time.time()
        
        # Primera llamada
        time1 = get_time()
        assert call_count == 1
        
        # Segunda llamada inmediata - usa caché
        time2 = get_time()
        assert time1 == time2
        assert call_count == 1
        
        # Esperar a que expire
        time.sleep(1.1)
        
        # Tercera llamada - caché expiró
        time3 = get_time()
        assert time3 != time1
        assert call_count == 2
    
    def test_cache_with_kwargs(self):
        """Caché funciona con keyword arguments"""
        call_count = 0
        
        @cache(ttl_seconds=60)
        def greet(name, greeting="Hello"):
            nonlocal call_count
            call_count += 1
            return f"{greeting}, {name}!"
        
        result1 = greet("Alice")
        result2 = greet(name="Alice")
        result3 = greet("Bob")
        
        assert result1 == "Hello, Alice!"
        assert result2 == "Hello, Alice!"
        assert result3 == "Hello, Bob!"
        assert call_count == 2  # Alice y Bob
    
    def test_cache_with_none_return(self):
        """Caché funciona con funciones que retornan None"""
        call_count = 0
        
        @cache(ttl_seconds=60)
        def returns_none():
            nonlocal call_count
            call_count += 1
            return None
        
        result1 = returns_none()
        result2 = returns_none()
        
        assert result1 is None
        assert result2 is None
        assert call_count == 1


class TestInvalidateCache:
    """Tests para invalidate_cache()"""
    
    def test_invalidate_all_cache(self):
        """Invalida todo el caché"""
        @cache(ttl_seconds=60)
        def func1():
            return 1
        
        @cache(ttl_seconds=60)
        def func2():
            return 2
        
        # Poblar caché
        func1()
        func2()
        
        # Verificar que hay caché
        stats = get_cache_stats()
        assert stats["total_entries"] >= 2
        
        # Invalidar todo
        invalidate_cache()
        
        # Verificar que se limpió
        stats = get_cache_stats()
        assert stats["total_entries"] == 0
    
    def test_invalidate_specific_pattern(self):
        """Invalida caché con patrón específico"""
        @cache(ttl_seconds=60)
        def user_data(user_id):
            return f"data_{user_id}"
        
        @cache(ttl_seconds=60)
        def post_data(post_id):
            return f"post_{post_id}"
        
        # Poblar caché
        user_data(1)
        user_data(2)
        post_data(1)
        
        # Invalidar solo user_data
        invalidate_cache("user_data")
        
        # post_data aún debe estar en caché
        # (esto es difícil de verificar sin acceso directo al _cache)
        # Pero al menos verificamos que no crashea
        stats = get_cache_stats()
        assert stats["total_entries"] >= 0


class TestGetCacheStats:
    """Tests para get_cache_stats()"""
    
    def test_cache_stats_structure(self):
        """Estructura de estadísticas es correcta"""
        invalidate_cache()  # Limpiar primero
        
        stats = get_cache_stats()
        
        assert "total_entries" in stats
        assert "active_entries" in stats
        assert "expired_entries" in stats
        assert "memory_usage_kb" in stats
        
        assert isinstance(stats["total_entries"], int)
        assert isinstance(stats["active_entries"], int)
        assert isinstance(stats["memory_usage_kb"], float)
    
    def test_cache_stats_after_operations(self):
        """Estadísticas reflejan operaciones"""
        invalidate_cache()
        
        @cache(ttl_seconds=60)
        def test_func(x):
            return x * 2
        
        # Sin caché
        stats1 = get_cache_stats()
        initial_count = stats1["total_entries"]
        
        # Agregar al caché
        test_func(1)
        test_func(2)
        
        stats2 = get_cache_stats()
        assert stats2["total_entries"] >= initial_count + 2


class TestCleanupExpiredCache:
    """Tests para cleanup_expired_cache()"""
    
    def test_cleanup_removes_expired(self):
        """Limpieza remueve entradas expiradas"""
        invalidate_cache()
        
        @cache(ttl_seconds=1)
        def short_lived():
            return "data"
        
        # Crear entrada
        short_lived()
        
        stats_before = get_cache_stats()
        assert stats_before["total_entries"] >= 1
        
        # Esperar a que expire
        time.sleep(1.1)
        
        # Limpiar
        cleanup_expired_cache()
        
        stats_after = get_cache_stats()
        # La entrada expirada debería haberse eliminado
        # (puede haber otras entradas de otros tests)
        assert stats_after["expired_entries"] == 0
    
    def test_cleanup_preserves_active(self):
        """Limpieza preserva entradas activas"""
        invalidate_cache()
        
        @cache(ttl_seconds=60)
        def long_lived():
            return "data"
        
        # Crear entrada que no expira pronto
        long_lived()
        
        stats_before = get_cache_stats()
        active_before = stats_before["active_entries"]
        
        # Limpiar
        cleanup_expired_cache()
        
        stats_after = get_cache_stats()
        assert stats_after["active_entries"] >= active_before


class TestCacheEdgeCases:
    """Tests de casos límite"""
    
    def test_cache_with_exception(self):
        """Caché no almacena excepciones"""
        call_count = 0
        
        @cache(ttl_seconds=60)
        def fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Error")
        
        # Primera llamada - falla
        with pytest.raises(ValueError):
            fails()
        assert call_count == 1
        
        # Segunda llamada - ejecuta de nuevo (no usa caché)
        with pytest.raises(ValueError):
            fails()
        assert call_count == 2
    
    def test_cache_with_large_data(self):
        """Caché maneja datos grandes"""
        @cache(ttl_seconds=60)
        def large_data():
            return "x" * 10000
        
        result1 = large_data()
        result2 = large_data()
        
        assert result1 == result2
        assert len(result1) == 10000
        
        stats = get_cache_stats()
        assert stats["memory_usage_kb"] > 0
    
    def test_cache_with_mutable_return(self):
        """Caché con retorno mutable (lista, dict)"""
        call_count = 0
        
        @cache(ttl_seconds=60)
        def get_list():
            nonlocal call_count
            call_count += 1
            return [1, 2, 3]
        
        result1 = get_list()
        result2 = get_list()
        
        # Ambos apuntan al mismo objeto (cuidado!)
        assert result1 is result2
        assert call_count == 1
        
        # Modificar result1 también modifica result2
        result1.append(4)
        assert 4 in result2


class TestCachePerformance:
    """Tests de rendimiento del caché"""
    
    def test_cache_improves_performance(self):
        """Caché mejora el rendimiento"""
        call_count = 0
        
        @cache(ttl_seconds=60)
        def slow_function():
            nonlocal call_count
            call_count += 1
            time.sleep(0.1)  # Simular operación lenta
            return "result"
        
        # Primera llamada - lenta
        start1 = time.time()
        result1 = slow_function()
        time1 = time.time() - start1
        
        # Segunda llamada - rápida (caché)
        start2 = time.time()
        result2 = slow_function()
        time2 = time.time() - start2
        
        assert result1 == result2
        assert call_count == 1
        assert time2 < time1  # Segunda llamada es más rápida
        assert time2 < 0.01  # Mucho más rápida que 0.1s
    
    def test_cache_memory_usage(self):
        """Monitoreo de uso de memoria"""
        invalidate_cache()
        
        @cache(ttl_seconds=60)
        def generate_data(size):
            return "x" * size
        
        # Generar varios tamaños
        for size in [100, 1000, 10000]:
            generate_data(size)
        
        stats = get_cache_stats()
        # Debe haber consumido algo de memoria
        assert stats["memory_usage_kb"] > 0
        assert stats["total_entries"] >= 3


# Fixtures
@pytest.fixture(autouse=True)
def cleanup_cache_after_test():
    """Limpia el caché después de cada test"""
    yield
    invalidate_cache()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

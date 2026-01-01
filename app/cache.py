"""
Sistema de caché para Chiknow
Soporta caché en memoria (desarrollo) y Redis (producción)
"""
from functools import wraps
import json
import hashlib
from typing import Any, Optional, Callable
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Caché en memoria (desarrollo)
_cache = {}
_cache_expiry = {}


def get_cache_key(*args, **kwargs) -> str:
    """
    Genera clave de caché única basada en argumentos
    
    Args:
        *args: Argumentos posicionales
        **kwargs: Argumentos con nombre
        
    Returns:
        str: Hash MD5 de los argumentos
    """
    try:
        key_data = json.dumps({
            "args": [str(arg) for arg in args],
            "kwargs": {k: str(v) for k, v in kwargs.items()}
        }, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    except Exception as e:
        logger.warning(f"Error generando cache key: {e}")
        return hashlib.md5(str(datetime.now()).encode()).hexdigest()


def cache(ttl_seconds: int = 300):
    """
    Decorator para cachear resultados de funciones
    
    Args:
        ttl_seconds: Tiempo de vida en segundos (default: 5 minutos)
        
    Usage:
        @cache(ttl_seconds=60)
        def expensive_function(param1, param2):
            # código costoso
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave de caché
            cache_key = f"{func.__module__}.{func.__name__}:{get_cache_key(*args, **kwargs)}"
            
            # Verificar caché
            if cache_key in _cache:
                if cache_key in _cache_expiry:
                    if datetime.now() < _cache_expiry[cache_key]:
                        logger.debug(f"Cache HIT: {func.__name__}")
                        return _cache[cache_key]
                    else:
                        # Expiró
                        logger.debug(f"Cache EXPIRED: {func.__name__}")
                        del _cache[cache_key]
                        del _cache_expiry[cache_key]
            
            # Cache MISS - calcular y cachear
            logger.debug(f"Cache MISS: {func.__name__}")
            result = func(*args, **kwargs)
            
            _cache[cache_key] = result
            _cache_expiry[cache_key] = datetime.now() + timedelta(seconds=ttl_seconds)
            
            return result
        
        # Agregar método para invalidar caché de esta función
        wrapper.invalidate_cache = lambda: invalidate_cache(func.__name__)
        
        return wrapper
    return decorator


def invalidate_cache(pattern: Optional[str] = None):
    """
    Invalida caché
    
    Args:
        pattern: Patrón de claves a invalidar (None = todo)
        
    Usage:
        invalidate_cache()  # Limpia todo
        invalidate_cache("get_hsk")  # Limpia solo funciones con "get_hsk" en el nombre
    """
    if pattern is None:
        count = len(_cache)
        _cache.clear()
        _cache_expiry.clear()
        logger.info(f"Cache invalidado completamente ({count} entradas)")
    else:
        keys_to_delete = [k for k in _cache.keys() if pattern in k]
        for key in keys_to_delete:
            del _cache[key]
            if key in _cache_expiry:
                del _cache_expiry[key]
        logger.info(f"Cache invalidado ({len(keys_to_delete)} entradas con patrón '{pattern}')")


def get_cache_stats() -> dict:
    """
    Obtiene estadísticas del caché
    
    Returns:
        dict: Estadísticas del caché
    """
    now = datetime.now()
    active_entries = sum(
        1 for key in _cache_expiry.keys()
        if _cache_expiry[key] > now
    )
    
    return {
        "total_entries": len(_cache),
        "active_entries": active_entries,
        "expired_entries": len(_cache) - active_entries,
        "memory_usage_kb": sum(len(str(v)) for v in _cache.values()) / 1024
    }


def cleanup_expired_cache():
    """
    Limpia entradas expiradas del caché
    Útil para ejecutar periódicamente
    """
    now = datetime.now()
    expired_keys = [
        key for key, expiry in _cache_expiry.items()
        if expiry <= now
    ]
    
    for key in expired_keys:
        del _cache[key]
        del _cache_expiry[key]
    
    if expired_keys:
        logger.info(f"Limpiadas {len(expired_keys)} entradas expiradas del caché")


# ============================================================================
# IMPLEMENTACIÓN CON REDIS (PRODUCCIÓN)
# ============================================================================

"""
Para usar Redis en producción:

1. Instalar: pip install redis
2. Configurar en config.py:
   REDIS_HOST = "localhost"
   REDIS_PORT = 6379
3. Descomentar el código siguiente

import redis
from app.config import config

try:
    redis_client = redis.Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=0,
        decode_responses=True,
        socket_connect_timeout=5
    )
    # Test de conexión
    redis_client.ping()
    USE_REDIS = True
    logger.info("✅ Conectado a Redis para caché")
except Exception as e:
    USE_REDIS = False
    logger.warning(f"⚠️ Redis no disponible, usando caché en memoria: {e}")


def cache_redis(ttl_seconds: int = 300):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not USE_REDIS:
                # Fallback a caché en memoria
                return cache(ttl_seconds)(func)(*args, **kwargs)
            
            cache_key = f"chiknow:{func.__module__}.{func.__name__}:{get_cache_key(*args, **kwargs)}"
            
            try:
                # Intentar obtener de Redis
                cached = redis_client.get(cache_key)
                if cached:
                    logger.debug(f"Redis HIT: {func.__name__}")
                    return json.loads(cached)
                
                # Cache MISS
                logger.debug(f"Redis MISS: {func.__name__}")
                result = func(*args, **kwargs)
                
                # Guardar en Redis
                redis_client.setex(
                    cache_key,
                    ttl_seconds,
                    json.dumps(result, default=str)
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Error en Redis cache: {e}")
                # Fallback: ejecutar sin caché
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def invalidate_cache_redis(pattern: Optional[str] = None):
    if not USE_REDIS:
        return invalidate_cache(pattern)
    
    try:
        if pattern is None:
            # Eliminar todas las claves de Chiknow
            keys = redis_client.keys("chiknow:*")
            if keys:
                redis_client.delete(*keys)
                logger.info(f"Redis cache invalidado ({len(keys)} claves)")
        else:
            keys = redis_client.keys(f"chiknow:*{pattern}*")
            if keys:
                redis_client.delete(*keys)
                logger.info(f"Redis cache invalidado ({len(keys)} claves con '{pattern}')")
    except Exception as e:
        logger.error(f"Error invalidando Redis cache: {e}")
"""

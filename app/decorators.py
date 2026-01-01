"""
Decoradores para manejo de transacciones y funcionalidades comunes
"""
from functools import wraps
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging
import time
from typing import Callable, Any

logger = logging.getLogger(__name__)


def transactional(func: Callable) -> Callable:
    """
    Decorator para manejar transacciones automáticamente
    
    Hace commit si la función se ejecuta sin errores.
    Hace rollback automático si hay cualquier excepción.
    
    Usage:
        @transactional
        def my_service_function(db: Session, ...):
            # código que modifica la BD
            return result
    
    Args:
        func: Función a decorar (primer parámetro debe ser db: Session)
    
    Returns:
        Callable: Función decorada con manejo de transacciones
    """
    @wraps(func)
    def wrapper(db: Session, *args, **kwargs):
        try:
            # Ejecutar función
            result = func(db, *args, **kwargs)
            
            # Commit si todo OK
            db.commit()
            
            logger.debug(f"Transacción exitosa en {func.__name__}")
            return result
            
        except SQLAlchemyError as e:
            # Rollback en error de BD
            db.rollback()
            logger.error(
                f"Error de BD en {func.__name__}: {e}",
                exc_info=True,
                extra={"function": func.__name__, "error_type": type(e).__name__}
            )
            raise
            
        except Exception as e:
            # Rollback en cualquier otro error
            db.rollback()
            logger.error(
                f"Error en {func.__name__}: {e}",
                exc_info=True,
                extra={"function": func.__name__, "error_type": type(e).__name__}
            )
            raise
    
    return wrapper


def log_execution_time(func: Callable) -> Callable:
    """
    Decorator para medir tiempo de ejecución
    
    Usage:
        @log_execution_time
        def slow_function():
            # código lento
            pass
    
    Args:
        func: Función a decorar
    
    Returns:
        Callable: Función decorada con logging de tiempo
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.time() - start_time
            logger.info(
                f"{func.__name__} ejecutada en {elapsed:.3f}s",
                extra={
                    "function": func.__name__,
                    "execution_time": elapsed,
                    "execution_time_ms": elapsed * 1000
                }
            )
    
    return wrapper


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorator para reintentar operaciones en caso de fallo
    
    Usage:
        @retry_on_failure(max_attempts=3, delay=1.0)
        def unreliable_function():
            # código que puede fallar
            pass
    
    Args:
        max_attempts: Número máximo de intentos
        delay: Delay entre intentos en segundos
    
    Returns:
        Callable: Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Intento {attempt + 1}/{max_attempts} falló en {func.__name__}: {e}",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_attempts": max_attempts
                        }
                    )
                    
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
            
            # Si llegamos aquí, todos los intentos fallaron
            logger.error(
                f"Todos los intentos fallaron en {func.__name__}",
                extra={"function": func.__name__, "max_attempts": max_attempts}
            )
            raise last_exception
        
        return wrapper
    return decorator


def validate_session_active(func: Callable) -> Callable:
    """
    Decorator para validar que una sesión SM2 esté activa
    
    Usage:
        @validate_session_active
        def review_card(db: Session, session_id: int, ...):
            # código que requiere sesión activa
            pass
    
    Args:
        func: Función a decorar
    
    Returns:
        Callable: Función decorada con validación de sesión
    """
    @wraps(func)
    def wrapper(db: Session, session_id: int, *args, **kwargs):
        from . import models
        
        # Verificar que la sesión existe y está activa
        session = db.query(models.SM2Session).filter(
            models.SM2Session.id == session_id
        ).first()
        
        if not session:
            logger.warning(
                f"Sesión {session_id} no encontrada en {func.__name__}",
                extra={"session_id": session_id, "function": func.__name__}
            )
            raise ValueError(f"Sesión {session_id} no encontrada")
        
        if session.fecha_fin is not None:
            logger.warning(
                f"Sesión {session_id} ya finalizada en {func.__name__}",
                extra={"session_id": session_id, "function": func.__name__}
            )
            raise ValueError(f"Sesión {session_id} ya está finalizada")
        
        # Ejecutar función si sesión válida
        return func(db, session_id, *args, **kwargs)
    
    return wrapper


def cached_property(func: Callable) -> property:
    """
    Decorator para propiedades calculadas una sola vez
    
    Similar a @property pero cachea el resultado
    
    Usage:
        class MyClass:
            @cached_property
            def expensive_property(self):
                # cálculo costoso
                return result
    
    Args:
        func: Función a decorar
    
    Returns:
        property: Property con caché
    """
    attr_name = f"_cached_{func.__name__}"
    
    @wraps(func)
    def wrapper(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)
    
    return property(wrapper)


def require_db_connection(func: Callable) -> Callable:
    """
    Decorator para verificar que hay conexión a BD antes de ejecutar
    
    Usage:
        @require_db_connection
        def database_operation(db: Session):
            # operación de BD
            pass
    
    Args:
        func: Función a decorar
    
    Returns:
        Callable: Función decorada con verificación de conexión
    """
    @wraps(func)
    def wrapper(db: Session, *args, **kwargs):
        try:
            # Test de conexión
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            
        except Exception as e:
            logger.error(
                f"Sin conexión a BD en {func.__name__}: {e}",
                extra={"function": func.__name__}
            )
            raise ConnectionError("No hay conexión a la base de datos") from e
        
        return func(db, *args, **kwargs)
    
    return wrapper


# Ejemplo de uso combinado
def safe_transaction(func: Callable) -> Callable:
    """
    Decorator que combina múltiples validaciones
    
    - Verifica conexión a BD
    - Maneja transacciones
    - Mide tiempo de ejecución
    
    Usage:
        @safe_transaction
        def critical_operation(db: Session):
            # operación crítica
            pass
    """
    return log_execution_time(
        require_db_connection(
            transactional(func)
        )
    )

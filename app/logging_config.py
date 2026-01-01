"""
Configuración de logging estructurado para Chiknow
"""
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
import json


class JSONFormatter(logging.Formatter):
    """
    Formateador JSON para logs estructurados
    """
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Agregar exception si existe
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Agregar campos extra personalizados
        extra_fields = [
            "request_id", "user_id", "session_id", "client_ip",
            "method", "path", "status_code", "process_time",
            "tarjeta_id", "hsk_id", "quality", "error_type"
        ]
        
        for field in extra_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """
    Formateador con colores para consola (desarrollo)
    """
    # Códigos de color ANSI
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        # Color según nivel
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Formato: [TIMESTAMP] LEVEL - module.function:line - message
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        formatted = (
            f"{color}[{timestamp}] {record.levelname:8}{reset} - "
            f"{record.module}.{record.funcName}:{record.lineno} - "
            f"{record.getMessage()}"
        )
        
        # Agregar exception si existe
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


def setup_logging(
    log_level: str = "INFO",
    log_file: str = "logs/chiknow.log",
    json_format: bool = False,
    console_colors: bool = True
):
    """
    Configura logging para la aplicación
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Ruta del archivo de log
        json_format: Si usar formato JSON (producción) o texto (desarrollo)
        console_colors: Si usar colores en consola (solo para formato texto)
    
    Returns:
        logging.Logger: Logger raíz configurado
    """
    # Crear directorio de logs si no existe
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Limpiar handlers existentes
    root_logger.handlers.clear()
    
    # ========================================================================
    # HANDLER PARA CONSOLA
    # ========================================================================
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        if console_colors and sys.stdout.isatty():
            console_handler.setFormatter(ColoredFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    '[%(asctime)s] %(levelname)-8s - %(name)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
    
    root_logger.addHandler(console_handler)
    
    # ========================================================================
    # HANDLER PARA ARCHIVO
    # ========================================================================
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        
        # Archivo siempre en formato JSON para parsing
        file_handler.setFormatter(JSONFormatter())
        
        root_logger.addHandler(file_handler)
    except Exception as e:
        root_logger.warning(f"No se pudo crear archivo de log: {e}")
    
    # ========================================================================
    # HANDLER PARA ERRORES (archivo separado)
    # ========================================================================
    try:
        error_file = log_path.parent / f"{log_path.stem}_errors.log"
        error_handler = logging.FileHandler(error_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        
        root_logger.addHandler(error_handler)
    except Exception as e:
        root_logger.warning(f"No se pudo crear archivo de errores: {e}")
    
    # ========================================================================
    # CONFIGURAR LOGGERS ESPECÍFICOS
    # ========================================================================
    
    # SQLAlchemy - solo warnings y errores
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    
    # Uvicorn - solo info
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # FastAPI
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    # Logger de Chiknow
    chiknow_logger = logging.getLogger("chiknow")
    chiknow_logger.setLevel(log_level)
    
    # ========================================================================
    # LOG INICIAL
    # ========================================================================
    root_logger.info("=" * 70)
    root_logger.info("🚀 CHIKNOW - Sistema de Logging Iniciado")
    root_logger.info("=" * 70)
    root_logger.info(f"Log level: {log_level}")
    root_logger.info(f"Formato: {'JSON' if json_format else 'Texto'}")
    root_logger.info(f"Archivo: {log_file}")
    root_logger.info(f"Handlers: {len(root_logger.handlers)}")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger para un módulo específico
    
    Args:
        name: Nombre del módulo
    
    Returns:
        logging.Logger: Logger configurado
        
    Usage:
        logger = get_logger(__name__)
        logger.info("Mensaje")
    """
    return logging.getLogger(name)


# Context manager para logging con contexto extra
class LogContext:
    """
    Context manager para agregar contexto extra a logs
    
    Usage:
        with LogContext(request_id="123", user_id=456):
            logger.info("Este log tendrá request_id y user_id")
    """
    def __init__(self, **kwargs):
        self.context = kwargs
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, *args):
        logging.setLogRecordFactory(self.old_factory)


# Detectar entorno y configurar apropiadamente
def setup_logging_from_env():
    """
    Configura logging según variables de entorno
    
    Variables de entorno soportadas:
    - LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL
    - LOG_FILE: Ruta del archivo de log
    - LOG_FORMAT: json o text
    - ENVIRONMENT: development, production
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE", "logs/chiknow.log")
    log_format = os.getenv("LOG_FORMAT", "text").lower()
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    # En producción, forzar JSON
    json_format = (log_format == "json") or (environment == "production")
    
    # En producción, sin colores
    console_colors = environment == "development"
    
    return setup_logging(
        log_level=log_level,
        log_file=log_file,
        json_format=json_format,
        console_colors=console_colors
    )

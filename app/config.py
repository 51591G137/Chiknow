"""
Gestión de configuración de base de datos
Permite alternar fácilmente entre local y producción
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Config:
    """Configuración de la aplicación"""
    
    # Entorno actual: 'local' o 'produccion'
    DB_ENVIRONMENT = os.getenv("DB_ENVIRONMENT", "local")
    
    # URLs de base de datos - usar DATABASE_URL como variable principal
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    # CORREGIDO: usar data/test.db por defecto
    DATABASE_URL_LOCAL = os.getenv("DATABASE_URL_LOCAL", "sqlite:///./data/test.db")
    DATABASE_URL_PRODUCTION = os.getenv("DATABASE_URL_PRODUCTION", "")
    
    @classmethod
    def get_database_url(cls):
        """Obtiene la URL de base de datos según el entorno"""
        if cls.DB_ENVIRONMENT == "produccion":
            # Prioridad: DATABASE_URL (para Render) -> DATABASE_URL_PRODUCTION
            url = cls.DATABASE_URL or cls.DATABASE_URL_PRODUCTION
            if not url:
                raise ValueError("URL de base de datos de producción no configurada")
        else:
            url = cls.DATABASE_URL_LOCAL
        
        # Fix para Render: postgres:// → postgresql://
        if url and url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        
        return url
    
    @classmethod
    def es_produccion(cls):
        """Verifica si estamos en producción"""
        return cls.DB_ENVIRONMENT == "produccion"
    
    @classmethod
    def es_local(cls):
        """Verifica si estamos en local"""
        return cls.DB_ENVIRONMENT == "local"
    
    @classmethod
    def info(cls):
        """Muestra información de configuración"""
        return {
            "entorno": cls.DB_ENVIRONMENT,
            "url": cls.get_database_url(),
            "es_produccion": cls.es_produccion(),
            "es_local": cls.es_local()
        }

# Instancia global
config = Config()

# Rate limiting
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))

# Redis (opcional)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/chiknow.log")
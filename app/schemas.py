"""
Schemas Pydantic con validación para Chiknow
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


class ReviewRequest(BaseModel):
    """Request para revisar una tarjeta en SM2"""
    tarjeta_id: int = Field(..., gt=0, description="ID de la tarjeta")
    session_id: int = Field(..., gt=0, description="ID de la sesión activa")
    quality: int = Field(..., ge=0, le=2, description="0=Again, 1=Hard, 2=Easy")
    hanzi_fallados: Optional[List[str]] = Field(None, description="Lista de hanzi que fallaron")
    frase_fallada: bool = Field(False, description="Si falló la estructura de la frase")
    respuesta_usuario: Optional[str] = Field(None, max_length=500, description="Respuesta del usuario")
    
    @validator('respuesta_usuario')
    def sanitize_respuesta(cls, v):
        """Sanitiza la respuesta del usuario"""
        if v:
            return v.strip()[:500]
        return v
    
    @validator('hanzi_fallados')
    def validate_hanzi_fallados(cls, v):
        """Valida lista de hanzi fallados"""
        if v:
            # Limitar a 20 hanzi máximo
            return v[:20]
        return v


class NotaRequest(BaseModel):
    """Request para crear/actualizar una nota"""
    nota: str = Field(..., min_length=1, max_length=2000, description="Contenido de la nota")
    
    @validator('nota')
    def sanitize_nota(cls, v):
        """Sanitiza el contenido de la nota"""
        return v.strip()[:2000]


class SearchQuery(BaseModel):
    """Query para búsquedas"""
    query: str = Field(..., min_length=1, max_length=100, description="Término de búsqueda")
    
    @validator('query')
    def sanitize_query(cls, v):
        """Sanitiza y valida el query de búsqueda"""
        # Eliminar caracteres SQL peligrosos
        dangerous = [';', '--', '/*', '*/', 'xp_', 'sp_', 'DROP', 'DELETE', 'INSERT']
        v_lower = v.lower()
        
        for char in dangerous:
            if char.lower() in v_lower:
                raise ValueError(f"Carácter/palabra no permitida: {char}")
        
        return v.strip()[:100]


class HSKWordCreate(BaseModel):
    """Schema para crear una palabra HSK"""
    numero: int = Field(..., gt=0)
    nivel: int = Field(..., ge=1, le=6)
    hanzi: str = Field(..., min_length=1, max_length=50)
    pinyin: str = Field(..., min_length=1, max_length=100)
    espanol: str = Field(..., min_length=1, max_length=500)
    hanzi_alt: Optional[str] = Field(None, max_length=50)
    pinyin_alt: Optional[str] = Field(None, max_length=100)
    categoria: Optional[str] = Field(None, max_length=50)
    ejemplo: Optional[str] = Field(None, max_length=500)
    significado_ejemplo: Optional[str] = Field(None, max_length=500)


class HSKWordResponse(BaseModel):
    """Schema para respuesta de palabra HSK"""
    id: int
    numero: int
    nivel: int
    hanzi: str
    pinyin: str
    espanol: str
    en_diccionario: bool
    hanzi_alt: Optional[str] = None
    pinyin_alt: Optional[str] = None
    categoria: Optional[str] = None
    
    class Config:
        from_attributes = True


class EjemploCreate(BaseModel):
    """Schema para crear un ejemplo"""
    hanzi: str = Field(..., min_length=1, max_length=200)
    pinyin: str = Field(..., min_length=1, max_length=300)
    espanol: str = Field(..., min_length=1, max_length=500)
    nivel: int = Field(1, ge=1, le=6)
    complejidad: int = Field(1, ge=1, le=3)
    hanzi_ids: List[int] = Field(..., min_items=1, max_items=20)
    
    @validator('hanzi_ids')
    def validate_hanzi_ids(cls, v):
        """Valida que todos los IDs sean positivos"""
        if not all(id > 0 for id in v):
            raise ValueError("Todos los IDs deben ser positivos")
        return v


class SM2StatisticsResponse(BaseModel):
    """Schema para estadísticas SM2"""
    total_tarjetas: int
    tarjetas_estudiadas: int
    tarjetas_nuevas: int
    tarjetas_pendientes_hoy: int
    total_revisiones: int


class PaginationParams(BaseModel):
    """Parámetros de paginación"""
    skip: int = Field(0, ge=0, description="Registros a saltar")
    limit: int = Field(100, ge=1, le=500, description="Límite de resultados")
    
    @property
    def offset(self) -> int:
        """Alias para skip"""
        return self.skip


class PaginatedResponse(BaseModel):
    """Respuesta paginada genérica"""
    total: int = Field(..., description="Total de registros")
    skip: int = Field(..., description="Registros saltados")
    limit: int = Field(..., description="Límite aplicado")
    has_more: bool = Field(..., description="Hay más resultados")
    items: List = Field(..., description="Items de esta página")


class HealthCheckResponse(BaseModel):
    """Respuesta del health check"""
    status: str
    timestamp: datetime
    environment: str
    version: str
    database: dict
    cache: Optional[dict] = None
    metrics: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Respuesta de error estándar"""
    error: str = Field(..., description="Tipo de error")
    detail: str = Field(..., description="Detalles del error")
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "detail": "El campo 'quality' debe estar entre 0 y 2",
                "timestamp": "2024-01-01T12:00:00"
            }
        }


class SuccessResponse(BaseModel):
    """Respuesta de éxito estándar"""
    status: str = Field("ok", description="Estado de la operación")
    message: str = Field(..., description="Mensaje descriptivo")
    data: Optional[dict] = Field(None, description="Datos adicionales")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "message": "Palabra agregada exitosamente",
                "data": {"hsk_id": 1, "tarjetas_creadas": 6}
            }
        }

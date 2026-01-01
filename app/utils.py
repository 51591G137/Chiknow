"""
Utilidades comunes para el proyecto Chiknow
"""
from datetime import datetime, timezone
from typing import Optional
import unicodedata


def now_utc() -> datetime:
    """
    Retorna datetime actual en UTC de forma consistente
    
    Returns:
        datetime: Fecha y hora actual en UTC
    """
    return datetime.now(timezone.utc)


def normalize_text(text: str) -> str:
    """
    Normaliza texto removiendo acentos y marcas diacríticas
    
    Args:
        text: Texto a normalizar
        
    Returns:
        str: Texto normalizado sin acentos
        
    Example:
        >>> normalize_text("nǐ hǎo")
        "ni hao"
    """
    if not text:
        return ""
    
    # Descomponer caracteres Unicode
    nfd = unicodedata.normalize('NFD', text)
    
    # Eliminar marcas diacríticas
    return ''.join(
        c for c in nfd 
        if unicodedata.category(c) != 'Mn'
    )


def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    Sanitiza input del usuario
    
    Args:
        text: Texto a sanitizar
        max_length: Longitud máxima permitida
        
    Returns:
        str: Texto sanitizado
    """
    if not text:
        return ""
    
    # Eliminar espacios extra
    text = text.strip()
    
    # Limitar longitud
    text = text[:max_length]
    
    # Eliminar caracteres de control peligrosos
    dangerous_chars = ['\x00', '\r', '\n\n\n']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    return text


def format_interval_display(days: int) -> str:
    """
    Formatea intervalo de días para display
    
    Args:
        days: Número de días
        
    Returns:
        str: Texto formateado (ej: "5d", "2m", "1y")
    """
    if days < 1:
        return "<1d"
    elif days < 30:
        return f"{days}d"
    elif days < 365:
        months = days // 30
        return f"{months}m"
    else:
        years = days // 365
        return f"{years}y"

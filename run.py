#!/usr/bin/env python3
"""
Archivo de inicio para la aplicación Chiknow
Usado para ejecutar localmente y en producción
"""
import uvicorn
import os

if __name__ == "__main__":
    # Obtener puerto de variable de entorno (para Render) o usar 8000 por defecto
    port = int(os.getenv("PORT", 8000))
    
    print(f"🚀 Iniciando Chiknow en puerto {port}...")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("DB_ENVIRONMENT") == "local",  # Recargar solo en local
        log_level="info"
    )
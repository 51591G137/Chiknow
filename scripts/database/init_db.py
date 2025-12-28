#!/usr/bin/env python3
"""
Script para inicializar la base de datos
Se ejecuta automáticamente en Render o manualmente en local
"""
import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.config import config
from app.database import engine

import models

def init_database():
    """Crea todas las tablas si no existen"""
    print("🔧 Inicializando base de datos...")
    
    try:
        # Crear todas las tablas
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas creadas exitosamente")
        
        # Verificar conexión
        with engine.connect() as conn:
            print("✅ Conexión a base de datos exitosa")
        
    except Exception as e:
        print(f"❌ Error al inicializar base de datos: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database()
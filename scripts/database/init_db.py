#!/usr/bin/env python3
"""
Script para inicializar la base de datos
Se ejecuta automáticamente en Render o manualmente en local
"""
import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import Base, engine, init_db

def main():
    """Función principal para inicializar la base de datos"""
    print("🔧 Inicializando base de datos...")
    
    try:
        # Importar todos los modelos para que SQLAlchemy los reconozca
        from app import models
        
        # Crear todas las tablas
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas creadas exitosamente")
        
        # Verificar conexión
        with engine.connect() as conn:
            print("✅ Conexión a base de datos exitosa")
            
        # Contar tablas creadas
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tablas = inspector.get_table_names()
        print(f"📊 Tablas creadas: {len(tablas)}")
        for tabla in tablas:
            print(f"  - {tabla}")
            
    except Exception as e:
        print(f"❌ Error al inicializar base de datos: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Prueba de importaciones
"""
import sys
import os

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Probando importaciones...")

try:
    from app import models
    print("✅ models importado")
    
    from app import repository
    print("✅ repository importado")
    
    from app import service
    print("✅ service importado")
    
    from app import database
    print("✅ database importado")
    
    from app import config
    print("✅ config importado")
    
    from app import main
    print("✅ main importado")
    
    print("\n🎉 ¡Todas las importaciones funcionan!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
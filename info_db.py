#!/usr/bin/env python3
"""
Muestra información sobre la base de datos actual
Uso: python scripts/info_bd.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from database import engine
from sqlalchemy import text

def mostrar_info():
    """Muestra información de la BD actual"""
    info = config.info()
    
    print("\n" + "="*70)
    print("📊 INFORMACIÓN DE BASE DE DATOS")
    print("="*70)
    
    print(f"\n🔧 Entorno: {info['entorno'].upper()}")
    
    if info['es_produccion']:
        print("   ⚠️  ESTÁS CONECTADO A PRODUCCIÓN")
        print("   Los cambios afectarán a usuarios reales")
    else:
        print("   ✅ Estás conectado a base de datos local")
        print("   Puedes experimentar libremente")
    
    # Ocultar credenciales en URL
    url_display = info['url']
    if '@' in url_display:
        # postgresql://user:password@host/db → postgresql://***@host/db
        parts = url_display.split('@')
        protocol_user = parts[0].split('//')[0] + '//***'
        url_display = protocol_user + '@' + parts[1]
    
    print(f"\n🔗 URL: {url_display}")
    
    # Intentar conectar y obtener estadísticas
    try:
        with engine.connect() as conn:
            # Contar registros
            result_hsk = conn.execute(text("SELECT COUNT(*) FROM hsk")).scalar()
            result_dict = conn.execute(text("SELECT COUNT(*) FROM diccionario")).scalar()
            result_tarjetas = conn.execute(text("SELECT COUNT(*) FROM tarjetas")).scalar()
            result_ejemplos = conn.execute(text("SELECT COUNT(*) FROM ejemplos")).scalar()
            
            print("\n📈 Estadísticas:")
            print(f"   Palabras HSK:       {result_hsk}")
            print(f"   En diccionario:     {result_dict}")
            print(f"   Tarjetas:           {result_tarjetas}")
            print(f"   Ejemplos:           {result_ejemplos}")
        
        print("\n✅ Conexión exitosa")
        
    except Exception as e:
        print(f"\n❌ Error de conexión: {e}")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    mostrar_info()
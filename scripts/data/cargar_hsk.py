"""
Script para cargar o actualizar datos de HSK desde hsk.csv

Este script:
1. Lee el archivo hsk.csv
2. Para cada fila, verifica si el ID ya existe en la BD
3. Si existe, actualiza los datos (UPSERT)
4. Si no existe, crea un nuevo registro

Uso desde CUALQUIER directorio:
    python scripts/data/cargar_hsk.py
    python cargar_hsk.py  (si estás en scripts/data/)
    cd /cualquier/ruta && python /ruta/a/chiknow/scripts/data/cargar_hsk.py

NOTA: El script detecta automáticamente las rutas correctas
"""

import sys
import os
import pandas as pd
from sqlalchemy.orm import Session
import unicodedata
import re

# ============================================================================
# CONFIGURACIÓN DE RUTAS ABSOLUTAS
# ============================================================================

# Obtener directorio del script actual
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Calcular directorio raíz del proyecto (2 niveles arriba: scripts/data/ -> scripts/ -> raíz/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

# Añadir raíz del proyecto al path de Python
sys.path.insert(0, PROJECT_ROOT)

# Cambiar directorio de trabajo al proyecto raíz
os.chdir(PROJECT_ROOT)

print(f"📁 Directorio del script: {SCRIPT_DIR}")
print(f"📁 Directorio raíz del proyecto: {PROJECT_ROOT}")
print(f"📁 Directorio de trabajo actual: {os.getcwd()}")

# ============================================================================
# IMPORTACIONES (ahora funcionarán desde cualquier ubicación)
# ============================================================================

from app.database import SessionLocal, engine, Base
import app.models as models

# ============================================================================
# FUNCIONES
# ============================================================================

def normalizar_nombre_columna(nombre):
    """
    Normaliza nombres de columnas para hacerlos comparables
    Elimina TODOS los acentos y marcas diacríticas, convierte a minúsculas
    """
    nombre_nfd = unicodedata.normalize('NFD', nombre)
    nombre_ascii = ''.join(
        c for c in nombre_nfd 
        if unicodedata.category(c) != 'Mn'
    )
    nombre_limpio = nombre_ascii.lower().strip()
    nombre_comparable = re.sub(r'[_\s]+', '', nombre_limpio)
    return nombre_comparable

def mapear_columnas(columnas_csv):
    """
    Crea un mapeo entre nombres de columnas del CSV y nombres estándar
    """
    variaciones = {
        'nivel': 'nivel',
        'level': 'nivel',
        'hanzi': 'hanzi',
        'hanzi': 'hanzi',
        'caracteres': 'hanzi',
        'pinyin': 'pinyin',
        'pinyin': 'pinyin',
        'romanizacion': 'pinyin',
        'español': 'espanol',
        'espanol': 'espanol',
        'spanish': 'espanol',
        'traduccion': 'espanol',
        'hanzialt': 'hanzi_alt',
        'hanzi_alt': 'hanzi_alt',
        'hanzialternativo': 'hanzi_alt',
        'pinyinalt': 'pinyin_alt',
        'pinyin_alt': 'pinyin_alt',
        'pinyinalternativo': 'pinyin_alt',
        'categoria': 'categoria',
        'categoria': 'categoria',
        'category': 'categoria',
        'tipo': 'categoria',
        'ejemplo': 'ejemplo',
        'example': 'ejemplo',
        'sample': 'ejemplo',
        'significadoejemplo': 'significado_ejemplo',
        'significado_ejemplo': 'significado_ejemplo',
        'significado ejemplo': 'significado_ejemplo',
        'examplemeaning': 'significado_ejemplo',
    }
    
    mapeo = {}
    mapeo_debug = {}
    
    for col_csv in columnas_csv:
        col_normalizada = normalizar_nombre_columna(col_csv)
        mapeo_debug[col_csv] = col_normalizada
        
        if col_normalizada in variaciones:
            nombre_estandar = variaciones[col_normalizada]
            mapeo[nombre_estandar] = col_csv
    
    print(f"\n🔍 Debug - Columnas normalizadas:")
    for original, normalizada in mapeo_debug.items():
        encontrada = "✅" if normalizada in variaciones else "❌"
        print(f"   {encontrada} '{original}' → '{normalizada}'")
    
    return mapeo

def cargar_hsk_desde_csv(csv_path: str = None):
    """
    Carga o actualiza datos de HSK desde CSV
    
    Args:
        csv_path: Ruta al archivo CSV (si None, usa ruta por defecto)
    """
    # Si no se proporciona ruta, usar ruta por defecto
    if csv_path is None:
        csv_path = os.path.join(PROJECT_ROOT, "data", "hsk.csv")
    
    # Verificar que el archivo existe
    if not os.path.exists(csv_path):
        print(f"❌ Error: No se encontró el archivo {csv_path}")
        return False
    
    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)
    
    # Leer CSV
    print(f"\n📖 Leyendo {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {csv_path}")
        return False
    except Exception as e:
        print(f"❌ Error al leer CSV: {e}")
        return False
    
    print(f"✅ Leídas {len(df)} filas del CSV")
    
    # Crear mapeo de columnas
    print(f"\n🔍 Analizando columnas del CSV...")
    print(f"Columnas encontradas: {list(df.columns)}")
    
    mapeo = mapear_columnas(df.columns)
    
    print(f"\n📋 Mapeo de columnas exitoso:")
    for estandar, csv_col in mapeo.items():
        print(f"   {estandar:20} ← '{csv_col}'")
    
    # Validar columnas requeridas
    columnas_requeridas = ['nivel', 'hanzi', 'pinyin', 'espanol']
    columnas_faltantes = [col for col in columnas_requeridas if col not in mapeo]
    
    if columnas_faltantes:
        print(f"\n❌ Error: No se pudieron mapear las columnas requeridas: {columnas_faltantes}")
        print(f"\nColumnas disponibles en el mapeo: {list(mapeo.keys())}")
        return False
    
    print(f"\n✅ Todas las columnas requeridas están presentes\n")
    
    db = SessionLocal()
    
    try:
        registros_nuevos = 0
        registros_actualizados = 0
        
        for idx, row in df.iterrows():
            # Generar ID basado en el índice
            hsk_id = idx + 1
            
            # Buscar si existe el registro
            existing = db.query(models.HSK).filter(models.HSK.id == hsk_id).first()
            
            # Preparar datos
            datos = {
                'id': hsk_id,
                'numero': hsk_id,
            }
            
            # Añadir campos requeridos
            for campo_estandar in ['nivel', 'hanzi', 'pinyin', 'espanol']:
                col_csv = mapeo[campo_estandar]
                valor = row[col_csv]
                
                if campo_estandar == 'nivel':
                    datos[campo_estandar] = int(valor) if pd.notna(valor) else 1
                else:
                    datos[campo_estandar] = str(valor).strip() if pd.notna(valor) else ''
            
            # Añadir campos opcionales
            for campo_opcional in ['hanzi_alt', 'pinyin_alt', 'categoria', 'ejemplo', 'significado_ejemplo']:
                if campo_opcional in mapeo:
                    col_csv = mapeo[campo_opcional]
                    valor = row[col_csv]
                    datos[campo_opcional] = str(valor).strip() if pd.notna(valor) else None
            
            if existing:
                # ACTUALIZAR
                for key, value in datos.items():
                    if key != 'id':
                        setattr(existing, key, value)
                registros_actualizados += 1
                
                if (registros_actualizados % 100 == 0):
                    print(f"   Actualizados: {registros_actualizados}")
            else:
                # CREAR
                nuevo_registro = models.HSK(**datos)
                db.add(nuevo_registro)
                registros_nuevos += 1
                
                if (registros_nuevos % 100 == 0):
                    print(f"   Nuevos: {registros_nuevos}")
        
        # Commit final
        db.commit()
        
        print("\n" + "="*50)
        print("✅ IMPORTACIÓN COMPLETADA")
        print(f"📊 Registros nuevos: {registros_nuevos}")
        print(f"🔄 Registros actualizados: {registros_actualizados}")
        print(f"📈 Total en BD: {db.query(models.HSK).count()}")
        print("="*50)
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error durante la importación: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def main():
    """Función principal"""
    print("\n" + "="*50)
    print("🚀 CARGADOR DE DATOS HSK")
    print("="*50 + "\n")
    
    # Buscar el archivo en múltiples ubicaciones
    posibles_rutas = [
        os.path.join(PROJECT_ROOT, "data", "hsk.csv"),
        os.path.join(PROJECT_ROOT, "datos", "hsk.csv"),
        "hsk.csv",
        "datos.csv"
    ]
    
    csv_path = None
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            csv_path = ruta
            break
    
    if csv_path is None:
        print("❌ No se encontró hsk.csv en ninguna ubicación esperada")
        print("Ubicaciones buscadas:")
        for ruta in posibles_rutas:
            print(f"  - {os.path.abspath(ruta)}")
        return False
    
    print(f"✅ Archivo encontrado: {csv_path}\n")
    return cargar_hsk_desde_csv(csv_path)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
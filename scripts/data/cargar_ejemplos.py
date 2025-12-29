"""
Script para cargar o actualizar ejemplos desde ejemplos.csv

Este script:
1. Lee el archivo ejemplos.csv
2. Para cada fila, verifica si el ID ya existe en la BD
3. Si existe, actualiza los datos (UPSERT)
4. Si no existe, crea un nuevo registro
5. Gestiona las relaciones con los hanzi componentes

Estructura esperada del CSV:
- ID (opcional, se generará si no existe)
- Hanzi: frase completa en caracteres chinos
- Pinyin: romanización completa
- Español: traducción al español
- Nivel: nivel HSK (1-6)
- Complejidad: 1=simple, 2=medio, 3=complejo
- Hanzi_IDs: IDs de los hanzi que componen la frase, separados por comas (ej: "1,2,3")
"""

import sys
import os
import pandas as pd
from sqlalchemy.orm import Session
import unicodedata
import re

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal, engine, Base
from app import models

def normalizar_nombre_columna(nombre):
    """
    Normaliza nombres de columnas para hacerlos comparables
    Elimina TODOS los acentos y marcas diacríticas, convierte a minúsculas
    """
    # Normalizar a NFD (descomponer caracteres con acentos)
    nombre_nfd = unicodedata.normalize('NFD', nombre)
    
    # Filtrar solo caracteres ASCII (elimina todos los acentos y marcas)
    nombre_ascii = ''.join(
        c for c in nombre_nfd 
        if unicodedata.category(c) != 'Mn'  # Mn = Nonspacing_Mark (acentos, tildes, etc.)
    )
    
    # Convertir a minúsculas y eliminar espacios extra
    nombre_limpio = nombre_ascii.lower().strip()
    
    # Eliminar guiones bajos y espacios para comparación
    nombre_comparable = re.sub(r'[_\s]+', '', nombre_limpio)
    
    return nombre_comparable

def mapear_columnas(columnas_csv):
    """
    Crea un mapeo entre nombres de columnas del CSV y nombres estándar
    
    Args:
        columnas_csv: Lista de nombres de columnas del CSV
    
    Returns:
        dict: Mapeo de nombre_estandar -> nombre_en_csv
    """
    # Definir variaciones posibles para cada columna
    variaciones = {
        'id': 'id',
        
        'hanzi': 'hanzi',
        'frase': 'hanzi',
        'caracteres': 'hanzi',
        
        'pinyin': 'pinyin',
        'romanizacion': 'pinyin',
        
        'español': 'espanol',
        'espanol': 'espanol',
        'spanish': 'espanol',
        'traduccion': 'espanol',
        
        'nivel': 'nivel',
        'level': 'nivel',
        'hsk': 'nivel',
        
        'complejidad': 'complejidad',
        'complexity': 'complejidad',
        'dificultad': 'complejidad',
        
        'hanziids': 'hanzi_ids',
        'hanzi_ids': 'hanzi_ids',
        'hanzis': 'hanzi_ids',
        'ids': 'hanzi_ids',
        'componentes': 'hanzi_ids',
    }
    
    mapeo = {}
    mapeo_debug = {}
    
    # Para cada columna del CSV
    for col_csv in columnas_csv:
        col_normalizada = normalizar_nombre_columna(col_csv)
        mapeo_debug[col_csv] = col_normalizada
        
        # Buscar en las variaciones
        if col_normalizada in variaciones:
            nombre_estandar = variaciones[col_normalizada]
            mapeo[nombre_estandar] = col_csv
    
    # Debug
    print(f"\n🔍 Debug - Columnas normalizadas:")
    for original, normalizada in mapeo_debug.items():
        encontrada = "✅" if normalizada in variaciones else "❌"
        print(f"   {encontrada} '{original}' → '{normalizada}'")
    
    return mapeo

def cargar_ejemplos_desde_csv(csv_path: str = "data/ejemplos.csv"):
    """
    Carga o actualiza ejemplos desde CSV
    
    Args:
        csv_path: Ruta al archivo CSV
    """
    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)
    
    # Leer CSV
    print(f"📖 Leyendo {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {csv_path}")
        return
    
    print(f"✅ Leídas {len(df)} filas del CSV")
    
    # Crear mapeo de columnas
    print(f"\n🔍 Analizando columnas del CSV...")
    print(f"Columnas encontradas: {list(df.columns)}")
    
    mapeo = mapear_columnas(df.columns)
    
    print(f"\n📋 Mapeo de columnas exitoso:")
    for estandar, csv_col in mapeo.items():
        print(f"   {estandar:20} ← '{csv_col}'")
    
    # Validar columnas requeridas
    columnas_requeridas = ['hanzi', 'pinyin', 'espanol']
    columnas_faltantes = [col for col in columnas_requeridas if col not in mapeo]
    
    if columnas_faltantes:
        print(f"\n❌ Error: No se pudieron mapear las columnas requeridas: {columnas_faltantes}")
        print(f"\nColumnas disponibles en el mapeo: {list(mapeo.keys())}")
        print(f"\nPor favor verifica que el CSV contenga columnas equivalentes a:")
        print(f"   - Hanzi (o Hànzì, frase, caracteres)")
        print(f"   - Pinyin (o Pīnyīn, romanizacion)")
        print(f"   - Español (o espanol, spanish, traduccion)")
        return
    
    print(f"\n✅ Todas las columnas requeridas están presentes\n")
    
    db = SessionLocal()
    
    try:
        registros_nuevos = 0
        registros_actualizados = 0
        relaciones_creadas = 0
        
        for idx, row in df.iterrows():
            # Determinar ID
            if 'id' in mapeo and pd.notna(row[mapeo['id']]):
                ejemplo_id = int(row[mapeo['id']])
            else:
                ejemplo_id = idx + 1
            
            # Buscar si existe
            existing = db.query(models.Ejemplo).filter(models.Ejemplo.id == ejemplo_id).first()
            
            # Preparar datos básicos usando mapeo
            datos = {
                'id': ejemplo_id,
                'hanzi': str(row[mapeo['hanzi']]).strip() if pd.notna(row[mapeo['hanzi']]) else '',
                'pinyin': str(row[mapeo['pinyin']]).strip() if pd.notna(row[mapeo['pinyin']]) else '',
                'espanol': str(row[mapeo['espanol']]).strip() if pd.notna(row[mapeo['espanol']]) else '',
            }
            
            # Añadir campos opcionales
            if 'nivel' in mapeo:
                datos['nivel'] = int(row[mapeo['nivel']]) if pd.notna(row[mapeo['nivel']]) else 1
            else:
                datos['nivel'] = 1
            
            if 'complejidad' in mapeo:
                datos['complejidad'] = int(row[mapeo['complejidad']]) if pd.notna(row[mapeo['complejidad']]) else 1
            else:
                datos['complejidad'] = 1
            
            # Mantener estado de activación si ya existe
            if existing:
                datos['activado'] = existing.activado
                datos['en_diccionario'] = existing.en_diccionario
            else:
                datos['activado'] = False
                datos['en_diccionario'] = False
            
            if existing:
                # ACTUALIZAR
                for key, value in datos.items():
                    if key != 'id':
                        setattr(existing, key, value)
                ejemplo_obj = existing
                registros_actualizados += 1
            else:
                # CREAR
                ejemplo_obj = models.Ejemplo(**datos)
                db.add(ejemplo_obj)
                db.flush()  # Para obtener el ID
                registros_nuevos += 1
            
            # GESTIONAR RELACIONES CON HANZI
            if 'hanzi_ids' in mapeo and pd.notna(row[mapeo['hanzi_ids']]):
                # Eliminar relaciones existentes
                db.query(models.HSKEjemplo).filter(
                    models.HSKEjemplo.ejemplo_id == ejemplo_obj.id
                ).delete()
                
                # Crear nuevas relaciones
                hanzi_ids_str = str(row[mapeo['hanzi_ids']]).strip()
                if hanzi_ids_str:
                    hanzi_ids = [int(x.strip()) for x in hanzi_ids_str.split(',') if x.strip()]
                    
                    for posicion, hsk_id in enumerate(hanzi_ids, start=1):
                        # Verificar que el hanzi existe
                        hanzi_existe = db.query(models.HSK).filter(models.HSK.id == hsk_id).first()
                        if hanzi_existe:
                            relacion = models.HSKEjemplo(
                                hsk_id=hsk_id,
                                ejemplo_id=ejemplo_obj.id,
                                posicion=posicion
                            )
                            db.add(relacion)
                            relaciones_creadas += 1
                        else:
                            print(f"⚠️  Advertencia: HSK ID {hsk_id} no existe (ejemplo {ejemplo_obj.id})")
            
            # Commit periódico
            if (idx + 1) % 50 == 0:
                db.commit()
                print(f"   Procesados: {idx + 1}/{len(df)}")
        
        # Commit final
        db.commit()
        
        print("\n" + "="*50)
        print("✅ IMPORTACIÓN DE EJEMPLOS COMPLETADA")
        print(f"📊 Ejemplos nuevos: {registros_nuevos}")
        print(f"🔄 Ejemplos actualizados: {registros_actualizados}")
        print(f"🔗 Relaciones HSK-Ejemplo creadas: {relaciones_creadas}")
        print(f"📈 Total ejemplos en BD: {db.query(models.Ejemplo).count()}")
        print("="*50)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error durante la importación: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

def main():
    """Función principal"""
    print("\n" + "="*50)
    print("🚀 CARGADOR DE EJEMPLOS")
    print("="*50 + "\n")
    
    # Buscar el archivo en múltiples ubicaciones
    posibles_rutas = [
        "data/ejemplos.csv",
        "../data/ejemplos.csv",
        "ejemplos.csv"
    ]
    
    csv_path = None
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            csv_path = ruta
            break
    
    if csv_path is None:
        print("❌ No se encontró ejemplos.csv en ninguna ubicación esperada")
        print("Ubicaciones buscadas:")
        for ruta in posibles_rutas:
            print(f"  - {os.path.abspath(ruta)}")
        return
    
    cargar_ejemplos_desde_csv(csv_path)

if __name__ == "__main__":
    main()
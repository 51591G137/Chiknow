#!/usr/bin/env python3
"""
Script para cargar datos HSK desde CSV SIN CABECERA
Uso: python3 cargar_hsk_sin_cabecera.py
"""

import csv
from database import SessionLocal, engine
import models

# Crear todas las tablas
models.Base.metadata.create_all(bind=engine)

def cargar_hsk_desde_csv(archivo_csv='datos.csv'):
    """Carga datos HSK desde un archivo CSV sin cabecera"""
    db = SessionLocal()
    
    try:
        # Verificar si ya hay datos
        count = db.query(models.HSK).count()
        if count > 0:
            print(f"⚠️  Ya hay {count} palabras en la base de datos.")
            respuesta = input("¿Quieres eliminarlas y recargar? (s/n): ")
            if respuesta.lower() != 's':
                print("❌ Cancelado")
                return
            
            # Eliminar datos existentes
            db.query(models.HSK).delete()
            db.commit()
            print("✅ Datos antiguos eliminados")
        
        # Leer CSV SIN CABECERA
        palabras = []
        with open(archivo_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 5:  # Asegurar que tiene todas las columnas
                    palabras.append(row)
        
        print(f"📖 Leyendo {len(palabras)} palabras desde {archivo_csv}...")
        
        # Insertar palabras
        errores = 0
        for i, row in enumerate(palabras, 1):
            try:
                palabra = models.HSK(
                    numero=int(row[0]),      # Primera columna: numero
                    nivel=int(row[1]),       # Segunda columna: nivel
                    hanzi=row[2],            # Tercera columna: hanzi
                    pinyin=row[3],           # Cuarta columna: pinyin
                    espanol=row[4]           # Quinta columna: espanol
                )
                db.add(palabra)
                
                if i % 100 == 0:
                    print(f"  Procesadas {i}/{len(palabras)}...")
                    
            except (ValueError, IndexError) as e:
                errores += 1
                print(f"  ⚠️  Error en línea {i}: {e}")
                if errores > 10:
                    print(f"  ❌ Demasiados errores, abortando...")
                    raise
        
        db.commit()
        
        # Verificar
        total = db.query(models.HSK).count()
        print(f"\n✅ ¡Éxito! Se cargaron {total} palabras HSK")
        if errores > 0:
            print(f"⚠️  Hubo {errores} errores al procesar algunas líneas")
        
        # Mostrar algunas palabras de ejemplo
        print("\n📝 Primeras 10 palabras cargadas:")
        ejemplos = db.query(models.HSK).order_by(models.HSK.numero).limit(10).all()
        for palabra in ejemplos:
            print(f"  {palabra.numero}. {palabra.hanzi} ({palabra.pinyin}) - {palabra.espanol} [HSK{palabra.nivel}]")
        
        print("\n📝 Últimas 5 palabras cargadas:")
        ultimas = db.query(models.HSK).order_by(models.HSK.numero.desc()).limit(5).all()
        for palabra in reversed(ultimas):
            print(f"  {palabra.numero}. {palabra.hanzi} ({palabra.pinyin}) - {palabra.espanol} [HSK{palabra.nivel}]")
        
    except FileNotFoundError:
        print(f"❌ ERROR: No se encontró el archivo '{archivo_csv}'")
        print("\nAsegúrate de que el archivo existe en el directorio actual")
        print("Formato esperado (SIN cabecera):")
        print("1,1,爱,ài,amar")
        print("2,1,八,bā,ocho")
        print("...")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

if __name__ == "__main__":
    print("="*60)
    print("CARGADOR DE DATOS HSK (CSV SIN CABECERA)")
    print("="*60)
    print("\nFormato esperado del CSV:")
    print("  numero,nivel,hanzi,pinyin,espanol")
    print("  1,1,爱,ài,amar")
    print("  2,1,八,bā,ocho")
    print()
    cargar_hsk_desde_csv()
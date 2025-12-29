#!/usr/bin/env python3
"""
Script de limpieza CORREGIDO para campo nivel
==============================================
Convierte bytes de enteros a int usando struct.unpack

Uso:
    python limpiar_nivel_correcto.py
"""
import sys
import os
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app import models

def bytes_to_int(bytes_value):
    """Convierte bytes a entero (little-endian, 64 bits)"""
    if not bytes_value:
        return 0
    
    # Si son 8 bytes (64 bits)
    if len(bytes_value) == 8:
        # Formato: 'q' = long long signed (8 bytes, little-endian)
        return struct.unpack('<q', bytes_value)[0]
    
    # Si son 4 bytes (32 bits)
    elif len(bytes_value) == 4:
        # Formato: 'i' = int signed (4 bytes, little-endian)
        return struct.unpack('<i', bytes_value)[0]
    
    # Fallback: interpretar primer byte
    else:
        return bytes_value[0] if bytes_value else 0

def limpiar_nivel():
    """Limpia el campo nivel convirtiendo bytes a int"""
    print("\n" + "="*70)
    print("  🔧 LIMPIANDO CAMPO 'nivel'")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        total = db.query(models.HSK).count()
        print(f"\n📊 Total registros: {total}")
        
        # Contar cuántos tienen bytes
        registros_con_bytes = 0
        for registro in db.query(models.HSK).all():
            if isinstance(registro.nivel, bytes):
                registros_con_bytes += 1
        
        print(f"⚠️  Registros con bytes en 'nivel': {registros_con_bytes}")
        
        if registros_con_bytes == 0:
            print("\n✅ No hay registros que limpiar")
            return True
        
        respuesta = input(f"\n¿Convertir {registros_con_bytes} registros? (s/n): ")
        if respuesta.lower() != 's':
            print("❌ Operación cancelada")
            return False
        
        print("\n🔄 Convirtiendo bytes a enteros...")
        
        limpiados = 0
        errores = 0
        
        for registro in db.query(models.HSK).all():
            if isinstance(registro.nivel, bytes):
                try:
                    # Convertir bytes a int
                    valor_int = bytes_to_int(registro.nivel)
                    
                    # Verificar que sea un valor razonable (HSK va de 1 a 6)
                    if valor_int < 1 or valor_int > 6:
                        print(f"   ⚠️  ID {registro.id}: valor fuera de rango ({valor_int}), usando 1")
                        valor_int = 1
                    
                    # Asignar el valor convertido
                    registro.nivel = valor_int
                    limpiados += 1
                    
                    # Commit periódico
                    if limpiados % 100 == 0:
                        db.commit()
                        print(f"   Limpiados: {limpiados}/{registros_con_bytes}")
                
                except Exception as e:
                    errores += 1
                    print(f"   ❌ Error en ID {registro.id}: {e}")
                    # Asignar valor por defecto
                    registro.nivel = 1
        
        # Commit final
        db.commit()
        
        print("\n" + "="*70)
        print("📊 RESULTADOS")
        print("="*70)
        print(f"✅ Limpiados exitosamente: {limpiados}")
        print(f"❌ Errores: {errores}")
        print(f"📈 Total procesados: {limpiados + errores}")
        
        # Verificar resultado
        print("\n🔍 Verificando resultado...")
        registros_con_bytes_final = 0
        for registro in db.query(models.HSK).all():
            if isinstance(registro.nivel, bytes):
                registros_con_bytes_final += 1
        
        if registros_con_bytes_final == 0:
            print("✅ Todos los registros fueron limpiados correctamente")
        else:
            print(f"⚠️  Aún quedan {registros_con_bytes_final} registros con bytes")
        
        # Mostrar ejemplos
        print("\n📝 Ejemplos de registros limpiados:")
        for registro in db.query(models.HSK).limit(5).all():
            print(f"   ID {registro.id}: nivel={registro.nivel} ({type(registro.nivel).__name__})")
        
        return registros_con_bytes_final == 0
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error durante la limpieza: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def verificar_api():
    """Verifica que la API pueda serializar los datos"""
    print("\n" + "="*70)
    print("  🧪 VERIFICANDO API")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        import json
        
        print("\n🔄 Intentando serializar todos los registros...")
        
        palabras = db.query(models.HSK).all()
        errores = 0
        
        for palabra in palabras:
            try:
                datos = {
                    "id": palabra.id,
                    "numero": palabra.numero,
                    "nivel": palabra.nivel,
                    "hanzi": palabra.hanzi,
                    "pinyin": palabra.pinyin,
                    "espanol": palabra.espanol
                }
                json.dumps(datos)
            except Exception as e:
                print(f"   ❌ Error en ID {palabra.id}: {e}")
                errores += 1
        
        if errores == 0:
            print(f"✅ Todos los {len(palabras)} registros se pueden serializar correctamente")
            return True
        else:
            print(f"❌ {errores} registros con errores de serialización")
            return False
        
    finally:
        db.close()

def main():
    """Función principal"""
    print("\n" + "="*70)
    print("  🚀 LIMPIEZA CORREGIDA DE CAMPO 'nivel'")
    print("="*70)
    print("\n💡 Este script convierte bytes de enteros (little-endian) a int")
    print()
    
    # Paso 1: Limpiar
    exito = limpiar_nivel()
    
    if exito:
        # Paso 2: Verificar API
        api_ok = verificar_api()
        
        if api_ok:
            print("\n" + "="*70)
            print("  ✅ LIMPIEZA COMPLETADA EXITOSAMENTE")
            print("="*70)
            print("\n🎯 Próximo paso:")
            print("   Inicia el servidor y prueba la aplicación:")
            print("   uvicorn app.main:app --reload")
            print()
        else:
            print("\n⚠️  La limpieza se completó pero aún hay problemas de serialización")
    else:
        print("\n❌ La limpieza no se completó correctamente")

if __name__ == "__main__":
    main()
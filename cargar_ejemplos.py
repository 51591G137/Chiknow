#!/usr/bin/env python3
"""
Script para cargar ejemplos/frases desde CSV
Uso: python3 cargar_ejemplos.py

Formato esperado del CSV (sin cabecera):
id,hanzi,pinyin,espanol

Ejemplo:
1,我喝茶,wǒ hē chá,Yo bebo té
2,你好,nǐ hǎo,Hola
3,我爱你,wǒ ài nǐ,Te amo

El script analiza automáticamente cada hanzi de la frase y busca su ID en la tabla HSK
"""

import csv
from database import SessionLocal, engine
import models
import service

# Crear todas las tablas
models.Base.metadata.create_all(bind=engine)

def analizar_hanzi_en_frase(db, frase):
    """
    Analiza una frase y devuelve los IDs HSK de cada hanzi encontrado
    
    Args:
        db: Sesión de base de datos
        frase: String con hanzi (ej: "我喝茶")
    
    Returns:
        tuple: (hanzi_ids, hanzi_no_encontrados)
    """
    hanzi_ids = []
    hanzi_no_encontrados = []
    
    for posicion, caracter in enumerate(frase, start=1):
        # Ignorar espacios, puntuación y caracteres ASCII
        if caracter.isspace() or not '\u4e00' <= caracter <= '\u9fff':
            continue
        
        # Buscar el hanzi en la tabla HSK
        hsk = db.query(models.HSK).filter(models.HSK.hanzi == caracter).first()
        
        if hsk:
            hanzi_ids.append(hsk.id)
        else:
            hanzi_no_encontrados.append(caracter)
    
    return hanzi_ids, hanzi_no_encontrados

def calcular_complejidad(num_hanzi):
    """Calcula complejidad basada en número de hanzi"""
    if num_hanzi <= 2:
        return 1  # Simple
    elif num_hanzi <= 4:
        return 2  # Medio
    else:
        return 3  # Complejo

def cargar_ejemplos_desde_csv(archivo_csv='ejemplos.csv'):
    """Carga ejemplos desde un archivo CSV sin cabecera"""
    db = SessionLocal()
    
    try:
        # Verificar si ya hay datos
        count = db.query(models.Ejemplo).count()
        if count > 0:
            print(f"⚠️  Ya hay {count} ejemplos en la base de datos.")
            respuesta = input("¿Quieres eliminarlos y recargar? (s/n): ")
            if respuesta.lower() != 's':
                print("❌ Cancelado")
                return
            
            # Eliminar datos existentes (y sus relaciones)
            print("  Eliminando tarjetas de ejemplos...")
            db.query(models.Tarjeta).filter(models.Tarjeta.ejemplo_id != None).delete()
            print("  Eliminando relaciones HSK-Ejemplo...")
            db.query(models.HSKEjemplo).delete()
            print("  Eliminando jerarquías de ejemplos...")
            db.query(models.EjemploJerarquia).delete()
            print("  Eliminando activaciones...")
            db.query(models.EjemploActivacion).delete()
            print("  Eliminando ejemplos...")
            db.query(models.Ejemplo).delete()
            db.commit()
            print("✅ Datos antiguos eliminados")
        
        # Verificar que existan palabras HSK
        hsk_count = db.query(models.HSK).count()
        if hsk_count == 0:
            print("❌ ERROR: No hay palabras HSK en la base de datos")
            print("   Ejecuta primero: python3 cargar_hsk_sin_cabecera.py")
            return
        
        print(f"ℹ️  Base de datos tiene {hsk_count} palabras HSK\n")
        
        # Leer CSV SIN CABECERA
        ejemplos_data = []
        with open(archivo_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:  # id, hanzi, pinyin, espanol
                    ejemplos_data.append(row)
        
        print(f"📖 Leyendo {len(ejemplos_data)} ejemplos desde {archivo_csv}...")
        print("🔍 Analizando hanzi de cada frase...\n")
        
        # Insertar ejemplos
        errores = 0
        ejemplos_creados = 0
        hanzi_total_no_encontrados = set()
        
        for i, row in enumerate(ejemplos_data, 1):
            try:
                ejemplo_id = int(row[0])
                hanzi = row[1].strip()
                pinyin = row[2].strip()
                espanol = row[3].strip()
                
                # Analizar hanzi en la frase
                hanzi_ids, hanzi_no_encontrados = analizar_hanzi_en_frase(db, hanzi)
                
                if hanzi_no_encontrados:
                    print(f"  ⚠️  Línea {i} ({hanzi}): Hanzi no encontrados en HSK: {', '.join(hanzi_no_encontrados)}")
                    hanzi_total_no_encontrados.update(hanzi_no_encontrados)
                
                if not hanzi_ids:
                    print(f"  ❌ Línea {i} ({hanzi}): No se encontró ningún hanzi válido, saltando...")
                    errores += 1
                    continue
                
                # Calcular complejidad y nivel
                complejidad = calcular_complejidad(len(hanzi_ids))
                nivel = 1  # Por defecto HSK1, podrías calcularlo según los niveles de los hanzi
                
                # Crear ejemplo usando el servicio
                ejemplo = service.crear_ejemplo_completo(
                    db, hanzi, pinyin, espanol, hanzi_ids, nivel, complejidad
                )
                
                ejemplos_creados += 1
                
                # Mostrar progreso cada 10
                if i % 10 == 0:
                    print(f"  ✓ Procesados {i}/{len(ejemplos_data)}... ({ejemplos_creados} creados)")
                    
            except (ValueError, IndexError) as e:
                errores += 1
                print(f"  ⚠️  Error en línea {i}: {e}")
                if errores > 20:
                    print(f"  ❌ Demasiados errores, abortando...")
                    raise
            except Exception as e:
                errores += 1
                print(f"  ⚠️  Error inesperado en línea {i}: {e}")
                import traceback
                traceback.print_exc()
        
        db.commit()
        
        # Verificar
        total = db.query(models.Ejemplo).count()
        print(f"\n{'='*60}")
        print(f"✅ ¡Éxito! Se cargaron {total} ejemplos")
        if errores > 0:
            print(f"⚠️  Hubo {errores} errores al procesar algunas líneas")
        
        if hanzi_total_no_encontrados:
            print(f"\n⚠️  Hanzi no encontrados en la tabla HSK:")
            print(f"   {', '.join(sorted(hanzi_total_no_encontrados))}")
            print(f"   Estos hanzi fueron ignorados en los ejemplos")
        
        # Mostrar estadísticas
        activados = db.query(models.Ejemplo).filter(models.Ejemplo.activado == True).count()
        en_diccionario = db.query(models.Ejemplo).filter(models.Ejemplo.en_diccionario == True).count()
        
        print(f"\n📊 Estadísticas:")
        print(f"  Total ejemplos cargados: {total}")
        print(f"  Activados (todos hanzi dominados): {activados}")
        print(f"  En diccionario del usuario: {en_diccionario}")
        print(f"  Por activar (requieren estudio): {total - activados}")
        
        # Distribución por complejidad
        simple = db.query(models.Ejemplo).filter(models.Ejemplo.complejidad == 1).count()
        medio = db.query(models.Ejemplo).filter(models.Ejemplo.complejidad == 2).count()
        complejo = db.query(models.Ejemplo).filter(models.Ejemplo.complejidad == 3).count()
        
        print(f"\n📈 Distribución por complejidad:")
        print(f"  Simple (1-2 hanzi):   {simple}")
        print(f"  Medio (3-4 hanzi):    {medio}")
        print(f"  Complejo (5+ hanzi):  {complejo}")
        
        # Mostrar algunos ejemplos
        print(f"\n📝 Primeros 10 ejemplos cargados:")
        ejemplos = db.query(models.Ejemplo).limit(10).all()
        for ejemplo in ejemplos:
            estado = "✓ Activado" if ejemplo.activado else "○ No activado"
            complejidad_str = ["Simple", "Medio", "Complejo"][ejemplo.complejidad - 1]
            
            print(f"\n  {ejemplo.id}. {ejemplo.hanzi} ({ejemplo.pinyin})")
            print(f"      {ejemplo.espanol}")
            print(f"      {estado} | HSK{ejemplo.nivel} | {complejidad_str}")
            
            # Mostrar hanzi componentes
            relaciones = db.query(models.HSKEjemplo, models.HSK).join(
                models.HSK, models.HSKEjemplo.hsk_id == models.HSK.id
            ).filter(
                models.HSKEjemplo.ejemplo_id == ejemplo.id
            ).order_by(models.HSKEjemplo.posicion).all()
            
            hanzi_componentes = [f"{hsk.hanzi}({hsk.pinyin})" for rel, hsk in relaciones]
            print(f"      Componentes: {' + '.join(hanzi_componentes)}")
        
        print(f"\n{'='*60}")
        print("\n💡 Próximos pasos:")
        print("  1. Añade palabras HSK a tu diccionario desde http://localhost:8000")
        print("  2. Estudia las palabras en /sm2 hasta dominarlas")
        print("  3. Los ejemplos se activarán automáticamente cuando domines todos sus hanzi")
        print("  4. Ve a /ejemplos para ver ejemplos disponibles")
        print("  5. Añade ejemplos activados a tu estudio")
        print("  6. Estudia los ejemplos en /sm2")
        
    except FileNotFoundError:
        print(f"❌ ERROR: No se encontró el archivo '{archivo_csv}'")
        print("\nAsegúrate de que el archivo existe en el directorio actual")
        print("\nFormato esperado (SIN cabecera):")
        print("  id,hanzi,pinyin,espanol")
        print("\nEjemplo:")
        print("  1,我喝茶,wǒ hē chá,Yo bebo té")
        print("  2,你好,nǐ hǎo,Hola")
        print("  3,我爱你,wǒ ài nǐ,Te amo")
        print("\nEl script analiza automáticamente cada hanzi y busca su ID en HSK")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

def mostrar_ayuda():
    """Muestra ayuda sobre el script"""
    print("\n" + "="*60)
    print("AYUDA: Cómo usar cargar_ejemplos.py")
    print("="*60)
    print("\nFormato del CSV (sin cabecera):")
    print("  id,hanzi,pinyin,espanol")
    print("\nColumnas:")
    print("  1. id      : Número de ejemplo")
    print("  2. hanzi   : Frase en caracteres chinos")
    print("  3. pinyin  : Pronunciación con tonos")
    print("  4. espanol : Traducción al español")
    print("\nEjemplo de archivo ejemplos.csv:")
    print("  1,我喝茶,wǒ hē chá,Yo bebo té")
    print("  2,你好,nǐ hǎo,Hola")
    print("  3,我爱你,wǒ ài nǐ,Te amo")
    print("  4,这是什么,zhè shì shénme,¿Qué es esto?")
    print("\nCómo funciona:")
    print("  1. El script lee cada frase del CSV")
    print("  2. Analiza cada hanzi de la frase")
    print("  3. Busca cada hanzi en la tabla HSK")
    print("  4. Crea las relaciones automáticamente")
    print("  5. Calcula la complejidad según el número de hanzi")
    print("\nComplejidad automática:")
    print("  - Simple:   1-2 hanzi")
    print("  - Medio:    3-4 hanzi")
    print("  - Complejo: 5+ hanzi")
    print("\nActivación automática:")
    print("  - Los ejemplos se activan cuando dominas TODOS sus hanzi")
    print("  - Dominar = haber estudiado la palabra y tener buen progreso")
    print("  - Puedes ver ejemplos disponibles en /ejemplos")
    print("\nRequisitos:")
    print("  - Debes haber cargado primero las palabras HSK")
    print("  - Ejecuta: python3 cargar_hsk_sin_cabecera.py")
    print("\nUso:")
    print("  python3 cargar_ejemplos.py           # Cargar ejemplos")
    print("  python3 cargar_ejemplos.py --ayuda   # Mostrar esta ayuda")

if __name__ == "__main__":
    print("="*60)
    print("CARGADOR DE EJEMPLOS/FRASES")
    print("="*60)
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in ['--ayuda', '-h', '--help']:
        mostrar_ayuda()
    else:
        cargar_ejemplos_desde_csv()
"""
Script para cargar ejemplos iniciales en la base de datos
Incluye frases simples, medias y complejas con jerarquías
"""

from main import SessionLocal
import service
import repository

def cargar_ejemplos_iniciales():
    db = SessionLocal()
    
    print("=" * 60)
    print("CARGANDO EJEMPLOS INICIALES")
    print("=" * 60)
    
    try:
        # ====================================================================
        # EJEMPLOS SIMPLES (Complejidad 1)
        # ====================================================================
        print("\n📝 Creando ejemplos simples...")
        
        # Ejemplo 1: 我喝茶 (Yo bebo té)
        # IDs de HSK: 我(380), 喝(144), 茶(36)
        ej1 = service.crear_ejemplo_completo(
            db,
            hanzi="我喝茶",
            pinyin="wǒ hē chá",
            espanol="Yo bebo té",
            hanzi_ids=[380, 144, 36],
            nivel=1,
            complejidad=1
        )
        print(f"✓ Creado: {ej1.hanzi} - {ej1.espanol}")
        
        # Ejemplo 2: 我吃饭 (Yo como)
        # IDs: 我(380), 吃(46), 饭(99)
        ej2 = service.crear_ejemplo_completo(
            db,
            hanzi="我吃饭",
            pinyin="wǒ chī fàn",
            espanol="Yo como",
            hanzi_ids=[380, 46, 99],
            nivel=1,
            complejidad=1
        )
        print(f"✓ Creado: {ej2.hanzi} - {ej2.espanol}")
        
        # Ejemplo 3: 我爱你 (Te amo)
        # IDs: 我(380), 爱(1), 你(271)
        ej3 = service.crear_ejemplo_completo(
            db,
            hanzi="我爱你",
            pinyin="wǒ ài nǐ",
            espanol="Te amo",
            hanzi_ids=[380, 1, 271],
            nivel=1,
            complejidad=1
        )
        print(f"✓ Creado: {ej3.hanzi} - {ej3.espanol}")
        
        # Ejemplo 4: 你好吗 (¿Cómo estás?)
        # IDs: 你(271), 好(138), 吗(227)
        ej4 = service.crear_ejemplo_completo(
            db,
            hanzi="你好吗",
            pinyin="nǐ hǎo ma",
            espanol="¿Cómo estás?",
            hanzi_ids=[271, 138, 227],
            nivel=1,
            complejidad=1
        )
        print(f"✓ Creado: {ej4.hanzi} - {ej4.espanol}")
        
        # ====================================================================
        # EJEMPLOS MEDIOS (Complejidad 2)
        # ====================================================================
        print("\n📝 Creando ejemplos medios...")
        
        # Ejemplo 5: 我喝茶在家 (Yo bebo té en casa)
        # IDs: 我(380), 喝(144), 茶(36), 在(455), 家(169)
        ej5 = service.crear_ejemplo_completo(
            db,
            hanzi="我喝茶在家",
            pinyin="wǒ hē chá zài jiā",
            espanol="Yo bebo té en casa",
            hanzi_ids=[380, 144, 36, 455, 169],
            nivel=1,
            complejidad=2
        )
        print(f"✓ Creado: {ej5.hanzi} - {ej5.espanol}")
        
        # Crear jerarquía: ej5 contiene ej1
        repository.create_jerarquia_ejemplo(db, ej5.id, ej1.id)
        print(f"  └─ Jerarquía: '{ej5.espanol}' contiene '{ej1.espanol}'")
        
        # Ejemplo 6: 我吃饭在家 (Yo como en casa)
        # IDs: 我(380), 吃(46), 饭(99), 在(455), 家(169)
        ej6 = service.crear_ejemplo_completo(
            db,
            hanzi="我吃饭在家",
            pinyin="wǒ chī fàn zài jiā",
            espanol="Yo como en casa",
            hanzi_ids=[380, 46, 99, 455, 169],
            nivel=1,
            complejidad=2
        )
        print(f"✓ Creado: {ej6.hanzi} - {ej6.espanol}")
        
        # Crear jerarquía: ej6 contiene ej2
        repository.create_jerarquia_ejemplo(db, ej6.id, ej2.id)
        print(f"  └─ Jerarquía: '{ej6.espanol}' contiene '{ej2.espanol}'")
        
        # ====================================================================
        # EJEMPLOS COMPLEJOS (Complejidad 3)
        # ====================================================================
        print("\n📝 Creando ejemplos complejos...")
        
        # Ejemplo 7: 我喝茶在家和你 (Yo bebo té en casa contigo)
        # IDs: 我(380), 喝(144), 茶(36), 在(455), 家(169), 和(145), 你(271)
        ej7 = service.crear_ejemplo_completo(
            db,
            hanzi="我喝茶在家和你",
            pinyin="wǒ hē chá zài jiā hé nǐ",
            espanol="Yo bebo té en casa contigo",
            hanzi_ids=[380, 144, 36, 455, 169, 145, 271],
            nivel=1,
            complejidad=3
        )
        print(f"✓ Creado: {ej7.hanzi} - {ej7.espanol}")
        
        # Crear jerarquías: ej7 contiene ej5 y ej1
        repository.create_jerarquia_ejemplo(db, ej7.id, ej5.id)
        repository.create_jerarquia_ejemplo(db, ej7.id, ej1.id)
        print(f"  └─ Jerarquía: '{ej7.espanol}' contiene '{ej5.espanol}' y '{ej1.espanol}'")
        
        print("\n" + "=" * 60)
        print("✅ EJEMPLOS CARGADOS EXITOSAMENTE")
        print("=" * 60)
        print(f"\nTotal de ejemplos creados: 7")
        print(f"  - Simples (complejidad 1): 4")
        print(f"  - Medios (complejidad 2): 2")
        print(f"  - Complejos (complejidad 3): 1")
        print(f"\nJerarquías creadas: 4")
        
        print("\n📋 PRÓXIMOS PASOS:")
        print("1. Añade las palabras individuales al diccionario")
        print("2. Estudia las palabras hasta dominarlas")
        print("3. Los ejemplos se activarán automáticamente")
        print("4. Añade los ejemplos a tu estudio")
        print("5. ¡Disfruta aprendiendo frases en contexto!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cargar_ejemplos_iniciales()
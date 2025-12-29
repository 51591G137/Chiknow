#!/usr/bin/env python3
"""
⚠️  SCRIPT PELIGROSO ⚠️
Sube base de datos local a Render (PRODUCCIÓN)
SOBRESCRIBE todos los datos de usuarios reales

Uso: python scripts/database/bd_local_a_render.py

SOLO usar cuando:
- Necesitas restaurar producción desde backup
- Vas a migrar datos iniciales por primera vez
- Estás 100% seguro de lo que haces
"""
import sys
import os

# Añadir el directorio raíz al path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root_dir)

from datetime import datetime
from dotenv import load_dotenv
import shutil

load_dotenv()

def verificar_prerequisitos():
    """Verifica que todo esté listo"""
    test_db_path = os.path.join(root_dir, "data", "test.db")
    
    if not os.path.exists(test_db_path):
        print(f"❌ No existe {test_db_path}")
        print("   No hay datos locales para subir")
        return False
    
    render_url = os.getenv("DATABASE_URL_PRODUCTION")
    if not render_url:
        print("❌ DATABASE_URL_PRODUCTION no configurada en .env")
        return False
    
    print("✅ Prerequisitos verificados")
    return True

def bd_local_a_render():
    """Sube base de datos local a producción en Render"""
    
    print("\n" + "="*70)
    print("⚠️  ⚠️  ⚠️  ADVERTENCIA CRÍTICA ⚠️  ⚠️  ⚠️")
    print("="*70)
    print("\n📤 SINCRONIZACIÓN: LOCAL → RENDER (PRODUCCIÓN)")
    print("\nEsta operación:")
    print("  ❌ BORRARÁ todos los datos actuales en producción")
    print("  ❌ Los usuarios PERDERÁN su progreso")
    print("  ❌ Es IRREVERSIBLE sin backup")
    print("\n" + "="*70)
    
    if not verificar_prerequisitos():
        return False
    
    render_url = os.getenv("DATABASE_URL_PRODUCTION")
    if render_url.startswith("postgres://"):
        render_url = render_url.replace("postgres://", "postgresql://", 1)
    
    # Triple confirmación
    print("\n🔴 CONFIRMACIÓN 1/3:")
    print("¿Entiendes que esto BORRARÁ todos los datos de producción?")
    conf1 = input("Escribe 'SI' para continuar: ")
    if conf1 != "SI":
        print("\n✅ Operación cancelada (buena decisión)")
        return False
    
    print("\n🔴 CONFIRMACIÓN 2/3:")
    print("¿Has verificado que data/test.db contiene los datos correctos?")
    conf2 = input("Escribe 'VERIFICADO' para continuar: ")
    if conf2 != "VERIFICADO":
        print("\n✅ Operación cancelada")
        return False
    
    print("\n🔴 CONFIRMACIÓN FINAL 3/3:")
    print("Esta es tu ÚLTIMA oportunidad para cancelar.")
    conf3 = input("Escribe 'EJECUTAR AHORA' para continuar: ")
    if conf3 != "EJECUTAR AHORA":
        print("\n✅ Operación cancelada")
        return False
    
    try:
        backups_dir = os.path.join(root_dir, "backups")
        os.makedirs(backups_dir, exist_ok=True)
        
        # Paso 1: BACKUP de local
        print("\n💾 Paso 1: Backup de base de datos local...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_local = os.path.join(backups_dir, f"local_pre_upload_{timestamp}.db")
        test_db_path = os.path.join(root_dir, "data", "test.db")
        
        shutil.copy2(test_db_path, backup_local)
        size_mb = os.path.getsize(backup_local) / 1024 / 1024
        print(f"✅ Backup local guardado: {backup_local} ({size_mb:.2f} MB)")
        
        # Paso 2: Conectar a bases de datos
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        from app import models
        
        print("\n🔌 Paso 2: Conectando a bases de datos...")
        
        # Conectar a local
        engine_local = create_engine(
            f"sqlite:///{test_db_path}",
            connect_args={"check_same_thread": False}
        )
        Session_local = sessionmaker(bind=engine_local)
        db_local = Session_local()
        print("   ✅ Conectado a BD local")
        
        # Conectar a producción
        engine_prod = create_engine(
            render_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True
        )
        Session_prod = sessionmaker(bind=engine_prod)
        db_prod = Session_prod()
        print("   ✅ Conectado a Render")
        
        # Paso 3: Limpiar producción
        print("\n🗑️  Paso 3: Limpiando base de datos de producción...")
        print("   (Eliminando en orden para respetar foreign keys)")
        
        with engine_prod.connect() as conn:
            # Borrar en el orden correcto (inverso a las dependencias)
            tables_to_clear = [
                "sm2_reviews",           # Depende de tarjetas y sesiones
                "sm2_progress",          # Depende de tarjetas
                "sm2_sessions",          # Independiente
                "ejemplo_activacion",    # Depende de ejemplos
                "ejemplo_jerarquia",     # Depende de ejemplos
                "hsk_ejemplo",           # Depende de HSK y ejemplos
                "tarjetas",              # Depende de diccionario, HSK y ejemplos
                "ejemplos",              # Independiente
                "notas",                 # Depende de HSK
                "diccionario",           # Depende de HSK
                "hsk"                    # Base, se borra al final
            ]
            
            for table in tables_to_clear:
                try:
                    result = conn.execute(text(f"DELETE FROM {table}"))
                    conn.commit()
                    print(f"   ✅ {table}: {result.rowcount} registros eliminados")
                except Exception as e:
                    error_msg = str(e)[:80]
                    print(f"   ⚠️  {table}: {error_msg}")
        
        print("✅ Base de datos de producción limpiada")
        
        # Paso 4: Copiar datos de local a producción
        print("\n📥 Paso 4: Subiendo datos locales a producción...")
        
        try:
            # Copiar HSK
            print("   Subiendo HSK...")
            hsk_items = db_local.query(models.HSK).all()
            
            for idx, item in enumerate(hsk_items):
                new_item = models.HSK(
                    id=item.id,
                    numero=item.numero,
                    nivel=item.nivel,
                    hanzi=item.hanzi,
                    pinyin=item.pinyin,
                    espanol=item.espanol,
                    hanzi_alt=item.hanzi_alt,
                    pinyin_alt=item.pinyin_alt,
                    categoria=item.categoria,
                    ejemplo=item.ejemplo,
                    significado_ejemplo=item.significado_ejemplo
                )
                db_prod.add(new_item)
                
                if (idx + 1) % 100 == 0:
                    db_prod.commit()
                    print(f"      Subidos: {idx + 1}/{len(hsk_items)}")
            
            db_prod.commit()
            print(f"   ✅ HSK: {len(hsk_items)} palabras")
            
            # Copiar Diccionario
            print("   Subiendo Diccionario...")
            dict_items = db_local.query(models.Diccionario).all()
            for item in dict_items:
                new_item = models.Diccionario(
                    id=item.id,
                    hsk_id=item.hsk_id,
                    activo=item.activo
                )
                db_prod.add(new_item)
            db_prod.commit()
            print(f"   ✅ Diccionario: {len(dict_items)} entradas")
            
            # Copiar Notas
            print("   Subiendo Notas...")
            notas = db_local.query(models.Notas).all()
            for item in notas:
                new_item = models.Notas(
                    id=item.id,
                    hsk_id=item.hsk_id,
                    nota=item.nota,
                    created_at=item.created_at,
                    updated_at=item.updated_at
                )
                db_prod.add(new_item)
            db_prod.commit()
            print(f"   ✅ Notas: {len(notas)} notas")
            
            # Copiar Ejemplos
            print("   Subiendo Ejemplos...")
            ejemplos = db_local.query(models.Ejemplo).all()
            for item in ejemplos:
                new_item = models.Ejemplo(
                    id=item.id,
                    hanzi=item.hanzi,
                    pinyin=item.pinyin,
                    espanol=item.espanol,
                    nivel=item.nivel,
                    complejidad=item.complejidad,
                    activado=item.activado,
                    en_diccionario=item.en_diccionario,
                    created_at=item.created_at
                )
                db_prod.add(new_item)
            db_prod.commit()
            print(f"   ✅ Ejemplos: {len(ejemplos)} frases")
            
            # Copiar Relaciones HSK-Ejemplo
            print("   Subiendo Relaciones HSK-Ejemplo...")
            relaciones = db_local.query(models.HSKEjemplo).all()
            for item in relaciones:
                new_item = models.HSKEjemplo(
                    id=item.id,
                    hsk_id=item.hsk_id,
                    ejemplo_id=item.ejemplo_id,
                    posicion=item.posicion
                )
                db_prod.add(new_item)
            db_prod.commit()
            print(f"   ✅ Relaciones: {len(relaciones)} enlaces")
            
            # Copiar Tarjetas
            print("   Subiendo Tarjetas...")
            tarjetas = db_local.query(models.Tarjeta).all()
            for item in tarjetas:
                new_item = models.Tarjeta(
                    id=item.id,
                    hsk_id=item.hsk_id,
                    diccionario_id=item.diccionario_id,
                    ejemplo_id=item.ejemplo_id,
                    mostrado1=item.mostrado1,
                    mostrado2=item.mostrado2,
                    audio=item.audio,
                    requerido=item.requerido,
                    activa=item.activa
                )
                db_prod.add(new_item)
            db_prod.commit()
            print(f"   ✅ Tarjetas: {len(tarjetas)} tarjetas")
            
            # Copiar Progreso SM2
            print("   Subiendo Progreso SM2...")
            progress = db_local.query(models.SM2Progress).all()
            for item in progress:
                new_item = models.SM2Progress(
                    id=item.id,
                    tarjeta_id=item.tarjeta_id,
                    easiness_factor=item.easiness_factor,
                    repetitions=item.repetitions,
                    interval=item.interval,
                    next_review=item.next_review,
                    estado=item.estado,
                    total_reviews=item.total_reviews,
                    correct_reviews=item.correct_reviews,
                    last_review=item.last_review,
                    created_at=item.created_at
                )
                db_prod.add(new_item)
            db_prod.commit()
            print(f"   ✅ Progreso SM2: {len(progress)} registros")
            
            # Copiar Sesiones SM2
            print("   Subiendo Sesiones SM2...")
            sessions = db_local.query(models.SM2Session).all()
            for item in sessions:
                new_item = models.SM2Session(
                    id=item.id,
                    fecha_inicio=item.fecha_inicio,
                    fecha_fin=item.fecha_fin,
                    tarjetas_estudiadas=item.tarjetas_estudiadas,
                    tarjetas_correctas=item.tarjetas_correctas,
                    tarjetas_incorrectas=item.tarjetas_incorrectas
                )
                db_prod.add(new_item)
            db_prod.commit()
            print(f"   ✅ Sesiones: {len(sessions)} sesiones")
            
            # Copiar Reviews SM2
            print("   Subiendo Reviews SM2...")
            reviews = db_local.query(models.SM2Review).all()
            for item in reviews:
                new_item = models.SM2Review(
                    id=item.id,
                    tarjeta_id=item.tarjeta_id,
                    session_id=item.session_id,
                    quality=item.quality,
                    respuesta_usuario=item.respuesta_usuario,
                    previous_easiness=item.previous_easiness,
                    new_easiness=item.new_easiness,
                    previous_interval=item.previous_interval,
                    new_interval=item.new_interval,
                    previous_estado=item.previous_estado,
                    new_estado=item.new_estado,
                    hanzi_fallados=item.hanzi_fallados,
                    frase_fallada=item.frase_fallada,
                    fecha=item.fecha
                )
                db_prod.add(new_item)
            db_prod.commit()
            print(f"   ✅ Reviews: {len(reviews)} revisiones")
            
            print("\n" + "="*70)
            print("✅ SINCRONIZACIÓN COMPLETADA EXITOSAMENTE")
            print("="*70)
            print(f"\n📁 Backup guardado en:")
            print(f"   {backup_local}")
            print("\n🌐 Los usuarios ahora verán estos datos en:")
            print(f"   https://chiknow.onrender.com")
            
        except Exception as e:
            print(f"\n❌ ERROR durante la copia: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db_local.close()
            db_prod.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n⚠️  ⚠️  ⚠️  SCRIPT PELIGROSO ⚠️  ⚠️  ⚠️")
    print("\nEste script SOBRESCRIBE la base de datos de producción.")
    print("\n¿Estás seguro de que quieres continuar?")
    
    inicial = input("\nEscribe 'CONTINUAR' para proceder o Enter para cancelar: ")
    if inicial != "CONTINUAR":
        print("\n✅ Operación cancelada. Buena decisión.")
        sys.exit(0)
    
    exito = bd_local_a_render()
    
    if exito:
        print("\n🎉 ¡Sincronización exitosa!")
    else:
        print("\n❌ La sincronización falló")
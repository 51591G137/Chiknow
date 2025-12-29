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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import subprocess
from datetime import datetime
from dotenv import load_dotenv
import shutil

load_dotenv()

def verificar_prerequisitos():
    """Verifica que todo esté listo"""
    # CORREGIDO: usar data/test.db
    if not os.path.exists("data/test.db"):
        print("❌ No existe data/test.db")
        print("   No hay datos locales para subir")
        return False
    
    # Verificar que existe DATABASE_URL_PRODUCTION
    render_url = os.getenv("DATABASE_URL_PRODUCTION")
    if not render_url:
        print("❌ DATABASE_URL_PRODUCTION no configurada en .env")
        return False
    
    # Verificar que pg_dump está instalado
    try:
        subprocess.run(["pg_dump", "--version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ pg_dump no está instalado")
        print("\n💡 Instalar PostgreSQL client:")
        print("   Mac: brew install postgresql")
        print("   Ubuntu: sudo apt install postgresql-client")
        print("   Windows: Descargar desde postgresql.org")
        return False
    
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
    
    # Verificar prerequisitos
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
    print("Los datos de producción se BORRARÁN en 5 segundos.")
    conf3 = input("Escribe 'EJECUTAR AHORA' para continuar: ")
    if conf3 != "EJECUTAR AHORA":
        print("\n✅ Operación cancelada")
        return False
    
    try:
        os.makedirs("backups", exist_ok=True)
        
        # Paso 1: BACKUP de producción (MUY IMPORTANTE)
        print("\n💾 Paso 1: BACKUP de producción (por seguridad)...")
        backup_file = f"backups/render_backup_pre_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        
        print("   Conectando a Render...")
        try:
            result = subprocess.run(
                ["pg_dump", render_url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                print(f"⚠️  Error en pg_dump: {result.stderr}")
                print("\n❓ ¿Continuar sin backup de producción? (MUY PELIGROSO)")
                continuar = input("Escribe 'SI SIN BACKUP' para continuar: ")
                if continuar != "SI SIN BACKUP":
                    print("\n✅ Operación cancelada")
                    return False
                print("\n⚠️  Continuando SIN backup de producción...")
            else:
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                
                backup_size = os.path.getsize(backup_file) / 1024 / 1024  # MB
                print(f"✅ Backup guardado: {backup_file} ({backup_size:.2f} MB)")
                print("   ⚠️  GUARDA ESTE ARCHIVO. Es tu única forma de recuperar datos.")
        except Exception as e:
            print(f"⚠️  No se pudo hacer backup: {e}")
            print("\n❓ ¿Continuar sin backup? (MUY PELIGROSO)")
            continuar = input("Escribe 'SI SIN BACKUP' para continuar: ")
            if continuar != "SI SIN BACKUP":
                print("\n✅ Operación cancelada")
                return False
        
        # Paso 2: Copiar test.db como backup
        print("\n💾 Paso 2: Backup de data/test.db local...")
        backup_local = f"backups/local_pre_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2("data/test.db", backup_local)
        print(f"✅ Backup local guardado: {backup_local}")
        
        # Paso 3: Conectar a producción y LIMPIAR
        print("\n🗑️  Paso 3: Limpiando base de datos de producción...")
        print("   ⚠️  Borrando todos los datos...")
        
        from sqlalchemy import create_engine, text
        engine_prod = create_engine(render_url)
        
        with engine_prod.connect() as conn:
            # NO necesitamos desactivar foreign keys si borramos en el orden correcto
            # Orden inverso a las dependencias (de hijos a padres)
            
            tables_to_clear = [
                # 1. Primero las tablas que dependen de otras
                ("sm2_reviews", "SM2 Reviews"),
                ("sm2_progress", "SM2 Progress"),
                ("sm2_sessions", "SM2 Sessions"),
                ("ejemplo_activacion", "Activación de Ejemplos"),
                ("ejemplo_jerarquia", "Jerarquía de Ejemplos"),
                ("hsk_ejemplo", "Relaciones HSK-Ejemplo"),
                ("tarjetas", "Tarjetas"),
                ("notas", "Notas"),
                # 2. Luego las tablas base
                ("ejemplos", "Ejemplos"),
                ("diccionario", "Diccionario"),
                ("hsk", "HSK")
            ]
            
            total_deleted = 0
            for table, nombre in tables_to_clear:
                try:
                    result = conn.execute(text(f"DELETE FROM {table}"))
                    count = result.rowcount
                    total_deleted += count
                    if count > 0:
                        print(f"   ✅ {nombre}: {count} registros eliminados")
                    else:
                        print(f"   ℹ️  {nombre}: vacía")
                    conn.commit()
                except Exception as e:
                    print(f"   ⚠️  {nombre}: {str(e)[:100]}")
                    conn.rollback()
                    # Continuar con la siguiente tabla
            
            print(f"\n   📊 Total eliminados: {total_deleted} registros")
        
        print("✅ Base de datos de producción limpiada")
        
        # Paso 4: Copiar datos de local a producción
        print("\n📥 Paso 4: Subiendo datos locales a producción...")
        
        # IMPORTANTE: Configurar entorno antes de importar
        os.environ["DB_ENVIRONMENT"] = "local"
        os.environ["DATABASE_URL_LOCAL"] = "sqlite:///./data/test.db"
        
        # Conectar a local
        from sqlalchemy import create_engine as create_eng
        from sqlalchemy.orm import sessionmaker
        from app import models
        
        engine_local = create_eng("sqlite:///./data/test.db", connect_args={"check_same_thread": False})
        Session_local = sessionmaker(bind=engine_local)
        db_local = Session_local()
        
        # Conectar a producción
        Session_prod = sessionmaker(bind=engine_prod)
        db_prod = Session_prod()
        
        try:
            # Copiar HSK
            print("   Subiendo HSK...")
            hsk_items = db_local.query(models.HSK).all()
            for item in hsk_items:
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
            db_prod.commit()
            print(f"   ✅ HSK: {len(hsk_items)} palabras subidas")
            
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
            print(f"   ✅ Progreso: {len(progress)} registros")
            
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
            
            print("\n" + "="*70)
            print("✅ SINCRONIZACIÓN COMPLETADA EXITOSAMENTE")
            print("="*70)
            print(f"\n📁 Backups guardados en: backups/")
            print(f"   - Producción (antes): {backup_file}")
            print(f"   - Local (antes): {backup_local}")
            print("\n💡 Los usuarios ahora verán estos datos en:")
            print(f"   {os.getenv('RENDER_APP_URL', 'tu-app.onrender.com')}")
            
        except Exception as e:
            print(f"\n❌ ERROR durante la copia: {e}")
            print("\n⚠️  La base de datos de producción puede estar en estado inconsistente")
            print(f"   Restaurar desde backup: {backup_file}")
            print("\n📖 Para restaurar:")
            print(f"   psql '{render_url}' < {backup_file}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db_local.close()
            db_prod.close()
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error en pg_dump: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n⚠️  ⚠️  ⚠️  SCRIPT PELIGROSO ⚠️  ⚠️  ⚠️")
    print("\nEste script SOBRESCRIBE la base de datos de producción.")
    print("Los usuarios PERDERÁN todos sus datos.")
    print("\n¿Estás seguro de que quieres continuar?")
    
    inicial = input("\nEscribe 'CONTINUAR' para proceder o Enter para cancelar: ")
    if inicial != "CONTINUAR":
        print("\n✅ Operación cancelada. Buena decisión.")
        sys.exit(0)
    
    bd_local_a_render()
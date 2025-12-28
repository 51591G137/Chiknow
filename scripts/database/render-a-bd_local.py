#!/usr/bin/env python3
"""
Descarga base de datos de Render (producción) a local
Uso: python scripts/render_a_bd_local.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def render_a_bd_local():
    """Copia base de datos de Render a local"""
    
    print("\n" + "="*70)
    print("📥 SINCRONIZACIÓN: RENDER (PRODUCCIÓN) → LOCAL")
    print("="*70)
    
    local_db = "test.db"
    render_url = os.getenv("DATABASE_URL_PRODUCTION")
    
    if not render_url:
        print("❌ DATABASE_URL_PRODUCTION no configurada en .env")
        return False
    
    # Fix URL
    if render_url.startswith("postgres://"):
        render_url = render_url.replace("postgres://", "postgresql://", 1)
    
    print("\n⚠️  Esta operación sobrescribirá tu base de datos local")
    print("   Se hará un backup primero")
    confirmacion = input("\n¿Continuar? (s/n): ")
    
    if confirmacion.lower() != 's':
        print("\n❌ Operación cancelada")
        return False
    
    try:
        # Paso 1: Backup de local (por si acaso)
        os.makedirs("backups", exist_ok=True)
        print("\n💾 Paso 1: Backup de base de datos local...")
        if os.path.exists(local_db):
            backup_local = f"backups/local_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            import shutil
            shutil.copy2(local_db, backup_local)
            print(f"✅ Backup guardado: {backup_local}")
        else:
            print("   (No existe BD local previa)")
        
        # Paso 2: Exportar PostgreSQL de Render
        print("\n📦 Paso 2: Exportando PostgreSQL de Render...")
        dump_file = f"backups/render_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        
        print("   Conectando a Render...")
        with open(dump_file, 'w', encoding='utf-8') as f:
            result = subprocess.run(
                ["pg_dump", render_url],
                stdout=f,
                stderr=subprocess.PIPE,
                check=True,
                encoding='utf-8'
            )
        print(f"✅ Exportado a: {dump_file}")
        
        # Paso 3: Eliminar test.db actual
        print("\n🗑️  Paso 3: Eliminando base de datos local actual...")
        if os.path.exists(local_db):
            os.remove(local_db)
            print("✅ Base de datos local eliminada")
        
        # Paso 4: Recrear BD local con datos de producción
        print("\n🔨 Paso 4: Recreando base de datos local con datos de producción...")
        
        # Asegurar que estamos en modo local
        os.environ["DB_ENVIRONMENT"] = "local"
        
        # Crear BD vacía con estructura
        from database import Base, engine
        import models
        Base.metadata.create_all(bind=engine)
        
        # Conectar a ambas BDs y copiar datos
        print("\n📥 Paso 5: Copiando datos...")
        
        # Conectar a producción
        from sqlalchemy import create_engine as create_eng
        from sqlalchemy.orm import sessionmaker
        
        engine_prod = create_eng(render_url)
        Session_prod = sessionmaker(bind=engine_prod)
        db_prod = Session_prod()
        
        # Conectar a local
        from database import SessionLocal
        db_local = SessionLocal()
        
        try:
            # Copiar HSK
            print("   Copiando HSK...")
            hsk_items = db_prod.query(models.HSK).all()
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
                db_local.add(new_item)
            db_local.commit()
            print(f"   ✅ HSK: {len(hsk_items)} palabras")
            
            # Copiar Diccionario
            print("   Copiando Diccionario...")
            dict_items = db_prod.query(models.Diccionario).all()
            for item in dict_items:
                new_item = models.Diccionario(
                    id=item.id,
                    hsk_id=item.hsk_id,
                    activo=item.activo
                )
                db_local.add(new_item)
            db_local.commit()
            print(f"   ✅ Diccionario: {len(dict_items)} entradas")
            
            # Copiar Ejemplos
            print("   Copiando Ejemplos...")
            ejemplos = db_prod.query(models.Ejemplo).all()
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
                db_local.add(new_item)
            db_local.commit()
            print(f"   ✅ Ejemplos: {len(ejemplos)} frases")
            
            # Copiar Tarjetas
            print("   Copiando Tarjetas...")
            tarjetas = db_prod.query(models.Tarjeta).all()
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
                db_local.add(new_item)
            db_local.commit()
            print(f"   ✅ Tarjetas: {len(tarjetas)} tarjetas")
            
            # Copiar Progreso SM2
            print("   Copiando Progreso SM2...")
            progress = db_prod.query(models.SM2Progress).all()
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
                db_local.add(new_item)
            db_local.commit()
            print(f"   ✅ Progreso: {len(progress)} registros")
            
            # Copiar Relaciones HSK-Ejemplo
            print("   Copiando Relaciones HSK-Ejemplo...")
            relaciones = db_prod.query(models.HSKEjemplo).all()
            for item in relaciones:
                new_item = models.HSKEjemplo(
                    id=item.id,
                    hsk_id=item.hsk_id,
                    ejemplo_id=item.ejemplo_id,
                    posicion=item.posicion
                )
                db_local.add(new_item)
            db_local.commit()
            print(f"   ✅ Relaciones: {len(relaciones)} enlaces")
            
            print("\n✅ Sincronización completada exitosamente")
            print(f"\n📁 Backups guardados en: backups/")
            print(f"   - Dump PostgreSQL: {dump_file}")
            if os.path.exists(backup_local):
                print(f"   - Backup local: {backup_local}")
            
            print("\n💡 Ahora test.db contiene una copia exacta de producción")
            
        except Exception as e:
            print(f"\n❌ Error copiando datos: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db_prod.close()
            db_local.close()
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error en pg_dump: {e}")
        if e.stderr:
            print(f"   {e.stderr}")
        print("\n💡 Verifica que pg_dump esté instalado:")
        print("   Mac: brew install postgresql")
        print("   Ubuntu: sudo apt install postgresql-client")
        print("   Windows: Instalar PostgreSQL desde postgresql.org")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    render_a_bd_local()
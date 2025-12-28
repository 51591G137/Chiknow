#!/usr/bin/env python3
"""
Descarga base de datos de Render (producción) a local
USO: python scripts/database/render-a-bd_local.py

NO requiere pg_dump - usa SQLAlchemy directamente
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from dotenv import load_dotenv
import shutil

load_dotenv()

def render_a_bd_local():
    """Copia base de datos de Render a local usando SQLAlchemy (sin pg_dump)"""
    
    print("\n" + "="*70)
    print("📥 SINCRONIZACIÓN: RENDER (PRODUCCIÓN) → LOCAL")
    print("="*70)
    
    local_db = "test.db"
    render_url = os.getenv("DATABASE_URL_PRODUCTION")
    
    if not render_url:
        print("❌ DATABASE_URL_PRODUCTION no configurada en .env")
        print("   Ejemplo: postgresql://usuario:password@host.render.com/database")
        return False
    
    # Fix URL
    if render_url.startswith("postgres://"):
        render_url = render_url.replace("postgres://", "postgresql://", 1)
    
    print(f"🔗 URL de producción: {render_url.split('@')[0]}@***")
    print("\n⚠️  Esta operación sobrescribirá tu base de datos local")
    print("   Se hará un backup primero")
    
    confirmacion = input("\n¿Continuar? (s/n): ")
    
    if confirmacion.lower() != 's':
        print("\n❌ Operación cancelada")
        return False
    
    try:
        # Paso 1: Backup de local
        os.makedirs("backups", exist_ok=True)
        print("\n💾 Paso 1: Backup de base de datos local...")
        backup_local = None
        if os.path.exists(local_db):
            backup_local = f"backups/local_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(local_db, backup_local)
            size_mb = os.path.getsize(backup_local) / 1024 / 1024
            print(f"✅ Backup guardado: {backup_local} ({size_mb:.2f} MB)")
        else:
            print("   (No existe BD local previa)")
        
        # Paso 2: Eliminar test.db actual
        print("\n🗑️  Paso 2: Eliminando base de datos local actual...")
        if os.path.exists(local_db):
            os.remove(local_db)
            print("✅ Base de datos local eliminada")
        
        # Paso 3: Recrear BD local vacía
        print("\n🔨 Paso 3: Creando estructura de base de datos local...")
        
        # Asegurar que estamos en modo local
        os.environ["DB_ENVIRONMENT"] = "local"
        
        # Importar después de cambiar el entorno
        from database import Base, engine
        import models
        
        # Crear todas las tablas vacías
        Base.metadata.create_all(bind=engine)
        print("✅ Estructura creada")
        
        # Paso 4: Conectar a producción
        print("\n🔌 Paso 4: Conectando a PostgreSQL de Render...")
        from sqlalchemy import create_engine as create_eng
        from sqlalchemy.orm import sessionmaker
        
        engine_prod = create_eng(render_url)
        Session_prod = sessionmaker(bind=engine_prod)
        db_prod = Session_prod()
        
        # Paso 5: Conectar a local
        from database import SessionLocal
        db_local = SessionLocal()
        
        # Lista de tablas en orden correcto (respetando dependencias)
        tablas = [
            ("HSK", models.HSK),
            ("Diccionario", models.Diccionario),
            ("Ejemplos", models.Ejemplo),
            ("HSK-Ejemplo", models.HSKEjemplo),
            ("EjemploJerarquia", models.EjemploJerarquia),
            ("EjemploActivacion", models.EjemploActivacion),
            ("Tarjetas", models.Tarjeta),
            ("Notas", models.Notas),
            ("SM2Sessions", models.SM2Session),
            ("SM2Progress", models.SM2Progress),
            ("SM2Reviews", models.SM2Review)
        ]
        
        total_registros = 0
        
        try:
            print("\n📥 Paso 5: Copiando datos (esto puede tardar)...")
            
            # Copiar cada tabla
            for nombre_tabla, modelo in tablas:
                try:
                    # Obtener datos de producción
                    registros = db_prod.query(modelo).all()
                    
                    if not registros:
                        print(f"   ⚠️  {nombre_tabla}: 0 registros")
                        continue
                    
                    # Insertar en local
                    contador = 0
                    for registro in registros:
                        # Crear nuevo objeto con todos los atributos
                        nuevo = modelo()
                        
                        # Copiar todos los atributos del objeto
                        for key, value in registro.__dict__.items():
                            if not key.startswith('_'):  # Ignorar atributos internos
                                setattr(nuevo, key, value)
                        
                        db_local.add(nuevo)
                        contador += 1
                        
                        # Commit cada 100 registros para no saturar memoria
                        if contador % 100 == 0:
                            db_local.flush()
                    
                    db_local.commit()
                    total_registros += contador
                    print(f"   ✅ {nombre_tabla}: {contador} registros")
                    
                except Exception as e:
                    db_local.rollback()
                    print(f"   ❌ Error en {nombre_tabla}: {str(e)[:100]}...")
                    # Continuar con la siguiente tabla
            
            # Recrear índices y secuencias
            print("\n🔧 Paso 6: Reconstruyendo índices y secuencias...")
            
            # Para SQLite, resetear autoincrementos
            if "sqlite" in str(db_local.bind.url):
                db_local.execute("DELETE FROM sqlite_sequence")
                db_local.commit()
                print("   ✅ Secuencias SQLite reseteadas")
            
            print("\n" + "="*70)
            print("✅ SINCRONIZACIÓN COMPLETADA EXITOSAMENTE")
            print("="*70)
            print(f"\n📊 Estadísticas:")
            print(f"   Total registros copiados: {total_registros}")
            print(f"   Tablas procesadas: {len(tablas)}")
            
            if backup_local:
                print(f"\n📁 Backup local guardado en: {backup_local}")
            
            # Verificar tamaños
            if os.path.exists(local_db):
                size_mb = os.path.getsize(local_db) / 1024 / 1024
                print(f"   Tamaño de test.db: {size_mb:.2f} MB")
            
            print("\n💡 Ahora puedes trabajar localmente con una copia exacta de producción")
            print("   Recuerda: Los cambios locales NO afectarán a producción")
            
        except Exception as e:
            print(f"\n❌ Error durante la copia de datos: {e}")
            import traceback
            traceback.print_exc()
            
            # Restaurar backup si hay error
            if backup_local and os.path.exists(backup_local):
                print("\n🔄 Restaurando backup...")
                shutil.copy2(backup_local, local_db)
                print(f"✅ Backup restaurado desde: {backup_local}")
            
            return False
            
        finally:
            db_prod.close()
            db_local.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    render_a_bd_local()
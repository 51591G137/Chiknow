#!/usr/bin/env python3
"""
Script para gestionar ejemplos y sus relaciones con HSK
Uso: 
  python3 gestionar_ejemplos.py listar          # Ver todos los ejemplos
  python3 gestionar_ejemplos.py analizar        # Analizar y completar relaciones HSK
  python3 gestionar_ejemplos.py estadisticas    # Ver estadísticas detalladas
"""

import sys
from database import SessionLocal
import models
import repository

def listar_ejemplos():
    """Lista todos los ejemplos cargados"""
    db = SessionLocal()
    
    try:
        ejemplos = db.query(models.Ejemplo).all()
        
        print("="*80)
        print(f"LISTADO DE EJEMPLOS ({len(ejemplos)} total)")
        print("="*80)
        
        if not ejemplos:
            print("\n⚠️  No hay ejemplos cargados")
            print("   Ejecuta: python3 cargar_ejemplos.py")
            return
        
        for ej in ejemplos:
            # Obtener hanzi componentes
            relaciones = db.query(models.HSKEjemplo, models.HSK).join(
                models.HSK, models.HSKEjemplo.hsk_id == models.HSK.id
            ).filter(
                models.HSKEjemplo.ejemplo_id == ej.id
            ).order_by(models.HSKEjemplo.posicion).all()
            
            estado = "✓" if ej.activado else "○"
            en_dict = "📚" if ej.en_diccionario else "  "
            complejidad = ["Simple", "Medio", "Complejo"][ej.complejidad - 1]
            
            print(f"\n{estado} {en_dict} ID:{ej.id:3d} | {ej.hanzi}")
            print(f"       {ej.pinyin}")
            print(f"       {ej.espanol}")
            print(f"       HSK{ej.nivel} | {complejidad} | {len(relaciones)} hanzi")
            
            if relaciones:
                hanzi_str = " + ".join([f"{hsk.hanzi}({hsk.pinyin})" for rel, hsk in relaciones])
                print(f"       Componentes: {hanzi_str}")
            else:
                print(f"       ⚠️  Sin relaciones HSK")
        
        print("\n" + "="*80)
        print("Leyenda:")
        print("  ✓ = Activado (todos hanzi dominados)")
        print("  ○ = No activado (requiere estudio)")
        print("  📚 = En diccionario del usuario")
        
    finally:
        db.close()

def analizar_y_completar_relaciones():
    """Analiza ejemplos y completa relaciones HSK faltantes"""
    db = SessionLocal()
    
    try:
        ejemplos = db.query(models.Ejemplo).all()
        
        print("="*80)
        print("ANÁLISIS DE RELACIONES HSK-EJEMPLO")
        print("="*80)
        
        ejemplos_sin_relaciones = []
        ejemplos_con_hanzi_faltantes = []
        
        for ej in ejemplos:
            # Obtener relaciones existentes
            relaciones = db.query(models.HSKEjemplo).filter(
                models.HSKEjemplo.ejemplo_id == ej.id
            ).all()
            
            if not relaciones:
                ejemplos_sin_relaciones.append(ej)
                continue
            
            # Analizar cada hanzi de la frase
            hanzi_en_frase = [c for c in ej.hanzi if '\u4e00' <= c <= '\u9fff']
            hanzi_relacionados = set()
            
            for rel in relaciones:
                hsk = db.query(models.HSK).filter(models.HSK.id == rel.hsk_id).first()
                if hsk:
                    hanzi_relacionados.add(hsk.hanzi)
            
            hanzi_faltantes = [h for h in hanzi_en_frase if h not in hanzi_relacionados]
            
            if hanzi_faltantes:
                ejemplos_con_hanzi_faltantes.append((ej, hanzi_faltantes))
        
        # Reportar ejemplos sin relaciones
        if ejemplos_sin_relaciones:
            print(f"\n⚠️  {len(ejemplos_sin_relaciones)} ejemplos SIN relaciones HSK:")
            for ej in ejemplos_sin_relaciones:
                print(f"   ID:{ej.id:3d} | {ej.hanzi} ({ej.pinyin})")
        
        # Reportar ejemplos con hanzi faltantes
        if ejemplos_con_hanzi_faltantes:
            print(f"\n⚠️  {len(ejemplos_con_hanzi_faltantes)} ejemplos con hanzi NO relacionados:")
            for ej, faltantes in ejemplos_con_hanzi_faltantes:
                print(f"   ID:{ej.id:3d} | {ej.hanzi}")
                print(f"           Faltantes: {', '.join(faltantes)}")
                
                # Buscar estos hanzi en HSK
                for hanzi in faltantes:
                    hsk = db.query(models.HSK).filter(models.HSK.hanzi == hanzi).first()
                    if hsk:
                        print(f"             → {hanzi}: Encontrado en HSK ID:{hsk.id}")
                    else:
                        print(f"             → {hanzi}: NO existe en tabla HSK")
        
        # Ofrecer completar automáticamente
        if ejemplos_sin_relaciones or ejemplos_con_hanzi_faltantes:
            print("\n" + "="*80)
            respuesta = input("¿Quieres completar automáticamente las relaciones? (s/n): ")
            
            if respuesta.lower() == 's':
                completar_relaciones_automaticas(db)
            else:
                print("❌ Operación cancelada")
        else:
            print("\n✅ Todas las relaciones están completas")
        
    finally:
        db.close()

def completar_relaciones_automaticas(db):
    """Completa automáticamente relaciones HSK-Ejemplo faltantes"""
    print("\n🔄 Completando relaciones automáticamente...")
    
    ejemplos = db.query(models.Ejemplo).all()
    relaciones_añadidas = 0
    
    for ej in ejemplos:
        # Obtener relaciones existentes
        relaciones_existentes = db.query(models.HSKEjemplo).filter(
            models.HSKEjemplo.ejemplo_id == ej.id
        ).all()
        
        hanzi_ya_relacionados = set()
        max_posicion = 0
        
        for rel in relaciones_existentes:
            hsk = db.query(models.HSK).filter(models.HSK.id == rel.hsk_id).first()
            if hsk:
                hanzi_ya_relacionados.add(hsk.hanzi)
            if rel.posicion > max_posicion:
                max_posicion = rel.posicion
        
        # Analizar hanzi en la frase
        posicion = max_posicion + 1
        for caracter in ej.hanzi:
            # Solo hanzi chinos
            if not ('\u4e00' <= caracter <= '\u9fff'):
                continue
            
            # Si ya está relacionado, saltar
            if caracter in hanzi_ya_relacionados:
                continue
            
            # Buscar en HSK
            hsk = db.query(models.HSK).filter(models.HSK.hanzi == caracter).first()
            
            if hsk:
                # Crear relación
                nueva_relacion = models.HSKEjemplo(
                    hsk_id=hsk.id,
                    ejemplo_id=ej.id,
                    posicion=posicion
                )
                db.add(nueva_relacion)
                relaciones_añadidas += 1
                posicion += 1
                print(f"  ✓ Añadida relación: Ejemplo {ej.id} ↔ HSK {hsk.id} ({hsk.hanzi})")
    
    db.commit()
    print(f"\n✅ Se añadieron {relaciones_añadidas} relaciones nuevas")

def mostrar_estadisticas():
    """Muestra estadísticas detalladas de ejemplos"""
    db = SessionLocal()
    
    try:
        total = db.query(models.Ejemplo).count()
        activados = db.query(models.Ejemplo).filter(models.Ejemplo.activado == True).count()
        en_diccionario = db.query(models.Ejemplo).filter(models.Ejemplo.en_diccionario == True).count()
        
        simple = db.query(models.Ejemplo).filter(models.Ejemplo.complejidad == 1).count()
        medio = db.query(models.Ejemplo).filter(models.Ejemplo.complejidad == 2).count()
        complejo = db.query(models.Ejemplo).filter(models.Ejemplo.complejidad == 3).count()
        
        total_relaciones = db.query(models.HSKEjemplo).count()
        
        print("="*80)
        print("ESTADÍSTICAS DE EJEMPLOS")
        print("="*80)
        
        print(f"\n📊 General:")
        print(f"  Total ejemplos:          {total}")
        print(f"  Activados:               {activados} ({activados/total*100:.1f}%)" if total > 0 else "  Activados: 0")
        print(f"  En diccionario usuario:  {en_diccionario}")
        print(f"  Por activar:             {total - activados}")
        
        print(f"\n📈 Por complejidad:")
        print(f"  Simple (1-2 hanzi):      {simple}")
        print(f"  Medio (3-4 hanzi):       {medio}")
        print(f"  Complejo (5+ hanzi):     {complejo}")
        
        print(f"\n🔗 Relaciones HSK:")
        print(f"  Total relaciones:        {total_relaciones}")
        print(f"  Promedio por ejemplo:    {total_relaciones/total:.1f}" if total > 0 else "  Promedio: 0")
        
        # Top 10 ejemplos por número de hanzi
        print(f"\n🏆 Top 10 ejemplos más complejos:")
        ejemplos_complejos = db.query(
            models.Ejemplo,
            db.query(models.HSKEjemplo).filter(
                models.HSKEjemplo.ejemplo_id == models.Ejemplo.id
            ).count().label('num_hanzi')
        ).order_by('num_hanzi DESC').limit(10).all()
        
        for i, (ej, num_hanzi) in enumerate(ejemplos_complejos, 1):
            print(f"  {i:2d}. {ej.hanzi} ({num_hanzi} hanzi)")
        
    finally:
        db.close()

def mostrar_ayuda():
    """Muestra ayuda de uso"""
    print("""
GESTIÓN DE EJEMPLOS

Uso:
  python3 gestionar_ejemplos.py COMANDO

Comandos:
  listar          - Lista todos los ejemplos con sus detalles
  analizar        - Analiza y completa relaciones HSK-Ejemplo
  estadisticas    - Muestra estadísticas detalladas
  help            - Muestra esta ayuda

Ejemplos:
  python3 gestionar_ejemplos.py listar
  python3 gestionar_ejemplos.py analizar
  python3 gestionar_ejemplos.py estadisticas
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        mostrar_ayuda()
    else:
        comando = sys.argv[1].lower()
        
        if comando == 'listar':
            listar_ejemplos()
        elif comando == 'analizar':
            analizar_y_completar_relaciones()
        elif comando in ['estadisticas', 'stats']:
            mostrar_estadisticas()
        elif comando in ['help', 'ayuda', '--help', '-h']:
            mostrar_ayuda()
        else:
            print(f"❌ Comando desconocido: {comando}")
            mostrar_ayuda()
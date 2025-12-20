import csv
from main import SessionLocal, HSK

# Iniciamos la sesión de la base de datos
db = SessionLocal()

try:
    # Abrimos el archivo CSV. 
    # 'utf-8-sig' es la clave para que lea bien los caracteres chinos (Hanzi) y el pinyin
    with open('datos.csv', mode='r', encoding='utf-8-sig') as archivo:
        # Usamos el lector de CSV estándar
        lector = csv.reader(archivo)
        
        print("Empezando la carga de datos...")
        
        for fila in lector:
            # Según tu ejemplo: 1,1,çˆ±,Ã i,"amar, querer"
            # fila[0] = numero, fila[1] = nivel, fila[2] = hanzi, fila[3] = pinyin, fila[4] = espanol
            
            nueva_palabra = HSK(
                numero=int(fila[0]),
                nivel=int(fila[1]),
                hanzi=fila[2],
                pinyin=fila[3],
                espanol=fila[4]
            )
            db.add(nueva_palabra)
        
        # Guardamos todos los cambios en la base de datos
        db.commit()
        print("¡Carga completada con éxito!")

except FileNotFoundError:
    print("Error: No se encontró el archivo 'datos.csv'. Asegúrate de subirlo a la misma carpeta.")
except Exception as e:
    db.rollback() # Si algo falla, deshacemos los cambios para no corromper la DB
    print(f"Hubo un error durante la carga: {e}")
finally:
    db.close() # Siempre cerramos la conexión al terminar
# test_quick.py
from app.database import SessionLocal
from app import models, repository

db = SessionLocal()

# Crear palabra de prueba
test_word = models.HSK(id=999, numero=999, nivel=1, hanzi="好", pinyin="hǎo", espanol="bien")
db.add(test_word)
db.commit()

# Buscar con y sin acentos
result1 = repository.search_hsk(db, "hǎo")  # Con acento
result2 = repository.search_hsk(db, "hao")  # Sin acento

print(f"Con acento: {len(result1)} resultados")
print(f"Sin acento: {len(result2)} resultados")

# Limpiar
db.delete(test_word)
db.commit()
db.close()

# Ambos deberían devolver >= 1
assert len(result1) >= 1, "Búsqueda con acento falló"
assert len(result2) >= 1, "Búsqueda sin acento falló"
print("✅ Búsqueda funcionando correctamente")
#!/usr/bin/env python3
"""Script para corregir los 4 tests problemáticos"""

with open('tests/test_cache.py', 'r') as f:
    lines = f.readlines()

# Patch 1: líneas 68-77 (test_respuesta_usuario_max_length)
lines[67:77] = [
    '        """respuesta_usuario tiene longitud máxima de 500 - rechaza si excede"""\n',
    '        long_text = "a" * 600\n',
    '        data = {\n',
    '            "tarjeta_id": 1,\n',
    '            "session_id": 1,\n',
    '            "quality": 2,\n',
    '            "respuesta_usuario": long_text\n',
    '        }\n',
    '        # Debe rechazar texto demasiado largo\n',
    '        with pytest.raises(ValidationError):\n',
    '            ReviewRequest(**data)\n',
    '        \n',
    '        # Exactamente 500 debe pasar\n',
    '        valid_data = data.copy()\n',
    '        valid_data["respuesta_usuario"] = "a" * 500\n',
    '        request = ReviewRequest(**valid_data)\n',
    '        assert len(request.respuesta_usuario) == 500\n',
]

# Ajustar índices por cambio de líneas (+7 líneas)
# Patch 2: líneas 109-114 -> ahora 116-121
lines[115:121] = [
    '        """nota tiene longitud máxima de 2000 - rechaza si excede"""\n',
    '        long_nota = "a" * 2500\n',
    '        # Debe rechazar nota demasiado larga\n',
    '        with pytest.raises(ValidationError):\n',
    '            NotaRequest(nota=long_nota)\n',
    '        \n',
    '        # Exactamente 2000 debe pasar\n',
    '        valid_nota = "a" * 2000\n',
    '        request = NotaRequest(nota=valid_nota)\n',
    '        assert len(request.nota) == 2000\n',
]

# Ajustar índices (+9 líneas en total)
# Patch 3: líneas 139-144 -> ahora 155-160
lines[154:160] = [
    '        """query tiene longitud máxima de 100 - rechaza si excede"""\n',
    '        long_query = "a" * 150\n',
    '        # Debe rechazar query demasiado largo\n',
    '        with pytest.raises(ValidationError):\n',
    '            SearchQuery(query=long_query)\n',
    '        \n',
    '        # Exactamente 100 debe pasar\n',
    '        valid_query = "a" * 100\n',
    '        query = SearchQuery(query=valid_query)\n',
    '        assert len(query.query) == 100\n',
]

# Ajustar índices (+11 líneas en total)
# Patch 4: líneas 273-281 -> ahora 293-298 (necesitamos encontrar el contexto)
# Buscar la línea con "ejemplo = EjemploCreate(**data)"
for i, line in enumerate(lines):
    if 'ejemplo = EjemploCreate(**data)' in line and 'many_ids' in lines[i-2]:
        # Reemplazar desde "ejemplo = EjemploCreate" hasta "assert len(ejemplo.hanzi_ids) == 20"
        lines[i:i+2] = [
            '        # Debe rechazar lista demasiado larga\n',
            '        with pytest.raises(ValidationError):\n',
            '            EjemploCreate(**data)\n',
            '        \n',
            '        # Exactamente 20 debe pasar\n',
            '        valid_data = data.copy()\n',
            '        valid_data["hanzi_ids"] = list(range(1, 21))\n',
            '        ejemplo = EjemploCreate(**valid_data)\n',
            '        assert len(ejemplo.hanzi_ids) == 20\n',
        ]
        break

with open('tests/test_cache.py', 'w') as f:
    f.writelines(lines)

print("✅ Archivo parcheado exitosamente")

NOTAS INTERNAS — NO DISTRIBUIR — solo para quien mantiene este módulo
(referencia de trabajo de Claude/Orange Crew; no es documentación de producto)

`_k9d2.dat` (XOR con llave "OC-9k-reglas-2026" + base85 de un JSON):

fz (fuzzy_matcher.py):
  sw = lista de stopwords para tokenizar descripciones
  um = umbral mínimo de similitud combinada para aceptar coincidencia difusa
  cf = [a, b] en confianza_desde_similitud: confianza = a + similitud * b

re (rule_engine.py):
  um = UMBRAL_DIFUSO, mínimo score de similitud combinada (nivel 5)
  cf = [base, tope] en nivel 4: confianza = min(tope, base + len(palabra_clave))

Si se necesita regenerar el .dat: mismo esquema que
`backend/app/exporters/_r7f3a.dat`, cambiando solo la llave y el
diccionario en claro. Correr las pruebas de negocio (casos de
`rule_engine`/`fuzzy_matcher` con ejemplos conocidos) antes de reemplazar.

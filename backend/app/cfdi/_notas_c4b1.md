NOTAS INTERNAS — NO DISTRIBUIR — solo para quien mantiene este módulo
(referencia de trabajo de Claude/Orange Crew; no es documentación de producto)

`_c4b1.dat` (XOR con llave "OC-4c-cfdi-2026" + base85 de un JSON):

cm (cfdi_matcher.py):
  ventana = días de tolerancia entre fecha del CFDI y fecha del movimiento
  tol     = tolerancia en pesos para considerar dos importes "iguales"
  cf      = [con_rfc, sin_rfc] confianza según si el movimiento trae RFC

ca (conciliador_avanzado.py):
  ventana   = días de tolerancia (más ancha que cm, porque agrupa varios)
  tol       = tolerancia en pesos
  max_items = tamaño máximo de combinación N:1 que se prueba (itertools)
  max_cand  = cuántos candidatos entran a la búsqueda de combinaciones
  cf        = confianza por tipo de match:
              exacto 1:1=100, N facturas->1 mov=88, N movs->1 factura=85,
              pago parcial=65, monto sin RFC=70
  disp_dias = umbral de dispersión de fechas para decidir el texto del
              motivo en "N movs -> 1 factura" (<=2 días: "se facturan
              juntas"; más: "pagos parciales acumulados")

Regenerar con el mismo esquema que `backend/app/exporters/_r7f3a.dat`
(otra llave). Correr `backend/tests/test_conciliador_avanzado.py` antes
de reemplazar el .dat.

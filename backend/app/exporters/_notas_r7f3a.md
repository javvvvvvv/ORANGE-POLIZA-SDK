NOTAS INTERNAS — NO DISTRIBUIR — solo para quien mantiene este exportador
(referencia de trabajo de Claude/Orange Crew; no es documentación de producto)

Índices de `_r7f3a.dat` por tipo de renglón (cada tipo es una lista; el
índice es la posición dentro de esa lista, en el orden en que los usa
`contpaqi_txt_exporter.py`):

P : 0 fch8=AAAAMMDD | 1 tpo1=1ing/2egr | 2 fol~r10 | 3 dsc101=texto | 4 gid36
M1: 0 ctaA31 | 1 refB31 | 2 nat1=0cargo/1abono | 3 imp21 | 4 gid36 | 5 fch8
AM/AD: 0 gid36 (uuid CFDI)
I : 0 pid5(opc) | 1 anio4 | 2 mes~i2 (izquierda, NO derecha; se confundio con derecha el 23-ago-2026) | 3 ctaRel31 | 4 serie19 | 5 fol~r8 (truncable, ver permitir_truncar)
    | 6 gid36(uuid cfdi) | 7 tasa%10 | 8 base21 | 9 iva21 | 10 tot21
    | 11/12 base-egr(0.0[42]|base[21]) | 13/14 base-ing(base[42]|0.0[21])
      [excluyentes, ver es_egreso en el código; anchos reales confirmados
      con el hueco hasta el siguiente campo real, NO con el largo del
      valor de ejemplo — ese fue el bug de "no cabe en la columna" del
      23-ago-2026, ya corregido] | 15 gid36(propio, no cfdi) | 16 conc21
    | 17 subc21 | 18 ded1
W2: 0 base21
V : 0 totFac21 | 1 tasa%10 | 2 baseTot21 | 3 ivaTot21 | 4 serie19 | 5 fol~r8 (truncable)
    | 6 netoRet21 | 7 totFac2_21 | 8 anio4 | 9 mes~i2 (izquierda, NO derecha; se confundio con derecha el 23-ago-2026) | 10 ctaRel31 | 11 gid36
R : 0 anio4 | 1 mes~i2 (izquierda, NO derecha; se confundio con derecha el 23-ago-2026)
D : 0 baseMenosIva21 | 1 tot21 | 2 baseMenosIva21b | 3 iva21

LIMITACIÓN CONOCIDA (revisada 23-ago-2026, con ~200 pólizas reales de
INGRESOS.TXT/EGRESOS.TXT del usuario): el folio de CFDI (I idx5, V idx5)
se confirmó y ensanchó a 8 dígitos (antes 5) porque en los ejemplos
reales aparecen folios de hasta 8 dígitos sin serie o con serie corta,
SIN chocar nunca con el campo de serie (máximo 12 caracteres, siempre
deja hueco). Un solo caso con un folio de 12 dígitos (sin serie) no
encajó ni ensanchando — para ese caso extremo, en vez de tronar todo el
lote, el folio se trunca (permitir_truncar=True); la asociación real con
Contpaqi de todos modos depende del UUID (I idx6), no de este folio de
referencia, así que truncarlo no afecta el cuadre ni la conciliación.

Reglas de armado (no están en el .dat, van en el código):
- AM se agrega tras cada M1 salvo si es_egreso=True y la línea es la
  cuenta == mov.cuenta_banco (esa asociación ya la lleva I/V).
- En ingresos, el renglón R va justo después del primer M1 (antes de su AM).

"~r" = right-justify (últimos N caracteres de la columna, no el ancho
completo declarado en _r7f3a.dat — el ancho real de cada bloque ya está
resuelto dentro del .dat, esto solo aclara la alineación).

Si algún día hay que tocar un offset: NO editar a mano el .dat (es un
XOR+base85 del JSON real). Regenerar con el mismo script de siempre
(llave fija "OC-7f-poliza-2026") a partir del diccionario en claro y
volver a correr las pruebas de bytes contra las 2 pólizas de referencia
del usuario antes de reemplazar el archivo.

RETENCIONES (agregado 23-ago-2026, con póliza real de retenciones del
usuario — honorarios, ISR 1.25% + IVA retenido 10.6667%):
- I nuevo idx18 [183,184]: '1' traslado normal | '2' retención.
- I nuevo idx19 [187,188]: '1' ISR | '2' IVA.
- I nuevo idx14 [441,477]: uuid PROPIO de la línea de traslado principal
  de esa factura — solo se llena en líneas de retención, para ligarlas.
  El orden real en el archivo es: retenciones PRIMERO, línea de traslado
  (+ su W2) al final; por eso el guid de la principal se genera antes.
- I idx12 (base repetida, antes [360,381] fijo): solo se llena en la
  línea de traslado; en una retención va "0.0".
- I idx10 (total): en una retención es el importe retenido tal cual
  (NO base+importe).
- V nuevos idx7/idx8 [185,206]/[206,227]: IVA retenido / ISR retenido.
- V idx6 [164,185]: total factura SIN restar retenciones (antes yo
  pensaba que era "neto", estaba mal — ver idx9).
- V idx9 (antes idx7) [227,248]: neto a pagar = total - ret_iva - ret_isr.
- V nuevo idx14 [347,360]: RFC de la contraparte de esa factura (antes
  quedaba con el RFC de la plantilla pegado, mal para cualquier persona
  distinta a la del ejemplo original).
- Tasas con más de 2 decimales (ej. 10.6667 = 2/3 de 16%) usan _num_tasa
  (4 decimales) en vez de _num (2).
- El folio vacío ahora se escribe como "0", no como espacios en blanco.
- Se quitó el "skip AM en la línea de cuenta_banco": la póliza de
  retenciones (limpia, prototípica) muestra que TODAS las líneas M1
  llevan AM, sin excepción. La única póliza donde vi un skip
  (recibida.txt original) tiene toda la pinta de ser un ajuste/traspaso
  raro, no un pago normal de factura.
- Retención en el lado INGRESO: implementado por simetría con egreso,
  sin ningún ejemplo real que lo confirme — avisar antes de confiar en
  eso si aparece un caso real.
- SIN CFDI = SIN retención, punto. El usuario lo confirmó explícitamente
  (23-ago-2026): a diferencia de la base/IVA normal (que si no hay CFDI
  se calcula en exento como respaldo), las retenciones NO tienen método
  alterno. Si un movimiento no trae CFDI conciliado, no se le calcula
  ni se le estima ninguna retención — es una decisión de negocio, no
  algo que falte implementar.

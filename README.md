# Orange Poliza Engine

Motor de automatización contable configurable: lee estados de cuenta
(Excel / PDF), los clasifica con un motor de reglas por empresa (no
código, no IA suelta), calcula los importes con fórmulas configurables
(`TOTAL/1.16`, `IVA`, `RET_IVA`, etc.), genera pólizas cuadradas y las
exporta en formato de importación masiva de Contpaqi. Multiempresa,
multiusuario, pensado para vivir en un servidor local al que entra todo
el equipo desde el navegador.

Este repo nace de `tuy.py` (el sistema anterior en Tkinter+SQLite): esa
lógica de negocio (formatos de estado de cuenta, manejo de IVA/retenciones,
estructura de póliza P/M1) se conservó y se generalizó; la arquitectura
(Tkinter, todo en un archivo, un usuario, una empresa a la vez) se
reemplazó por completo.

## Cambios recientes

- **Aplicación web funcional** en `webapp/` (Flask + PostgreSQL + Tailwind vía
  CDN, sin build step de Node). Multiusuario y multiempresa de verdad:
  login con contraseña hasheada, roles por empresa, y un asistente de
  primer arranque (`/setup`) que crea la organización, el usuario admin
  y la primera empresa.
- **Catálogo de cuentas** (`catalogo_repo.py` + pantalla "Catálogo"):
  subir Excel o pegar texto, igual que hacía `tuy.py`, con búsqueda y
  autocompletado (`<datalist>`) en los campos de cuenta del constructor
  de reglas y de la configuración.
- **Configuración de IVA por empresa** (cuentas acreditable / por
  acreditar / trasladado / por trasladar, complementarias en dólares,
  diferencias cambiarias, retenciones) — equivalente a "Configurar IVA"
  del sistema anterior, ahora en la pantalla "Configuración".
- **Multi-banco real**: tabla `bancos` con CRUD completo; cada estado de
  cuenta importado queda ligado a un banco, y el exportador usa la
  cuenta contable de ESE banco (no una fija) al armar las filas `I`/`V`
  de CFDI.
- **Importar mejorado**: acepta **varios archivos Excel a la vez**
  (mismo banco/formato), permite indicar la hoja, y **persiste el
  archivo original** en `webapp/uploads/<empresa_id>/` en vez de
  perderlo en una carpeta temporal.
- **Estado de cuenta marcado de vuelta** (`marcado_repo.py`, pantalla
  "Documentos importados"): regenera el Excel original con las filas
  procesadas resaltadas en amarillo y una columna nueva "Número de
  Póliza" (`EG-1`, `IN-3`, etc.) — el mismo comportamiento que
  `marcar_estado_cuenta()` tenía en `tuy.py`, ahora también disponible
  para descargar desde la web.
- **Revisión de pólizas** (pantalla "Pólizas"): lista todo lo generado,
  marca cuadradas/no cuadradas, y despliega el "por qué se generó así"
  de cada una.
- Migración automática de esquema (`db.py`) para que una base de datos
  ya creada con una versión anterior no pierda datos al agregar columnas
  nuevas.

## Cómo correr la aplicación web

En Windows: doble clic en `iniciar_orange_poliza.bat` — instala lo que
falte y abre el navegador solo.

En este entorno de desarrollo (Linux/Mac, manualmente):
```bash
cd webapp
pip install -r requirements.txt
python3 app.py
```
Abre `http://127.0.0.1:5000`. La primera vez te manda a `/setup` para
crear tu cuenta y tu primera empresa.

## Cambios recientes (este turno)

- **Multiusuario real, no solo de esquema**: ahora hay pantalla
  "Usuarios" (dentro de cada empresa) para agregar más gente — si el
  correo ya existe en tu organización solo se le da acceso a la
  empresa con un rol; si no existe, se crea ahí mismo. Antes solo se
  podía crear el primer usuario en `/setup`, que era el hueco real que
  tenía el sistema para ser "multiusuario de verdad".
- **CFDI 100% opcional, y ahora lo dice explícitamente en la pantalla**:
  importar Excel nunca dependió de subir XML (son rutas separadas desde
  el principio), pero la pantalla de importar ahora lo marca con una
  etiqueta "Opcional" y explica que el flujo funciona completo sin eso.
- **Asistente movimiento por movimiento** (pantalla "Clasificar
  pendientes", ahora la ruta principal `/pendientes`): muestra un
  movimiento a la vez — descripción, monto, tipo — con un campo de
  cuenta con autocompletado contra el catálogo y un checkbox de IVA,
  igual que `tuy.py`. Al guardar arma la plantilla contable (2 o 3
  líneas) automáticamente, crea la regla, clasifica de un jalón todos
  los movimientos parecidos, y pasa solo al siguiente pendiente. El
  constructor de reglas con fórmulas manuales sigue disponible como
  "modo avanzado" para retenciones o combinaciones raras.
- **Vista previa del Excel al importar**: ya no se escribe el nombre de
  columna a ciegas. Subes el archivo, el sistema muestra qué pestañas
  tiene (si hay varias) y una tabla con las primeras filas reales;
  luego eliges con clics (`<select>`, no texto libre) qué columna es
  fecha, cuál descripción, ingresos/egresos, etc. Soporta variar la
  pestaña sin volver a subir el archivo.
- **Botones de navegación reordenados según el flujo real**: Dashboard
  → Configuración inicial (catálogo, IVA/bancos, usuarios) →
  Importar → Clasificar pendientes → Reglas → Generar pólizas →
  Revisar → Exportar, con la barra lateral agrupada por sección en vez
  de una lista plana.

## Cambios recientes (este turno)

- **Coincidencia difusa de texto** (`core/fuzzy_matcher.py`, integrado
  en `rule_engine.py` como nivel "difusa"): reconoce que "CLIE COMERC
  NORTE" y "COMERCIALIZADORA NORTE DEPOSITO" se refieren al mismo
  cliente que la regla ya conoce, comparando palabra por palabra
  (ignorando conectores como DE/DEL/SA/CV) con detección de
  abreviaturas y tolerancia a texto reordenado. Confianza siempre menor
  a una coincidencia exacta (50-80%).
- **Conciliador avanzado de CFDI ↔ movimientos** (`cfdi/conciliador_avanzado.py`):
  ya no solo resuelve 1 factura = 1 movimiento. Ahora encuentra, con un
  algoritmo de subset-sum:
  - **Pagos parciales**: un movimiento cubre solo parte de una factura;
    se acumulan cronológicamente hasta liquidarla, con saldo pendiente
    calculado.
  - **Varias facturas en un solo pago** (N facturas → 1 movimiento).
  - **Varios movimientos que juntos pagan una factura** (N movimientos
    → 1 factura) — el caso típico de comisiones bancarias acumuladas
    todo el mes en una sola factura.
  - **Coincidencia solo por importe**, cuando el movimiento no trae RFC.

  Solo el caso 100% exacto (RFC + importe) se aplica solo; todo lo
  demás queda en la nueva pantalla **"Conciliaciones sugeridas"** para
  confirmar o descartar con un clic, con la explicación de por qué el
  algoritmo lo propuso.
- **Multiempresa real**: ahora se puede crear más empresas desde la
  app (`+ Nueva empresa` en el selector), no solo la primera en
  `/setup`.
- **Reglas generales por empresa** (Configuración → "Reglas
  generales"): define cómo son "naturalmente" tus ingresos y egresos
  más allá de lo obvio — ej. algunas empresas además del IVA llevan
  "cargo Ingresos por aplicar / abono Ingresos". Estas líneas se
  agregan solas a cualquier movimiento que claificiques con el
  asistente rápido.
- **"Afectable a impuestos"** en el asistente movimiento por
  movimiento: si se desmarca (nómina, préstamos entre cuentas propias),
  el movimiento va directo banco ↔ la cuenta elegida, sin IVA ni
  reglas generales, sin importar lo que digan esas configuraciones.
- **El asistente ya no pregunta nada si el movimiento ya tiene un CFDI
  confirmado**: muestra la factura, base e IVA exactos que ya sabe por
  el XML, y solo pide la cuenta contable del cliente/proveedor si
  todavía no existe una regla para ese RFC.

## Cambios recientes (este turno — correcciones reportadas en Windows)

- **Arreglado el `PermissionError: [WinError 32]` al importar en
  Windows**: la causa era `pd.ExcelFile(ruta)` en `listar_hojas()`
  dejando el archivo abierto (nunca se cerraba), lo que bloqueaba el
  archivo para cualquier operación posterior — típico en Windows,
  donde los locks de archivo son estrictos (en Linux/Mac no se nota).
  Ahora todo el importador usa `with pd.ExcelFile(...) as xls:` para
  cerrar siempre. Además, el movimiento del archivo temporal a su
  carpeta final ahora reintenta con una breve espera y, si Windows
  sigue sin soltar el archivo (ej. un antivirus escaneándolo), cae a
  copiar en vez de mover — así el import nunca truena solo por esto.
- **Vista previa rediseñada**: el problema real era que bancos como
  BBVA o Banamex meten varias filas de logo/resumen antes de la tabla
  real, así que la vista previa vieja mostraba esas filas como si
  fueran encabezados y no servía. Ahora primero se ve la hoja cruda con
  números de fila (como en Excel) y un enlace "Usar esta fila" junto a
  cada una; al elegir la fila correcta, se recarga con esa fila como
  encabezado real y aparece el formulario de mapeo de columnas.
- **CFDI con dos botones separados** (Emitidos / Recibidos) en vez de
  uno solo: ahora el tipo se indica explícitamente en vez de
  adivinarlo por el RFC de la empresa, lo cual es mucho más confiable
  si el RFC de la empresa todavía no está bien capturado en
  Configuración — se probó que un CFDI con RFC que no coincide con
  nada configurado igual se clasifica bien gracias al botón usado.

## Cambios recientes (este turno — corrección de exportación .xls)

- **Arreglado por qué no exportaba `.xls` aunque ya se hubiera instalado
  LibreOffice**: el instalador de LibreOffice en Windows **no agrega
  `soffice` al PATH del sistema** — por eso, aunque estuviera instalado,
  Python no lo encontraba con el comando `soffice` a secas.
  `xls_writer.py` ahora también busca en las rutas de instalación
  típicas (`C:\Program Files\LibreOffice\program\soffice.exe` y la
  versión x86), sin necesidad de tocar el PATH. Si de plano no está
  instalado en ningún lado, el mensaje de error ahora dice exactamente
  dónde se buscó, en vez de fallar en silencio con un `.xlsx`
  renombrado. El `.bat` también se actualizó para revisar esas mismas
  rutas al arrancar.

## Cambios recientes (este turno — corrección de "Not Found" al guardar)

- **Arreglado el `404 Not Found` al guardar en "asignar rápido"** (y en
  varios otros botones): era un bug clásico de URLs relativas en HTML.
  Páginas como `/empresas/<id>/pendientes` no terminan en `/`, así que
  un formulario con acción relativa tipo `action="5/asignar-rapido"` lo
  resuelve el navegador como `/empresas/<id>/5/asignar-rapido` (mal) en
  vez de `/empresas/<id>/pendientes/5/asignar-rapido` (correcto). Se
  revisó **toda** la aplicación y se corrigieron a rutas absolutas los
  formularios/enlaces afectados: asignar rápido y omitir (el que
  reportaste), reglas (activar/desactivar/eliminar/nueva), catálogo
  (eliminar todo), usuarios (quitar), documentos (descargar marcado) y
  conciliaciones (confirmar/rechazar). Ninguno de estos dependía ya de
  la posición relativa de la página, así que no debería volver a pasar
  aunque cambien las rutas en el futuro.

## Qué ya existe y corre (esta fase: el motor)

```
backend/
  app/
    core/
      formula_engine.py     # evalúa fórmulas de forma segura (ast, no eval)
      rule_engine.py         # encuentra qué regla aplica a un movimiento
      learning_engine.py     # convierte una clasificación manual en regla
      rules_repository.py    # CRUD persistente de reglas (PostgreSQL, vía webapp/db.py)
      policy_generator.py    # aplica la plantilla de la regla y cuadra la póliza
    importers/
      excel_importer.py      # 3 formatos de estado de cuenta, configurables
    exporters/
      contpaqi_exporter.py   # exporta a .xls formato P/M1/AM/I/W2/V/AD de Contpaqi
      xls_writer.py           # convierte a .xls real (BIFF8) vía LibreOffice headless
    cfdi/
      cfdi_importer.py        # parsea CFDI 3.3/4.0 (XML del SAT)
      cfdi_matcher.py          # concilia CFDI <-> movimientos bancarios automáticamente
  tests/
    test_formula_engine.py       # pruebas de seguridad (anti-inyección) + cálculo
    demo_end_to_end.py           # demo mínimo del motor de reglas + pólizas
    pipeline_demo.py              # PIPELINE COMPLETO: excel + CFDI -> reglas -> pólizas -> .xls
    generar_estado_cuenta_ejemplo.py
    generar_cfdis_ejemplo.py
database/
  schema.sql                              # modelo de datos completo (multiempresa/multiusuario)
  plantilla_encabezados_contpaqi.xlsx     # bloque de encabezados/esquema real, tomado del archivo de referencia
  ejemplo_contpaqi_referencia.xls         # el archivo de referencia original que compartiste
```

### Cómo correrlo

Solo necesita Python 3 + pandas + openpyxl (no requiere red ni servidor):

```bash
cd backend/tests
python3 test_formula_engine.py     # 25 pruebas: fórmulas válidas + intentos de inyección
python3 demo_end_to_end.py          # motor de reglas + generación de pólizas, explicado paso a paso
python3 pipeline_demo.py            # pipeline completo con Excel de entrada y de salida
```

## Decisiones de diseño importantes (para no perderlas de vista)

1. **Las reglas viven en datos, no en código.** `Regla` y
   `LineaPlantilla` son estructuras; en producción son filas de
   PostgreSQL (`database/schema.sql`), nunca `if descripcion == "OXXO"`
   escrito a mano.

2. **Las fórmulas no usan `eval()`.** `formula_engine.py` parsea con el
   módulo `ast` y solo permite números, las variables conocidas
   (`TOTAL`, `BASE`, `IVA`, `RET_IVA`, `RET_ISR`, `TIPO_CAMBIO`), los
   operadores `+ - * /` y `round/abs/min/max`. Todo lo demás se
   rechaza. Esto importa porque el usuario final (un contador, no un
   programador) va a escribir estas fórmulas desde la interfaz web.

3. **Prioridad de clasificación siempre determinista:**
   RFC exacto → cuenta bancaria exacta → descripción exacta →
   contiene palabra clave → sin coincidencia (revisión manual). La IA,
   cuando se conecte (Fase 6 del roadmap), entra únicamente como una
   sugerencia adicional en el último escalón, nunca reemplaza este
   orden.

4. **Toda póliza sabe explicarse.** `generar_poliza()` regresa una
   lista `explicacion` en español, paso a paso, lista para mostrarse en
   el "visor de por qué hizo esto" de la interfaz.

5. **El formato de salida no cambia aunque el motor sí.**
   `contpaqi_exporter.py` reproduce la estructura P/M1 exacta que ya
   tenías validada con Contpaqi en `tuy.py`, para no romper la
   compatibilidad con lo que el despacho ya usa.

## Por qué esto no se puede terminar de construir en este chat

Esta conversación corre en un entorno sin red y sin FastAPI/PostgreSQL/
Docker/Node instalados — solo puede ejecutar Python puro con las
librerías que ya traía (pandas, openpyxl, pdfplumber, sqlite3). Es
perfecto para diseñar y probar el núcleo del sistema (lo que acabamos
de hacer), pero **no puede levantar un servidor de verdad, instalar
dependencias nuevas, ni mantener estado entre sesiones**.

Para las fases 1, 3 (PDF/OCR), 4-9 del roadmap de abajo — API con
FastAPI, base de datos PostgreSQL real, autenticación, frontend en
React, Docker, y que quede corriendo en tu servidor local — la
herramienta correcta es **Claude Code** (terminal, VS Code, o la app de
escritorio), donde sí hay red, git, y una sesión persistente en tu
propia máquina/servidor. Ahí seguimos exactamente donde se quedó esto:
le pego este mismo repo, y seguimos con la API.

## Roadmap completo

- [x] **Fase 0 — Motor**: fórmulas seguras, motor de reglas,
      generador de pólizas, aprendizaje supervisado, importador Excel,
      exportador Contpaqi, modelo de datos. *(hecho en este chat)*
- [ ] **Fase 1 — Fundación**: FastAPI + PostgreSQL + Alembic, login/JWT,
      organizaciones, usuarios, roles por empresa, Docker Compose.
- [ ] **Fase 2 — Catálogo**: importar catálogo real, jerarquía de
      cuentas, búsqueda, configuración de IVA por empresa desde la UI.
- [ ] **Fase 3 — Importadores**: PDF digital (pdfplumber, ya
      disponible), PDF escaneado (OCR con Tesseract), CSV, XML,
      detección automática de formato por banco.
- [ ] **Fase 4 — Motor contable en la API**: exponer formula_engine /
      rule_engine / policy_generator como endpoints, con
      persistencia real de movimientos y pólizas.
- [ ] **Fase 5 — Constructor visual de reglas**: la interfaz en React
      para armar reglas y fórmulas sin escribir texto (botones TOTAL,
      BASE, IVA, +, -, *, /).
- [ ] **Fase 6 — Aprendizaje + sugerencias IA**: conectar
      learning_engine.py a la UI, y opcionalmente una sugerencia de IA
      como último recurso antes de "sin coincidencia".
- [ ] **Fase 7 — Pólizas y exportación**: numeración por empresa,
      múltiples formatos de exportación configurables.
- [ ] **Fase 8 — Revisión y auditoría**: simulador de "qué pasaría si
      proceso esto", visor de explicación en la UI, aprobación de
      pólizas pendientes.
- [ ] **Fase 9 — Modo automático**: subir varios estados de cuenta a la
      vez y que el sistema solo pida atención en las excepciones.

## Siguiente paso sugerido

Abre este proyecto en Claude Code (terminal o VS Code) y sigue
**`docs/INSTRUCCIONES_CLAUDE_CODE.md`** — ahí está el prompt exacto para
pegar, con el detalle de qué construir en la Fase 1 (API + PostgreSQL +
autenticación + frontend React con interfaz multiusuario) reutilizando
todo el motor que ya está aquí, sin reescribirlo.

**Nota permanente**: cualquier entrega instalable/ejecutable de este
proyecto debe incluir un `.bat` para Windows que instale lo que haga
falta y levante la aplicación con un doble clic — ya quedó documentado
en las instrucciones de arranque para que Claude Code lo tenga presente
desde el primer commit.

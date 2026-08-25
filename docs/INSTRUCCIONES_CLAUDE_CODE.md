# Instrucciones de arranque para Claude Code

Este documento es el "prompt" de continuación. Ábrelo en Claude Code
(terminal, VS Code, o la app de escritorio) apuntando a esta carpeta, y
pégale el contenido de la sección **"Prompt para pegar"** de abajo.

## Qué ya existe (no reconstruir, reutilizar)

Todo el motor ya está construido y probado en `backend/app/`:

- `core/formula_engine.py` — evaluador seguro de fórmulas (`TOTAL/1.16`, etc.)
- `core/rule_engine.py` — motor de clasificación (RFC > cuenta > exacta > palabra clave)
- `core/learning_engine.py` — sugiere reglas nuevas a partir de clasificación manual
- `core/rules_repository.py` — CRUD de reglas, hoy en SQLite (migrar a PostgreSQL)
- `core/policy_generator.py` — genera y cuadra las líneas de póliza
- `importers/excel_importer.py` — 3 formatos de estado de cuenta
- `exporters/contpaqi_exporter.py` + `xls_writer.py` — exporta .xls real con
  estructura P/M1/AM/I/W2/V/AD (con CFDI y F4)
- `cfdi/cfdi_importer.py` + `cfdi_matcher.py` — importa y concilia CFDI contra movimientos
- `database/schema.sql` — modelo de datos completo multiempresa/multiusuario
- `tests/pipeline_demo.py` — demo de referencia de cómo se conectan todas las piezas

Corre `python3 backend/tests/pipeline_demo.py` para ver el flujo completo
funcionando antes de tocar nada, así entiendes cómo encajan las piezas.

## Qué hay que construir en esta fase (Fase 1: Fundación + API + UI)

### Backend

1. **FastAPI** sobre PostgreSQL (usar `database/schema.sql` como base para
   migraciones de Alembic — convertir tipos SQLite a PostgreSQL donde aplique:
   `INTEGER PRIMARY KEY AUTOINCREMENT` -> `SERIAL PRIMARY KEY`, etc.)
2. **Autenticación JWT** con login por correo/contraseña.
3. **Multiempresa real**: cada usuario ve solo las empresas a las que tiene
   acceso (tabla `usuario_empresa`), con rol por empresa (admin/editor/
   capturista/lector).
4. Endpoints REST envolviendo el motor ya construido:
   - `POST /empresas/{id}/importar-estado-cuenta` (sube Excel, usa `excel_importer.py`)
   - `POST /empresas/{id}/importar-cfdi` (sube uno o varios XML, usa `cfdi_importer.py` + `cfdi_matcher.py`)
   - `POST /empresas/{id}/movimientos/clasificar` (corre `rule_engine.py` sobre pendientes)
   - `GET/POST/PUT/DELETE /empresas/{id}/reglas` (envuelve `rules_repository.py`)
   - `POST /empresas/{id}/movimientos/{id}/clasificar-manual` (usa `learning_engine.py`
     para sugerir la regla nueva, y la guarda si el usuario confirma)
   - `POST /empresas/{id}/polizas/generar` (usa `policy_generator.py`)
   - `GET /empresas/{id}/polizas/exportar` (usa `contpaqi_exporter.py`, regresa el .xls)
   - `GET /empresas/{id}/dashboard` (resumen: % automatizado, pendientes, etc.)
5. Docker Compose: `api` (FastAPI) + `db` (PostgreSQL) + `web` (frontend).

### Frontend — interfaz bonita, multiusuario

Usar React + Tailwind. Pantallas mínimas para esta fase:

1. **Login** — correo/contraseña, selector de empresa después de entrar si el
   usuario tiene acceso a varias.
2. **Dashboard** por empresa — tarjetas de resumen (movimientos totales,
   % automatizado, pendientes de revisión), como se diseñó en la
   conversación original: tarjetas + barra de progreso + lista de últimos
   movimientos con ✓/⚠.
3. **Importar** — subir Excel de estado de cuenta y XML de CFDI (drag & drop),
   mostrar resultado de la conciliación automática.
4. **Revisión de pendientes** — lista de movimientos sin regla, con la
   sugerencia de `learning_engine.py` ya armada; el usuario confirma o ajusta
   y con un clic se guarda la regla nueva.
5. **Constructor de reglas** — formulario visual (no texto libre) para crear/
   editar reglas: condiciones (RFC, cuenta, palabras clave, tipo) + líneas de
   plantilla (cuenta, cargo/abono, fórmula) con los botones de variables
   (TOTAL, BASE, IVA, RET_IVA, RET_ISR, +, -, *, /) en vez de que el usuario
   tenga que escribir la fórmula a mano. Debe poder **agregar y quitar**
   líneas de plantilla y palabras clave libremente.
6. **Visor de póliza / explicación** — al hacer clic en una póliza generada,
   mostrar el "por qué hizo esto" (la lista `explicacion` que ya regresa
   `policy_generator.py`), y si tiene CFDI asociado, el detalle de la
   conciliación (`motivo` de `cfdi_matcher.py`).
7. **Exportar** — botón que genera y descarga el .xls.

Diseño: usar la skill `frontend-design` para tokens de diseño, tipografía y
evitar que se vea "genérico". Paleta y tono profesional-contable, no
infantil (esto lo va a usar un despacho de contadores).

### El .bat — requisito permanente

**Cada vez que se entregue algo instalable/ejecutable en este proyecto,
debe venir con un `.bat` para Windows** que:

1. Verifique si Python/Node/Docker están instalados; si no, avise con
   instrucciones claras de qué instalar (o instale lo que se pueda
   automáticamente vía winget/choco si está disponible).
2. Instale las dependencias del proyecto (`pip install -r requirements.txt`,
   `npm install`, `docker compose pull`, etc.) solo si hace falta (no
   reinstalar cada vez que se corre).
3. Levante el servidor completo (`docker compose up`, o `uvicorn` +
   `npm run dev` si se corre sin Docker).
4. Abra el navegador automáticamente en `http://localhost:<puerto>`.
5. Deje una ventana de consola visible con los logs, y un mensaje claro
   de "Orange Poliza Engine está corriendo. Cierra esta ventana para
   detenerlo."

Nombre sugerido: `iniciar_orange_poliza.bat` en la raíz del proyecto.

## Prompt para pegar en Claude Code

```
Este es el proyecto Orange Poliza Engine. Ya tiene el motor completo
construido y probado en backend/app/ (fórmulas, reglas, aprendizaje,
importación de Excel y CFDI, conciliación, exportación a .xls formato
Contpaqi). Lee database/schema.sql y corre
backend/tests/pipeline_demo.py para entender cómo encaja todo.

Ahora construye la Fase 1 completa siguiendo
docs/INSTRUCCIONES_CLAUDE_CODE.md: API con FastAPI sobre PostgreSQL
reutilizando el motor ya hecho (no reescribas formula_engine.py,
rule_engine.py, etc. — envuélvelos), autenticación JWT, multiempresa
con roles, Docker Compose, y un frontend en React + Tailwind con las
pantallas descritas ahí (dashboard, importar, revisión de pendientes,
constructor visual de reglas, visor de explicación de pólizas,
exportar). Usa la skill frontend-design para que la interfaz se vea
profesional, no genérica.

Además, siempre que entregues algo ejecutable en este proyecto, incluye
un .bat para Windows que instale dependencias (si hacen falta) y
levante todo el sistema con un doble clic, tal como se describe en la
sección "El .bat" de ese documento.
```

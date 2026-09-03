# ============================================================================
# PROPIEDAD INTELECTUAL Y LICENCIA COMERCIAL CERRADA
# ============================================================================
# Autor Legal y Titular de Derechos: JAVIER ILLAN GONZALEZ
# Organización: ORANGE CREW
# Contacto: ILLANJAVIER9@GMAIL.COM
#
# ADVERTENCIA LEGAL (MÉXICO Y GLOBAL):
# Este código fuente y su arquitectura son propiedad intelectual exclusiva de
# JAVIER ILLAN GONZALEZ. Queda estrictamente prohibida su reproducción,
# distribución, modificación, ingeniería inversa, copia o uso comercial sin la
# autorización expresa y por escrito del autor. Obra protegida conforme a la
# Ley Federal del Derecho de Autor y tratados internacionales aplicables.
# ============================================================================
import json
from datetime import datetime
from flask import Blueprint, request, jsonify

# Importamos el motor (se asume que sys.path ya incluye backend/app/core)
from rule_engine import encontrar_regla, Regla
from policy_generator import generar_poliza, LineaPlantilla

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

@api_bp.route("/engine/classify", methods=["POST"])
def classify_movements():
    """
    Endpoint para procesar movimientos de manera volatil (stateless).
    Recibe un JSON con:
      - movimientos: lista de dicts (fecha, descripcion, tipo, total, rfc_contraparte, etc.)
      - reglas: lista de dicts con la configuracion de las reglas
      - plantillas: lista de dicts con la configuracion de los asientos
      - tasa_iva: float opcional (default 0.16)
    Retorna:
      - resultados: lista de polizas generadas o razones por las que fallo.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Payload JSON requerido"}), 400
        
    movimientos_crudos = data.get("movimientos", [])
    reglas_crudas = data.get("reglas", [])
    plantillas_crudas = data.get("plantillas", [])
    tasa_iva = float(data.get("tasa_iva", 0.16))
    
    # 1. Parsear reglas
    reglas_parseadas = []
    for r in reglas_crudas:
        regla = Regla(
            id=r.get("id"),
            nombre=r.get("nombre", ""),
            prioridad=r.get("prioridad", 50),
            condicion_tipo=r.get("condicion_tipo", "ingreso"),
            condicion_rfc=r.get("condicion_rfc"),
            condicion_cuenta_bancaria=r.get("condicion_cuenta_bancaria"),
            condicion_descripcion_exacta=r.get("condicion_descripcion_exacta"),
            condicion_palabras_clave=r.get("condicion_palabras_clave", []),
            usa_similitud_difusa=r.get("usa_similitud_difusa", False)
        )
        reglas_parseadas.append(regla)
        
    # 2. Parsear plantillas
    plantillas_dict = {}
    for p in plantillas_crudas:
        
        asientos_obj = []
        for a in p.get("asientos", []):
            asientos_obj.append(LineaPlantilla(
                cuenta=a.get("cuenta"),
                naturaleza=a.get("naturaleza"),
                formula=a.get("formula"),
                descripcion_linea=a.get("descripcion_linea")
            ))
        plantillas_dict[p.get("regla_id")] = {
            "tipo_poliza": p.get("tipo_poliza", "diario"),
            "concepto_poliza": p.get("concepto_poliza", "Poliza automatica"),
            "asientos": asientos_obj
        }

        
    resultados = []
    
    # 3. Procesar cada movimiento
    for m in movimientos_crudos:
        # Asegurar formato del movimiento
        if isinstance(m.get("fecha"), str):
            try:
                # Intentar parsear ISO format
                m["fecha"] = datetime.fromisoformat(m["fecha"].replace("Z", "+00:00"))
            except ValueError:
                pass
                
        # Asegurar valores por defecto requeridos por generar_poliza
        m.setdefault("tiene_iva", True)
        m.setdefault("ret_iva", 0.0)
        m.setdefault("ret_isr", 0.0)
        m.setdefault("tipo_cambio", 1.0)
        
        match = encontrar_regla(m, reglas_parseadas)
        
        res = {
            "movimiento_original": m,
            "match": {
                "encontrado": match.regla is not None,
                "regla_id": match.regla.id if match.regla else None,
                "regla_nombre": match.regla.nombre if match.regla else None,
                "confianza": match.confianza,
                "motivo": match.motivo
            }
        }
        
        if match.regla is not None:
            plantilla = plantillas_dict.get(match.regla.id)
            if plantilla:
                poliza_res = generar_poliza(
                    movimiento=m, 
                    plantilla=plantilla["asientos"], 
                    nombre_regla=match.regla.nombre, 
                    motivo_match=match.motivo,
                    tasa_iva=empresa['tasa_iva'], tasa_ret_iva=empresa.get('tasa_retencion_iva', 0.0), tasa_ret_isr=empresa.get('tasa_retencion_isr', 0.0)
                )
                res["poliza"] = {
                    "cuadrada": poliza_res.cuadrada,
                    "encabezado": {
                        "fecha": m["fecha"].isoformat() if hasattr(m["fecha"], 'isoformat') else str(m["fecha"]),
                        "tipo": plantilla["tipo_poliza"],
                        "concepto": plantilla["concepto_poliza"],
                    },
                    "asientos": [
                        {
                            "cuenta": a.cuenta,
                            "tipo_movimiento": a.tipo_movimiento,
                            "importe": a.importe,
                            "referencia": a.referencia,
                            "concepto": a.concepto
                        } for a in poliza_res.asientos
                    ]
                }
            else:
                res["poliza"] = None
                res["error"] = "Plantilla no encontrada para la regla"
                
        resultados.append(res)
        
    return jsonify({
        "status": "ok",
        "procesados": len(resultados),
        "resultados": resultados
    })


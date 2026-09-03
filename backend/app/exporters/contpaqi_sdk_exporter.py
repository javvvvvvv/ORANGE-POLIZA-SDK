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
import urllib.request
from datetime import datetime

def exportar_polizas_via_sdk(movimientos_poliza, empresa_nombre="MiEmpresa"):
    """
    Exporta las pÃ³lizas llamando a la API HTTP de ContpaqiBridge (C#).
    """
    data = {
        "empresa": empresa_nombre,
        "polizas": []
    }
    
    for mov in movimientos_poliza:
        tipo_str = str(mov.tipo).lower()
        tipo_int = 3 # diario por defecto
        if "ingreso" in tipo_str: tipo_int = 1
        elif "egreso" in tipo_str: tipo_int = 2
        
        p = {
            "numero": str(mov.numero_poliza),
            "tipo": tipo_int,
            "fecha": mov.fecha.strftime("%Y-%m-%d"),
            "concepto": mov.descripcion,
            "diario": 0,
            "movimientos": []
        }
        for linea in mov.lineas:
            m = {
                "cuenta": str(linea.cuenta).replace("-", ""),
                "tipoMovto": 0 if linea.naturaleza.lower() == "cargo" else 1,
                "importe": float(round(linea.importe, 2)),
                "concepto": str(linea.descripcion) if linea.descripcion else "",
                "referencia": str(getattr(mov, "numero_factura", "")) if getattr(mov, "numero_factura", "") else "",
                "diario": 0
            }
            p["movimientos"].append(m)
        data["polizas"].append(p)

    json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
    
    # URL del bridge en C# que corre en Windows host. host.docker.internal resuelve a la PC host desde dentro de Docker.
    url = "http://host.docker.internal:5005/"
    
    req = urllib.request.Request(
        url, 
        data=json_data, 
        headers={
            'Content-Type': 'application/json',
            'Host': 'localhost:5005'
        }, 
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            return {
                "exito": res_json.get("exito", False),
                "mensaje": res_json.get("mensaje", ""),
                "polizas_procesadas": len(movimientos_poliza)
            }
    except Exception as e:
        print(f"Error al conectar con ContpaqiBridge en {url}: {e}")
        return {
            "exito": False,
            "mensaje": f"No se pudo conectar al puente (AsegÃºrate de tener corriendo iniciar_puente_contpaqi.bat): {e}",
            "polizas_procesadas": 0
        }


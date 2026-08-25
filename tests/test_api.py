import unittest
import json
import sys
import os

# Asegurar imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "webapp")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "app", "core")))

from webapp.app import app
from rule_engine import Regla
from policy_generator import PlantillaPoliza

class TestMotorContableAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_api_classify_sin_match(self):
        payload = {
            "movimientos": [
                {"fecha": "2026-08-20T10:00:00", "descripcion": "COMPRA DESCONOCIDA", "total": 500, "tipo": "egreso"}
            ],
            "reglas": [],
            "plantillas": []
        }
        res = self.app.post("/api/v1/engine/classify", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["procesados"], 1)
        self.assertFalse(data["resultados"][0]["match"]["encontrado"])
        self.assertIsNone(data["resultados"][0]["poliza"])

    def test_api_classify_con_match(self):
        payload = {
            "movimientos": [
                {"fecha": "2026-08-20T10:00:00", "descripcion": "PAGO CFE", "total": 1160, "tipo": "egreso"}
            ],
            "reglas": [
                {
                    "id": 1,
                    "nombre": "Regla CFE",
                    "condicion_tipo": "egreso",
                    "condicion_palabras_clave": ["CFE", "LUZ"]
                }
            ],
            "plantillas": [
                {
                    "id": 1,
                    "regla_id": 1,
                    "tipo_poliza": "egreso",
                    "concepto_poliza": "Pago de luz",
                    "asientos": [
                        {"cuenta": "600-01-000", "tipo_movimiento": "cargo", "concepto": "Luz", "importe": "{subtotal}"},
                        {"cuenta": "118-01-000", "tipo_movimiento": "cargo", "concepto": "IVA Luz", "importe": "{iva}"},
                        {"cuenta": "100-01-000", "tipo_movimiento": "abono", "concepto": "Pago banco", "importe": "{total}"}
                    ]
                }
            ]
        }
        res = self.app.post("/api/v1/engine/classify", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["procesados"], 1)
        
        match = data["resultados"][0]["match"]
        self.assertTrue(match["encontrado"])
        self.assertEqual(match["regla_id"], 1)
        
        poliza = data["resultados"][0]["poliza"]
        self.assertIsNotNone(poliza)
        self.assertTrue(poliza["cuadrada"])
        
        # Validar IVA (1160 / 1.16 = 1000 subtotal, 160 iva)
        asientos = poliza["asientos"]
        self.assertEqual(len(asientos), 3)
        self.assertEqual(asientos[0]["importe"], 1000.0)
        self.assertEqual(asientos[1]["importe"], 160.0)
        self.assertEqual(asientos[2]["importe"], 1160.0)

if __name__ == "__main__":
    unittest.main()

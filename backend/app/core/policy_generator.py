# -*- coding: utf-8 -*-
"""
Generador de pólizas para Orange Poliza Engine.

Toma:
  - un movimiento normalizado (fecha, descripción, total, tipo, etc.)
  - una PLANTILLA de movimientos contables (lista de líneas: cuenta,
    cargo/abono, fórmula) que viene de la regla que hizo match
      (ver rule_engine.encontrar_regla)

y genera:
  - las líneas de la póliza (cargos y abonos ya calculados)
  - una validación de que cuadra (suma cargos == suma abonos)
  - una explicación paso a paso para el visor de auditoría
"""

from dataclasses import dataclass, field
from typing import Optional

try:
    from .formula_engine import evaluar_formula, construir_variables, FormulaError
except ImportError:  # se ejecuta como script suelto (ej. demo_end_to_end.py)
    from formula_engine import evaluar_formula, construir_variables, FormulaError


@dataclass
class LineaPlantilla:
    """Una línea de la plantilla contable de una regla, tal como se
    guarda en la tabla `plantilla_movimientos`."""
    cuenta: str
    naturaleza: str  # 'cargo' | 'abono'
    formula: str      # ej. "TOTAL / 1.16", "IVA", "TOTAL"
    descripcion_linea: Optional[str] = None  # si es None, se usa la descripción del movimiento


@dataclass
class LineaPoliza:
    """Una línea ya calculada, lista para exportar."""
    cuenta: str
    naturaleza: str
    importe: float
    descripcion: str
    formula_usada: str


@dataclass
class ResultadoPoliza:
    lineas: list = field(default_factory=list)
    cuadrada: bool = False
    diferencia: float = 0.0
    explicacion: list = field(default_factory=list)  # lista de strings, paso a paso
    errores: list = field(default_factory=list)


def generar_poliza(
    movimiento: dict,
    plantilla: list[LineaPlantilla],
    nombre_regla: str,
    motivo_match: str,
    tasa_iva: float = 0.16,
    tasa_ret_iva: float = 0.0,
    tasa_ret_isr: float = 0.0,
) -> ResultadoPoliza:
    """
    Genera las líneas de póliza para un movimiento, aplicando la
    plantilla de la regla que hizo match.

    :param movimiento: dict con al menos 'total', 'descripcion', 'tipo',
        'tiene_iva', 'ret_iva', 'ret_isr', 'tipo_cambio'
    :param plantilla: lista de LineaPlantilla en el orden en que deben
        aparecer en la póliza
    :param nombre_regla: nombre de la regla que se está aplicando (para
        la explicación)
    :param motivo_match: el `motivo` que regresó rule_engine.encontrar_regla
    """
    resultado = ResultadoPoliza()

    variables = construir_variables(
        total=movimiento["total"],
        tasa_iva=tasa_iva,
        tiene_iva=movimiento.get("tiene_iva", False),
        ret_iva=movimiento.get("ret_iva", 0.0),
        ret_isr=movimiento.get("ret_isr", 0.0),
        tipo_cambio=movimiento.get("tipo_cambio", 1.0),
        tasa_ret_iva=tasa_ret_iva,
        tasa_ret_isr=tasa_ret_isr,
    )

    resultado.explicacion.append(
        f"Regla aplicada: '{nombre_regla}'. {motivo_match}"
    )
    resultado.explicacion.append(
        "Variables calculadas del movimiento: "
        + ", ".join(f"{k}={v}" for k, v in variables.items())
    )

    suma_cargos = 0.0
    suma_abonos = 0.0

    for linea_plantilla in plantilla:
        try:
            importe = evaluar_formula(linea_plantilla.formula, variables)
        except FormulaError as e:
            resultado.errores.append(
                f"Error en la línea de cuenta {linea_plantilla.cuenta}: {e}"
            )
            continue

        if importe < 0:
            resultado.errores.append(
                f"La fórmula '{linea_plantilla.formula}' para la cuenta "
                f"{linea_plantilla.cuenta} dio un importe negativo ({importe}). "
                f"Revisa la fórmula."
            )
            continue

        descripcion_linea = (
            linea_plantilla.descripcion_linea or movimiento.get("descripcion", "")
        )

        linea = LineaPoliza(
            cuenta=linea_plantilla.cuenta,
            naturaleza=linea_plantilla.naturaleza,
            importe=importe,
            descripcion=descripcion_linea,
            formula_usada=linea_plantilla.formula,
        )
        resultado.lineas.append(linea)

        if linea_plantilla.naturaleza == "cargo":
            suma_cargos += importe
        else:
            suma_abonos += importe

        resultado.explicacion.append(
            f"  {linea_plantilla.naturaleza.upper():6s}  cuenta {linea_plantilla.cuenta:12s} "
            f"= {linea_plantilla.formula}  ->  ${importe:,.2f}"
        )

    suma_cargos = round(suma_cargos, 2)
    suma_abonos = round(suma_abonos, 2)
    diferencia = round(suma_cargos - suma_abonos, 2)

    resultado.diferencia = diferencia
    resultado.cuadrada = (abs(diferencia) < 0.01) and not resultado.errores

    if resultado.cuadrada:
        resultado.explicacion.append(
            f"✓ Póliza cuadrada. Cargos: ${suma_cargos:,.2f}  "
            f"Abonos: ${suma_abonos:,.2f}"
        )
    else:
        if not resultado.errores:
            resultado.explicacion.append(
                f"✗ Póliza NO cuadrada. Cargos: ${suma_cargos:,.2f}  "
                f"Abonos: ${suma_abonos:,.2f}  Diferencia: ${diferencia:,.2f}"
            )

    return resultado

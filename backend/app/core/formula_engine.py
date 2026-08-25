# -*- coding: utf-8 -*-
"""
Motor de fórmulas para Orange Poliza Engine.

Permite que cada empresa defina, por regla, cómo se calcula el importe
de cada movimiento de la póliza a partir de variables conocidas del
movimiento original (TOTAL, TASA_IVA, RET_IVA, etc.), usando una
expresión de texto tipo:

    "TOTAL / 1.16"
    "TOTAL * 0.16"
    "BASE - RET_IVA"
    "TOTAL - (TOTAL / (1 + TASA_IVA))"

No usamos eval() directo sobre el texto del usuario porque eso permitiría
ejecutar cualquier código Python. En vez de eso, parseamos la expresión
con el módulo `ast` y solo permitimos un subconjunto muy limitado de
nodos (números, nombres de variables conocidas, +, -, *, /, paréntesis,
signo negativo y la función round()). Cualquier otra cosa (imports,
llamadas a funciones no permitidas, atributos, etc.) se rechaza.
"""

import ast
import operator


class FormulaError(Exception):
    """Se lanza cuando una fórmula es inválida o usa algo no permitido."""
    pass


# Operadores aritméticos permitidos
_OPERADORES_BINARIOS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

_OPERADORES_UNARIOS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Funciones permitidas dentro de una fórmula
_FUNCIONES_PERMITIDAS = {
    "round": round,
    "abs": abs,
    "min": min,
    "max": max,
}

# Variables que el motor de reglas expone a cada fórmula.
# Cada movimiento normalizado se traduce a este diccionario antes de evaluar.
VARIABLES_DISPONIBLES = [
    "TOTAL",       # importe total del movimiento (siempre positivo)
    "TASA_IVA",    # ej. 0.16
    "BASE",        # TOTAL / (1 + TASA_IVA), calculado automáticamente si hay IVA
    "IVA",         # TOTAL - BASE, calculado automáticamente si hay IVA
    "RET_IVA",     # retención de IVA capturada manualmente (0 si no aplica)
    "RET_ISR",     # retención de ISR capturada manualmente (0 si no aplica)
    "TIPO_CAMBIO", # tipo de cambio si el movimiento es en dólares (1.0 si es en pesos)
]


def evaluar_formula(expresion: str, variables: dict) -> float:
    """
    Evalúa una fórmula de texto de forma segura y regresa el resultado
    redondeado a 2 decimales.

    :param expresion: texto de la fórmula, ej. "TOTAL / 1.16"
    :param variables: diccionario con los valores actuales del movimiento,
                       ej. {"TOTAL": 11600, "TASA_IVA": 0.16, ...}
    :raises FormulaError: si la fórmula no es válida o usa algo no permitido
    """
    if not expresion or not expresion.strip():
        raise FormulaError("La fórmula está vacía.")

    try:
        arbol = ast.parse(expresion, mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"Fórmula con error de sintaxis: {expresion!r} ({e})")

    resultado = _evaluar_nodo(arbol.body, variables)

    if not isinstance(resultado, (int, float)):
        raise FormulaError(f"La fórmula '{expresion}' no regresó un número.")

    return round(float(resultado), 2)


def _evaluar_nodo(nodo, variables: dict):
    # Número literal: 1.16, 100, etc.
    if isinstance(nodo, ast.Constant):
        if isinstance(nodo.value, (int, float)):
            return nodo.value
        raise FormulaError(f"Valor no permitido en la fórmula: {nodo.value!r}")

    # Nombre de variable: TOTAL, BASE, IVA, etc.
    if isinstance(nodo, ast.Name):
        nombre = nodo.id
        if nombre not in variables:
            disponibles = ", ".join(sorted(variables.keys()))
            raise FormulaError(
                f"La variable '{nombre}' no está disponible. "
                f"Variables disponibles: {disponibles}"
            )
        return variables[nombre]

    # Operación binaria: a + b, a - b, a * b, a / b
    if isinstance(nodo, ast.BinOp):
        tipo_op = type(nodo.op)
        if tipo_op not in _OPERADORES_BINARIOS:
            raise FormulaError(f"Operador no permitido: {tipo_op.__name__}")
        izquierda = _evaluar_nodo(nodo.left, variables)
        derecha = _evaluar_nodo(nodo.right, variables)
        if tipo_op is ast.Div and derecha == 0:
            raise FormulaError("División entre cero en la fórmula.")
        return _OPERADORES_BINARIOS[tipo_op](izquierda, derecha)

    # Operación unaria: -TOTAL, +TOTAL
    if isinstance(nodo, ast.UnaryOp):
        tipo_op = type(nodo.op)
        if tipo_op not in _OPERADORES_UNARIOS:
            raise FormulaError(f"Operador unario no permitido: {tipo_op.__name__}")
        valor = _evaluar_nodo(nodo.operand, variables)
        return _OPERADORES_UNARIOS[tipo_op](valor)

    # Paréntesis ya vienen resueltos por el parser como parte del árbol

    # Llamada a función: round(TOTAL / 1.16, 2)
    if isinstance(nodo, ast.Call):
        if not isinstance(nodo.func, ast.Name):
            raise FormulaError("Solo se permiten llamadas a funciones simples.")
        nombre_funcion = nodo.func.id
        if nombre_funcion not in _FUNCIONES_PERMITIDAS:
            raise FormulaError(f"Función no permitida: {nombre_funcion}()")
        argumentos = [_evaluar_nodo(a, variables) for a in nodo.args]
        return _FUNCIONES_PERMITIDAS[nombre_funcion](*argumentos)

    raise FormulaError(f"Elemento no permitido en la fórmula: {type(nodo).__name__}")


def construir_variables(
    total: float,
    tasa_iva: float = 0.16,
    tiene_iva: bool = True,
    ret_iva: float = 0.0,
    ret_isr: float = 0.0,
    tipo_cambio: float = 1.0,
    tasa_ret_iva: float = 0.0,
    tasa_ret_isr: float = 0.0,
) -> dict:
    """
    Construye el diccionario de variables que se le pasa a evaluar_formula(),
    a partir de los datos de un movimiento ya normalizado.
    """
    total = round(float(total), 2)

    if tiene_iva:
        divisor = 1.0 + tasa_iva - tasa_ret_iva - tasa_ret_isr
        base = round(total / divisor, 2)
        iva = round(base * tasa_iva, 2)
        if ret_iva == 0.0 and tasa_ret_iva > 0:
            ret_iva = round(base * tasa_ret_iva, 2)
        if ret_isr == 0.0 and tasa_ret_isr > 0:
            ret_isr = round(base * tasa_ret_isr, 2)
    else:
        base = total
        iva = 0.0

    return {
        "TOTAL": total,
        "TASA_IVA": tasa_iva,
        "BASE": base,
        "IVA": iva,
        "RET_IVA": round(float(ret_iva), 2),
        "RET_ISR": round(float(ret_isr), 2),
        "TIPO_CAMBIO": tipo_cambio,
    }


def validar_formula(expresion: str) -> bool:
    """
    Valida que una fórmula sea sintácticamente correcta y solo use
    variables conocidas, sin necesidad de tener valores reales todavía.
    Útil para validar en la interfaz mientras el usuario construye una regla.
    """
    variables_dummy = {nombre: 1.0 for nombre in VARIABLES_DISPONIBLES}
    try:
        evaluar_formula(expresion, variables_dummy)
        return True
    except FormulaError:
        return False

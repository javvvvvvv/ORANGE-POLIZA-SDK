# -*- coding: utf-8 -*-
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
import os
import datetime
from db import get_connection

# Si no hay keys de Stripe, usaremos un mock interno
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')

def get_checkout_url(org_id, success_url, cancel_url):
    '''
    Retorna la URL a la que el usuario debe ser redirigido para pagar.
    Si Stripe esta configurado, llama a Stripe API.
    Si no, devuelve una URL local al simulador de pagos.
    '''
    if STRIPE_SECRET_KEY:
        # Aqu iria la integracin real con stripe.Checkout.Session.create
        # Por ahora regresamos simulador si no est completamente implementado
        pass
    
    # Mock fallback
    return f"/billing/mock-checkout?org_id={org_id}"

def reactivar_suscripcion(org_id, dias=30):
    '''Reactivar la suscripcion de la organizacion en la BD (ej. despues de un webhook de pago)'''
    con = get_connection()
    nueva_fecha = (datetime.datetime.now() + datetime.timedelta(days=dias)).isoformat()
    con.execute("UPDATE organizaciones SET estado_suscripcion = 'activa', fecha_vencimiento = ? WHERE id = ?", (nueva_fecha, org_id))
    con.commit()
    con.close()


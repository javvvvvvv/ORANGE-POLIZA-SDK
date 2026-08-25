import os
import stripe
from flask import Blueprint, redirect, request, jsonify, session, flash, url_for, g
from auth import login_required
from db import get_connection

pagos_bp = Blueprint('pagos', __name__)

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_mock_secret')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_mock')
PRICE_ID = os.environ.get('STRIPE_PRICE_ID', 'price_1XXXXXX') 

@pagos_bp.route('/pagos/checkout', methods=['GET', 'POST'])
@login_required
def crear_checkout():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return redirect(url_for('auth.login'))
        
    con = get_connection()
    usr = con.execute('SELECT organizacion_id, rol_global FROM usuarios WHERE id = ?', (usuario_id,)).fetchone()
    con.close()
    
    if not usr or usr['rol_global'] not in ('superadmin', 'admin', 'gerente'):
        flash('Solo los administradores pueden gestionar la suscripción.', 'error')
        return redirect(url_for('empresas.selector_empresas'))
        
    org_id = usr['organizacion_id']
    domain_url = request.host_url.rstrip('/')
    
    if stripe.api_key == "sk_test_mock_secret":
        # Modo opcional/simulado: Otorga vigencia instantáneamente sin llamar a Stripe
        _acreditar_pago(org_id)
        flash('¡Modo de prueba! Se ha renovado tu suscripción por 30 días automáticamente.', 'success')
        return redirect(url_for('empresas.selector_empresas'))
        
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': PRICE_ID,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=domain_url + url_for('pagos.exito') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=domain_url + url_for('empresas.selector_empresas'),
            client_reference_id=str(org_id),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Error al conectar con la pasarela de pagos: {str(e)}', 'error')
        return redirect(url_for('empresas.selector_empresas'))

@pagos_bp.route('/pagos/exito')
@login_required
def exito():
    flash('¡Pago completado! Tu suscripción ha sido procesada correctamente.', 'success')
    return redirect(url_for('empresas.selector_empresas'))

@pagos_bp.route('/pagos/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    if stripe.api_key == "sk_test_mock_secret":
        # Modo opcional/simulado: Otorga vigencia instantáneamente sin llamar a Stripe
        _acreditar_pago(org_id)
        flash('¡Modo de prueba! Se ha renovado tu suscripción por 30 días automáticamente.', 'success')
        return redirect(url_for('empresas.selector_empresas'))
        
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return 'Error', 400
        
    if event['type'] == 'checkout.session.completed':
        session_obj = event['data']['object']
        org_id = session_obj.get('client_reference_id')
        
        if org_id:
            _acreditar_pago(int(org_id))
            
    return jsonify(success=True), 200

def _acreditar_pago(org_id):
    con = get_connection()
    if stripe.api_key == "sk_test_mock_secret":
        # Modo opcional/simulado: Otorga vigencia instantáneamente sin llamar a Stripe
        _acreditar_pago(org_id)
        flash('¡Modo de prueba! Se ha renovado tu suscripción por 30 días automáticamente.', 'success')
        return redirect(url_for('empresas.selector_empresas'))
        
    try:
        con.execute(
            '''UPDATE organizaciones 
               SET estado_suscripcion = 'activa', 
                   fecha_vencimiento_suscripcion = 
                     CASE 
                       WHEN fecha_vencimiento_suscripcion > NOW() THEN fecha_vencimiento_suscripcion + INTERVAL '30 days'
                       ELSE NOW() + INTERVAL '30 days'
                     END
               WHERE id = ?''', 
            (org_id,)
        )
        con.commit()
    finally:
        con.close()

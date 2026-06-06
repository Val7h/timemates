"""
Rotas de cobrança e subscriptions (Stripe integration).
"""

import os
import stripe
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db, User, Subscription
from auth import get_current_user_required
from stripe_service import (
    create_checkout_session,
    cancel_subscription,
    get_user_subscription,
    process_webhook_event,
    STRIPE_WEBHOOK_SECRET
)

router = APIRouter(prefix="/api/billing", tags=["billing"])

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')


@router.post("/create-checkout")
async def create_checkout(
    request: Request,
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Cria uma sessão de checkout do Stripe para o usuário comprar premium.

    Returns:
        dict com checkout_url
    """
    # Verifica se já tem subscription ativa
    existing_sub = db.query(Subscription).filter_by(user_id=user.id).first()
    if existing_sub and existing_sub.status == 'active':
        raise HTTPException(
            status_code=400,
            detail="Usuário já possui uma subscription ativa"
        )

    try:
        result = create_checkout_session(user)
        return {
            'checkout_url': result['checkout_url'],
            'session_id': result['session_id']
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscription")
async def get_subscription(
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Retorna os dados da subscription do usuário.

    Returns:
        dict com plan, status, datas de período, etc.
    """
    sub_data = get_user_subscription(db, user.id)
    return sub_data


@router.post("/cancel")
async def cancel_user_subscription(
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Cancela a subscription do usuário.

    Returns:
        dict com status do cancelamento
    """
    try:
        result = cancel_subscription(db, user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook do Stripe para processar eventos de pagamento e subscription.

    Deve ser chamado pela Stripe com a signature correta.
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    if not sig_header or not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=400, detail="Missing signature header or webhook secret")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")

    # Processa o evento
    result = process_webhook_event(db, event)

    return {
        'status': 'received',
        'event_id': event.get('id'),
        'processing_result': result
    }


@router.get("/public-key")
async def get_public_key():
    """
    Retorna a chave pública do Stripe para o frontend usar.
    """
    public_key = os.getenv('STRIPE_PUBLIC_KEY')
    if not public_key:
        raise HTTPException(
            status_code=500,
            detail="STRIPE_PUBLIC_KEY não configurada"
        )
    return {'public_key': public_key}


@router.post("/portal")
async def create_billing_portal(
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Cria um link para o portal de gerenciamento de billing do Stripe.

    Permite ao usuário gerenciar payment method, invoices, etc.
    """
    sub = db.query(Subscription).filter_by(user_id=user.id).first()

    if not sub:
        raise HTTPException(
            status_code=404,
            detail="Usuário não possui subscription"
        )

    try:
        session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=os.getenv('BASE_URL', 'http://localhost:8765') + '/account/billing'
        )
        return {'portal_url': session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

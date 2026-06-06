"""
Serviço de integração com Stripe para pagamentos de subscriptions.
"""

import os
import stripe
from datetime import datetime
from sqlalchemy.orm import Session
from database import Subscription, User

# Configuração do Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Mapeamento de produtos/preços do Stripe
PRODUCTS = {
    'premium_monthly': os.getenv('STRIPE_PRICE_PREMIUM_MONTHLY', 'price_1234567890abcdef')
}

# URLs de callback
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8765')
SUCCESS_URL = f"{BASE_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
CANCEL_URL = f"{BASE_URL}/billing/cancel"


def create_checkout_session(user: User) -> dict:
    """
    Cria uma sessão de checkout Stripe para o usuário.

    Args:
        user: Objeto User do banco de dados

    Returns:
        dict com url do checkout
    """
    try:
        session = stripe.checkout.Session.create(
            customer_email=user.email,
            line_items=[
                {
                    'price': PRODUCTS['premium_monthly'],
                    'quantity': 1,
                }
            ],
            mode='subscription',
            success_url=SUCCESS_URL,
            cancel_url=CANCEL_URL,
            metadata={
                'user_id': str(user.id),
            }
        )
        return {
            'checkout_url': session.url,
            'session_id': session.id
        }
    except stripe.error.StripeError as e:
        raise Exception(f"Erro ao criar checkout: {str(e)}")


def create_or_update_subscription(
    db: Session,
    user_id: int,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    status: str,
    current_period_start: datetime,
    current_period_end: datetime
) -> Subscription:
    """
    Cria ou atualiza uma subscription no banco de dados.

    Args:
        db: Session do SQLAlchemy
        user_id: ID do usuário
        stripe_customer_id: ID do cliente no Stripe
        stripe_subscription_id: ID da subscription no Stripe
        status: Status da subscription
        current_period_start: Início do período de cobrança
        current_period_end: Fim do período de cobrança

    Returns:
        Objeto Subscription criado ou atualizado
    """
    sub = db.query(Subscription).filter_by(user_id=user_id).first()

    if sub:
        # Atualizar subscription existente
        sub.stripe_customer_id = stripe_customer_id
        sub.stripe_subscription_id = stripe_subscription_id
        sub.status = status
        sub.current_period_start = current_period_start
        sub.current_period_end = current_period_end
        sub.updated_at = datetime.utcnow()
    else:
        # Criar nova subscription
        sub = Subscription(
            user_id=user_id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            plan='premium',
            status=status,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
        )
        db.add(sub)

    db.commit()
    db.refresh(sub)
    return sub


def cancel_subscription(db: Session, user_id: int) -> dict:
    """
    Cancela uma subscription do usuário.

    Args:
        db: Session do SQLAlchemy
        user_id: ID do usuário

    Returns:
        dict com status do cancelamento
    """
    sub = db.query(Subscription).filter_by(user_id=user_id).first()

    if not sub:
        raise Exception("Subscription não encontrada")

    try:
        # Cancela no Stripe
        stripe.Subscription.delete(sub.stripe_subscription_id)

        # Atualiza no banco
        sub.status = 'canceled'
        sub.cancel_at_period_end = False
        sub.updated_at = datetime.utcnow()
        db.commit()

        return {
            'status': 'canceled',
            'message': 'Subscription cancelada com sucesso'
        }
    except stripe.error.StripeError as e:
        raise Exception(f"Erro ao cancelar subscription: {str(e)}")


def get_user_subscription(db: Session, user_id: int) -> dict:
    """
    Retorna os dados da subscription do usuário.

    Args:
        db: Session do SQLAlchemy
        user_id: ID do usuário

    Returns:
        dict com dados da subscription ou None
    """
    sub = db.query(Subscription).filter_by(user_id=user_id).first()

    if not sub:
        return {
            'plan': None,
            'status': None,
            'current_period_end': None,
            'is_active': False
        }

    return {
        'plan': sub.plan,
        'status': sub.status,
        'current_period_start': sub.current_period_start.isoformat() if sub.current_period_start else None,
        'current_period_end': sub.current_period_end.isoformat() if sub.current_period_end else None,
        'cancel_at_period_end': sub.cancel_at_period_end,
        'is_active': sub.status == 'active'
    }


def process_webhook_event(db: Session, event: dict) -> dict:
    """
    Processa eventos de webhook do Stripe.

    Args:
        db: Session do SQLAlchemy
        event: Evento enviado pelo Stripe

    Returns:
        dict com resultado do processamento
    """
    event_type = event['type']

    if event_type == 'customer.subscription.created':
        return _handle_subscription_created(db, event['data']['object'])

    elif event_type == 'customer.subscription.updated':
        return _handle_subscription_updated(db, event['data']['object'])

    elif event_type == 'customer.subscription.deleted':
        return _handle_subscription_deleted(db, event['data']['object'])

    elif event_type == 'invoice.payment_succeeded':
        return _handle_invoice_payment_succeeded(db, event['data']['object'])

    elif event_type == 'invoice.payment_failed':
        return _handle_invoice_payment_failed(db, event['data']['object'])

    return {'status': 'ignored', 'event_type': event_type}


def _handle_subscription_created(db: Session, subscription: dict) -> dict:
    """Handles customer.subscription.created event."""
    user_id = int(subscription['metadata'].get('user_id', 0))

    if user_id:
        create_or_update_subscription(
            db=db,
            user_id=user_id,
            stripe_customer_id=subscription['customer'],
            stripe_subscription_id=subscription['id'],
            status=subscription['status'],
            current_period_start=datetime.fromtimestamp(subscription['current_period_start']),
            current_period_end=datetime.fromtimestamp(subscription['current_period_end'])
        )
        return {'status': 'processed', 'event': 'subscription.created', 'user_id': user_id}

    return {'status': 'skipped', 'event': 'subscription.created', 'reason': 'user_id not found'}


def _handle_subscription_updated(db: Session, subscription: dict) -> dict:
    """Handles customer.subscription.updated event."""
    user_id = int(subscription['metadata'].get('user_id', 0))

    if user_id:
        create_or_update_subscription(
            db=db,
            user_id=user_id,
            stripe_customer_id=subscription['customer'],
            stripe_subscription_id=subscription['id'],
            status=subscription['status'],
            current_period_start=datetime.fromtimestamp(subscription['current_period_start']),
            current_period_end=datetime.fromtimestamp(subscription['current_period_end'])
        )
        return {'status': 'processed', 'event': 'subscription.updated', 'user_id': user_id}

    return {'status': 'skipped', 'event': 'subscription.updated', 'reason': 'user_id not found'}


def _handle_subscription_deleted(db: Session, subscription: dict) -> dict:
    """Handles customer.subscription.deleted event."""
    customer_id = subscription['customer']
    sub = db.query(Subscription).filter_by(stripe_customer_id=customer_id).first()

    if sub:
        sub.status = 'canceled'
        sub.updated_at = datetime.utcnow()
        db.commit()
        return {'status': 'processed', 'event': 'subscription.deleted', 'user_id': sub.user_id}

    return {'status': 'skipped', 'event': 'subscription.deleted', 'reason': 'subscription not found'}


def _handle_invoice_payment_succeeded(db: Session, invoice: dict) -> dict:
    """Handles invoice.payment_succeeded event."""
    customer_id = invoice['customer']
    sub = db.query(Subscription).filter_by(stripe_customer_id=customer_id).first()

    if sub:
        sub.status = 'active'
        sub.updated_at = datetime.utcnow()
        db.commit()
        return {'status': 'processed', 'event': 'invoice.payment_succeeded', 'user_id': sub.user_id}

    return {'status': 'skipped', 'event': 'invoice.payment_succeeded', 'reason': 'subscription not found'}


def _handle_invoice_payment_failed(db: Session, invoice: dict) -> dict:
    """Handles invoice.payment_failed event."""
    customer_id = invoice['customer']
    sub = db.query(Subscription).filter_by(stripe_customer_id=customer_id).first()

    if sub:
        sub.status = 'past_due'
        sub.updated_at = datetime.utcnow()
        db.commit()
        return {'status': 'processed', 'event': 'invoice.payment_failed', 'user_id': sub.user_id}

    return {'status': 'skipped', 'event': 'invoice.payment_failed', 'reason': 'subscription not found'}

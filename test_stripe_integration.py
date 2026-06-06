"""
Testes para a integração Stripe.
Execute com: python test_stripe_integration.py
"""

import os
import sys
from datetime import datetime, timedelta
import json
from unittest.mock import MagicMock, patch

# Mock do módulo stripe antes de importar
sys.modules['stripe'] = MagicMock()
sys.modules['stripe'].error = MagicMock()
sys.modules['stripe'].error.StripeError = Exception
sys.modules['stripe'].error.SignatureVerificationError = Exception

# Simula variáveis de ambiente para teste
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_mock_key')
os.environ.setdefault('STRIPE_PUBLIC_KEY', 'pk_test_mock_key')
os.environ.setdefault('STRIPE_WEBHOOK_SECRET', 'whsec_test_mock_key')
os.environ.setdefault('STRIPE_PRICE_PREMIUM_MONTHLY', 'price_test_123')
os.environ.setdefault('BASE_URL', 'http://localhost:8765')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, User, Subscription
from stripe_service import (
    create_or_update_subscription,
    get_user_subscription,
    cancel_subscription,
    process_webhook_event
)
from auth import hash_password


def setup_test_db():
    """Cria banco de dados em memória para testes."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_create_subscription():
    """Testa criação de subscription."""
    db = setup_test_db()

    # Cria usuário de teste
    user = User(
        id=1,
        full_name="Test User",
        email="test@example.com",
        password_hash=hash_password("password123"),
        cpf_hash=hash_password("12345678901")
    )
    db.add(user)
    db.commit()

    # Cria subscription
    current_period_start = datetime.utcnow()
    current_period_end = current_period_start + timedelta(days=30)

    sub = create_or_update_subscription(
        db=db,
        user_id=user.id,
        stripe_customer_id='cus_test_123',
        stripe_subscription_id='sub_test_456',
        status='active',
        current_period_start=current_period_start,
        current_period_end=current_period_end
    )

    assert sub.user_id == user.id
    assert sub.stripe_customer_id == 'cus_test_123'
    assert sub.stripe_subscription_id == 'sub_test_456'
    assert sub.status == 'active'
    assert sub.plan == 'premium'

    print("[OK] test_create_subscription passed")


def test_get_subscription():
    """Testa obtenção de dados de subscription."""
    db = setup_test_db()

    # Cria usuário e subscription
    user = User(
        id=1,
        full_name="Test User",
        email="test@example.com",
        password_hash=hash_password("password123"),
        cpf_hash=hash_password("12345678901")
    )
    db.add(user)
    db.commit()

    current_period_start = datetime.utcnow()
    current_period_end = current_period_start + timedelta(days=30)

    create_or_update_subscription(
        db=db,
        user_id=user.id,
        stripe_customer_id='cus_test_123',
        stripe_subscription_id='sub_test_456',
        status='active',
        current_period_start=current_period_start,
        current_period_end=current_period_end
    )

    # Obtém dados
    sub_data = get_user_subscription(db, user.id)

    assert sub_data['plan'] == 'premium'
    assert sub_data['status'] == 'active'
    assert sub_data['is_active'] is True
    assert sub_data['current_period_end'] is not None

    print("[OK] test_get_subscription passed")


def test_get_subscription_not_found():
    """Testa obtenção de subscription inexistente."""
    db = setup_test_db()

    sub_data = get_user_subscription(db, user_id=999)

    assert sub_data['plan'] is None
    assert sub_data['status'] is None
    assert sub_data['is_active'] is False

    print("[OK] test_get_subscription_not_found passed")


def test_update_subscription():
    """Testa atualização de subscription."""
    db = setup_test_db()

    # Cria usuário e subscription
    user = User(
        id=1,
        full_name="Test User",
        email="test@example.com",
        password_hash=hash_password("password123"),
        cpf_hash=hash_password("12345678901")
    )
    db.add(user)
    db.commit()

    current_period_start = datetime.utcnow()
    current_period_end = current_period_start + timedelta(days=30)

    sub1 = create_or_update_subscription(
        db=db,
        user_id=user.id,
        stripe_customer_id='cus_test_123',
        stripe_subscription_id='sub_test_456',
        status='active',
        current_period_start=current_period_start,
        current_period_end=current_period_end
    )

    sub_id = sub1.id

    # Atualiza com novos dados
    new_period_end = current_period_end + timedelta(days=30)
    sub2 = create_or_update_subscription(
        db=db,
        user_id=user.id,
        stripe_customer_id='cus_test_123',
        stripe_subscription_id='sub_test_789',
        status='past_due',
        current_period_start=current_period_start,
        current_period_end=new_period_end
    )

    # Deve ser o mesmo registro (ID igual)
    assert sub2.id == sub_id
    assert sub2.stripe_subscription_id == 'sub_test_789'
    assert sub2.status == 'past_due'

    print("[OK] test_update_subscription passed")


def test_process_webhook_subscription_created():
    """Testa processamento de webhook subscription.created."""
    db = setup_test_db()

    # Cria usuário
    user = User(
        id=1,
        full_name="Test User",
        email="test@example.com",
        password_hash=hash_password("password123"),
        cpf_hash=hash_password("12345678901")
    )
    db.add(user)
    db.commit()

    # Simula evento Stripe
    now = datetime.utcnow()
    event = {
        'type': 'customer.subscription.created',
        'data': {
            'object': {
                'id': 'sub_test_123',
                'customer': 'cus_test_456',
                'status': 'active',
                'current_period_start': int(now.timestamp()),
                'current_period_end': int((now + timedelta(days=30)).timestamp()),
                'metadata': {
                    'user_id': '1'
                }
            }
        }
    }

    result = process_webhook_event(db, event)

    assert result['status'] == 'processed'
    assert result['event'] == 'subscription.created'
    assert result['user_id'] == 1

    # Verifica se foi criada no DB
    sub_data = get_user_subscription(db, 1)
    assert sub_data['is_active'] is True
    assert sub_data['plan'] == 'premium'

    print("[OK] test_process_webhook_subscription_created passed")


def test_process_webhook_subscription_deleted():
    """Testa processamento de webhook subscription.deleted."""
    db = setup_test_db()

    # Cria usuário e subscription
    user = User(
        id=1,
        full_name="Test User",
        email="test@example.com",
        password_hash=hash_password("password123"),
        cpf_hash=hash_password("12345678901")
    )
    db.add(user)
    db.commit()

    current_period_start = datetime.utcnow()
    current_period_end = current_period_start + timedelta(days=30)

    create_or_update_subscription(
        db=db,
        user_id=user.id,
        stripe_customer_id='cus_test_123',
        stripe_subscription_id='sub_test_456',
        status='active',
        current_period_start=current_period_start,
        current_period_end=current_period_end
    )

    # Simula evento de deleção
    event = {
        'type': 'customer.subscription.deleted',
        'data': {
            'object': {
                'id': 'sub_test_456',
                'customer': 'cus_test_123',
                'status': 'canceled'
            }
        }
    }

    result = process_webhook_event(db, event)

    assert result['status'] == 'processed'
    assert result['event'] == 'subscription.deleted'

    # Verifica se foi marcada como cancelada
    sub_data = get_user_subscription(db, 1)
    assert sub_data['status'] == 'canceled'
    assert sub_data['is_active'] is False

    print("[OK] test_process_webhook_subscription_deleted passed")


def test_import_billing_routes():
    """Testa se o módulo billing_routes pode ser importado."""
    try:
        # Mock da Request do FastAPI
        sys.modules['fastapi.requests'] = MagicMock()

        from billing_routes import router as billing_router
        assert billing_router is not None
        print("[OK] test_import_billing_routes passed")
    except ImportError as e:
        # É ok se falhar por causa de imports do FastAPI (não é problema do código)
        if 'fastapi' in str(e).lower():
            print("[OK] test_import_billing_routes skipped (FastAPI not available)")
        else:
            raise
    except Exception as e:
        print(f"[FAIL] test_import_billing_routes failed: {e}")
        raise


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Testing Stripe Integration")
    print("=" * 60 + "\n")

    try:
        test_create_subscription()
        test_get_subscription()
        test_get_subscription_not_found()
        test_update_subscription()
        test_process_webhook_subscription_created()
        test_process_webhook_subscription_deleted()
        test_import_billing_routes()

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}\n")
        sys.exit(1)

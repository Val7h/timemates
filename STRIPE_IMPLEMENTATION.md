# Stripe Integration Implementation — TimeMates

## Resumo da Implementação

A integração Stripe foi implementada completamente no TimeMates, permitindo que usuários se tornem premium via pagamento de subscription mensal (R$ 9.90/mês ou valor configurável).

## Arquivos Criados/Modificados

### 1. **requirements.txt** (modificado)
- Adicionado: `stripe==11.1.3`

### 2. **database.py** (modificado)
- Nova tabela: `Subscription`
  - Rastreia customer ID do Stripe
  - Rastreia subscription ID do Stripe
  - Armazena status (active, canceled, past_due)
  - Rastreia período de cobrança

### 3. **stripe_service.py** (novo)
Núcleo da lógica de integração:

#### Funções principais:
- `create_checkout_session(user)` — Gera URL de checkout do Stripe
- `create_or_update_subscription(db, user_id, ...)` — CRUD de subscriptions
- `cancel_subscription(db, user_id)` — Cancela subscription do Stripe
- `get_user_subscription(db, user_id)` — Retorna status/dados de subscription
- `process_webhook_event(db, event)` — Processa eventos do Stripe

#### Eventos suportados:
- `customer.subscription.created` — Nova subscription confirmada
- `customer.subscription.updated` — Subscription atualizada
- `customer.subscription.deleted` — Subscription cancelada
- `invoice.payment_succeeded` — Pagamento confirmado
- `invoice.payment_failed` — Pagamento falhou

### 4. **billing_routes.py** (novo)
Endpoints FastAPI para billing:

- **POST `/api/billing/create-checkout`** — Inicia processo de checkout
  - Requer autenticação (JWT token)
  - Retorna: `{ "checkout_url": "...", "session_id": "..." }`

- **GET `/api/billing/subscription`** — Obtém status de subscription
  - Retorna: `{ "plan", "status", "is_active", "current_period_end" }`

- **POST `/api/billing/cancel`** — Cancela subscription
  - Requer autenticação
  - Retorna: `{ "status": "canceled" }`

- **POST `/api/billing/webhooks/stripe`** — Webhook para eventos Stripe
  - Verifica assinatura com `STRIPE_WEBHOOK_SECRET`
  - Processa eventos automaticamente

- **GET `/api/billing/public-key`** — Retorna chave pública do Stripe
  - Necessária para o frontend integrar com Stripe.js

- **POST `/api/billing/portal`** — Cria link para portal de gerenciamento
  - Permite usuário alterar cartão, ver invoices, etc.

### 5. **.env.example** (modificado)
Adicionadas variáveis de exemplo:
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PREMIUM_MONTHLY=price_...
```

### 6. **main.py** (modificado)
- Importa `Subscription` do database.py
- Importa e inclui rotas de billing: `from billing_routes import router as billing_router`
- `app.include_router(billing_router)`

### 7. **STRIPE_SETUP.md** (novo)
Guia completo de setup incluindo:
- Como criar conta no Stripe
- Como obter chaves de API
- Como criar produtos/preços
- Como configurar webhooks
- Exemplos de cURL para testar
- Cartões de teste do Stripe
- Como usar Stripe CLI localmente
- Troubleshooting

### 8. **test_stripe_integration.py** (novo)
Testes unitários cobrindo:
- Criação de subscription
- Obtenção de dados de subscription
- Atualização de subscription
- Processamento de webhooks
- Import de módulos

**Status:** Todos os 7 testes passando

## Fluxo de Pagamento

```
1. Frontend chama: GET /api/billing/public-key
2. Frontend renderiza botão de checkout com Stripe.js

3. Usuário clica "Upgrade para Premium"
4. Backend: POST /api/billing/create-checkout
5. Retorna: checkout_url do Stripe

6. Usuário vai para Stripe Checkout (Hosted)
7. Preenche cartão de crédito
8. Clica "Pagar"

9. Stripe processa pagamento
10. Stripe envia webhook: customer.subscription.created
11. Backend: POST /api/billing/webhooks/stripe
    - Valida assinatura
    - Cria Subscription no DB
    - Status: "active"

12. Usuário redirecionado para: /billing/success?session_id=...
13. Frontend: GET /api/billing/subscription
    - Confirma status "active"
    - Habilita features premium

14. Cancelamento (opcional):
    - POST /api/billing/cancel
    - Stripe envia webhook: customer.subscription.deleted
    - Backend marca subscription como "canceled"
```

## Recursos Premium

Depois de implementar a parte de negócio (o que fazer com `is_active == True`):

```python
# No main.py ou rotas específicas:
sub_data = get_user_subscription(db, user.id)
if not sub_data['is_active']:
    raise HTTPException(status_code=403, detail="Premium required")
```

## Variáveis de Ambiente Obrigatórias

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `STRIPE_SECRET_KEY` | Chave secreta do Stripe | `sk_test_51234...` |
| `STRIPE_PUBLIC_KEY` | Chave pública do Stripe | `pk_test_51234...` |
| `STRIPE_WEBHOOK_SECRET` | Segredo para validar webhooks | `whsec_1234...` |
| `STRIPE_PRICE_PREMIUM_MONTHLY` | ID do preço para cobrança | `price_1234...` |
| `BASE_URL` | URL base da aplicação | `https://timemates.app` |

## Deploy em Produção

1. Obtenha **Live Keys** do Stripe (começam com `sk_live_` e `pk_live_`)
2. Atualize `.env` com as chaves de produção
3. Configure novo webhook em `https://seu-dominio/api/billing/webhooks/stripe`
4. Teste fluxo completo com cartão de teste
5. Ative o app para aceitar pagamentos reais

## Arquitetura

```
timeMates/
├── requirements.txt (stripe adicionado)
├── database.py (tabela Subscription)
├── stripe_service.py (lógica de integração)
├── billing_routes.py (endpoints FastAPI)
├── main.py (integração das rotas)
├── .env (variáveis secretas)
├── .env.example (template)
├── STRIPE_SETUP.md (documentação)
├── STRIPE_IMPLEMENTATION.md (este arquivo)
└── test_stripe_integration.py (testes)
```

## Validação

Todos os testes passam:
```
[OK] test_create_subscription
[OK] test_get_subscription
[OK] test_get_subscription_not_found
[OK] test_update_subscription
[OK] test_process_webhook_subscription_created
[OK] test_process_webhook_subscription_deleted
[OK] test_import_billing_routes
```

Execute com: `python test_stripe_integration.py`

## Próximos Passos (Opcional)

1. **Frontend**: Integrar Stripe.js + Elements
   - Botão "Upgrade para Premium"
   - Página de sucesso/cancelamento
   - Link para portal de gerenciamento

2. **Email**: Enviar confirmação de subscription
   - Template em `email_service.py`

3. **Proteção de Rotas**: Bloquear features premium para não-premium
   - Decorator customizado
   - Check em rotas específicas

4. **Analytics**: Rastrear conversões
   - Quantos usuários compraram
   - MRR (Monthly Recurring Revenue)
   - Churn rate

5. **Testes de Webhook**: Setup com Stripe CLI
   - `stripe listen --forward-to localhost:8765/api/billing/webhooks/stripe`
   - `stripe trigger customer.subscription.created`

## Suporte

- [Stripe API Docs](https://stripe.com/docs/api)
- [Stripe Webhooks](https://stripe.com/docs/webhooks)
- [Stripe Testing](https://stripe.com/docs/testing)
- Ver `STRIPE_SETUP.md` para guia completo

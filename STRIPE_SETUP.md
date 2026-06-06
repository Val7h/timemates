# Stripe Integration Setup — TimeMates

Guia completo para configurar e testar a integração Stripe no TimeMates.

## 1. Criar Conta no Stripe

1. Acesse https://stripe.com
2. Clique em "Sign up" e crie uma conta
3. Complete a verificação de email
4. Faça login no [Stripe Dashboard](https://dashboard.stripe.com)

## 2. Obter Chaves de API (Test Keys)

1. No Dashboard, vá para: **Developers** → **API Keys**
2. Copie as chaves de teste:
   - **Secret Key** (começa com `sk_test_`) → `STRIPE_SECRET_KEY`
   - **Publishable Key** (começa com `pk_test_`) → `STRIPE_PUBLIC_KEY`
3. Para webhook: **Developers** → **Webhooks** → **Add endpoint**
   - URL: `https://seu-domain/api/billing/webhooks/stripe` (ou `http://localhost:8765/api/billing/webhooks/stripe` para local)
   - Eventos: `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`
   - Copie o **Signing Secret** → `STRIPE_WEBHOOK_SECRET`

## 3. Criar Produto de Cobrança

1. No Dashboard, vá para: **Products** → **+ Add product**
2. Preencha:
   - **Name**: `Premium Monthly`
   - **Type**: `Service`
   - **Billing cycle**: `Monthly`
   - **Price**: `9.90` (em reais, ou ajuste para sua moeda)
3. Clique em **Create product**
4. Copie o **Price ID** (começa com `price_`) → `STRIPE_PRICE_PREMIUM_MONTHLY`

## 4. Configurar Variáveis de Ambiente

Crie/atualize o arquivo `.env` na raiz do projeto:

```bash
# ── Stripe (Test Keys) ──────────────────────────────────────────────────────
STRIPE_SECRET_KEY=sk_test_51234567890abcdef
STRIPE_PUBLIC_KEY=pk_test_51234567890abcdef
STRIPE_WEBHOOK_SECRET=whsec_1234567890abcdef
STRIPE_PRICE_PREMIUM_MONTHLY=price_1234567890abcdef

# ── Base URL ──────────────────────────────────────────────────────────────────
BASE_URL=http://localhost:8765
```

## 5. Instalar Dependências

```bash
pip install -r requirements.txt
```

## 6. Executar Servidor

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8765 --reload
```

## 7. Testar Endpoints

### 7.1 Obter Stripe Public Key

```bash
curl http://localhost:8765/api/billing/public-key
```

**Resposta:**
```json
{
  "public_key": "pk_test_..."
}
```

### 7.2 Criar Sessão de Checkout (Requer Token de Autenticação)

Primeiro, registre e faça login para obter um token JWT:

```bash
# 1. Registrar
curl -X POST http://localhost:8765/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePassword123!",
    "cpf": "12345678901"
  }'

# 2. Fazer login e obter token
TOKEN=$(curl -X POST http://localhost:8765/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123!"
  }' | jq -r '.access_token')

# 3. Criar checkout
curl -X POST http://localhost:8765/api/billing/create-checkout \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Resposta:**
```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_...",
  "session_id": "cs_..."
}
```

### 7.3 Obter Status de Subscription

```bash
curl http://localhost:8765/api/billing/subscription \
  -H "Authorization: Bearer $TOKEN"
```

**Resposta (sem subscription):**
```json
{
  "plan": null,
  "status": null,
  "current_period_end": null,
  "is_active": false
}
```

### 7.4 Cancelar Subscription

```bash
curl -X POST http://localhost:8765/api/billing/cancel \
  -H "Authorization: Bearer $TOKEN"
```

**Resposta:**
```json
{
  "status": "canceled",
  "message": "Subscription cancelada com sucesso"
}
```

### 7.5 Criar Portal de Gerenciamento de Billing

```bash
curl -X POST http://localhost:8765/api/billing/portal \
  -H "Authorization: Bearer $TOKEN"
```

**Resposta:**
```json
{
  "portal_url": "https://billing.stripe.com/p/session/..."
}
```

## 8. Testar com Cartão de Teste Stripe

Ao clicar em **checkout_url**, você será levado para a página de checkout do Stripe.

Use os seguintes cartões de teste:

| Cenário | Número | Exp | CVC |
|---------|--------|-----|-----|
| Sucesso | `4242 4242 4242 4242` | 12/26 | 123 |
| Falha | `4000 0000 0000 0002` | 12/26 | 123 |
| Ação Necessária | `4000 0025 0000 3155` | 12/26 | 123 |

## 9. Simular Webhooks Localmente (Stripe CLI)

### 9.1 Instalar Stripe CLI

- **macOS**: `brew install stripe/stripe-cli/stripe`
- **Windows**: Baixe em https://github.com/stripe/stripe-cli/releases
- **Linux**: `curl https://raw.githubusercontent.com/stripe/stripe-cli/master/install.sh | bash`

### 9.2 Fazer Login

```bash
stripe login
```

Escolha sua conta e copie a chave fornecida.

### 9.3 Encaminhar Webhooks

```bash
stripe listen --forward-to http://localhost:8765/api/billing/webhooks/stripe
```

Copie o **Webhook signing secret** exibido.

### 9.4 Simular Evento

Em outro terminal:

```bash
stripe trigger customer.subscription.created
```

## 10. Banco de Dados

A tabela `subscriptions` é criada automaticamente ao iniciar o servidor.

**Schema:**
```sql
CREATE TABLE subscriptions (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL UNIQUE,
  stripe_customer_id VARCHAR(255) NOT NULL UNIQUE,
  stripe_subscription_id VARCHAR(255) NOT NULL UNIQUE,
  plan VARCHAR(50),
  status VARCHAR(20),
  current_period_start TIMESTAMP,
  current_period_end TIMESTAMP,
  cancel_at_period_end BOOLEAN,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

## 11. Fluxo Completo

1. **Usuário acessa página de checkout**
2. **GET `/api/billing/public-key`** → Obter chave pública
3. **POST `/api/billing/create-checkout`** → Gerar URL de checkout
4. **Usuário preenche cartão** no Stripe Checkout
5. **Stripe envia webhook** `customer.subscription.created`
6. **Backend processa webhook** e cria subscription no DB
7. **GET `/api/billing/subscription`** → Verificar status premium
8. **GET `/api/billing/portal`** → Permitir gerenciamento (cancelar, atualizar cartão)

## 12. Migrar para Produção

Quando estiver pronto para produção:

1. Crie uma conta de produção no Stripe (ou ative)
2. Obtenha **Live Keys** (começam com `sk_live_` e `pk_live_`)
3. Atualize `.env` com as chaves de produção
4. Atualize `BASE_URL` para seu domínio real
5. Configure webhook no Stripe Dashboard para seu domínio
6. Teste e monitore no [Stripe Dashboard](https://dashboard.stripe.com)

## 13. Troubleshooting

### Erro: "STRIPE_SECRET_KEY not configured"

Verifique se `.env` foi criado com as variáveis corretas.

```bash
# Linux/Mac
cat .env

# Windows
type .env
```

### Erro: "Invalid signature"

O webhook secret pode estar errado. Regenere em **Developers** → **Webhooks**.

### Erro: "user_id not found in metadata"

Ao criar checkout, certifique-se de que o usuário está autenticado (token JWT válido).

### Webhook não é recebido

Se usar local:
1. Instale Stripe CLI
2. Execute `stripe listen --forward-to http://localhost:8765/api/billing/webhooks/stripe`
3. Use o signing secret fornecido

Se usar produção:
1. Verifique se a URL está correta em **Developers** → **Webhooks**
2. Verifique os logs em **Developers** → **Webhooks** → Clique no endpoint → **Recent events**

## Referências

- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe Billing](https://stripe.com/docs/billing)
- [Stripe Webhook Events](https://stripe.com/docs/api/events)
- [Stripe Test Cards](https://stripe.com/docs/testing)

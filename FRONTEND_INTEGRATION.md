# Frontend Integration Guide — Stripe Checkout

Este documento fornece exemplos de como integrar o Stripe Checkout no frontend do TimeMates.

## 1. HTML com Stripe.js

```html
<!-- Em static/index.html, adicione Stripe.js antes de </body> -->
<script src="https://js.stripe.com/v3/"></script>

<!-- Botão para iniciar checkout -->
<button id="upgrade-btn" class="btn btn-primary">
  Upgrade para Premium
</button>

<!-- Modal ou página de status -->
<div id="billing-status"></div>
```

## 2. JavaScript - Carregar Chave Pública

```javascript
// script.js ou em <script> no HTML

let stripePublicKey = null;

// Carregar chave pública quando a página carrega
async function loadStripeKey() {
  try {
    const response = await fetch('/api/billing/public-key');
    const data = await response.json();
    stripePublicKey = data.public_key;
    console.log('Stripe key loaded');
  } catch (error) {
    console.error('Failed to load Stripe key:', error);
  }
}

loadStripeKey();
```

## 3. JavaScript - Criar Checkout

```javascript
document.getElementById('upgrade-btn').addEventListener('click', async () => {
  const token = localStorage.getItem('access_token');
  
  if (!token) {
    alert('Você precisa estar logado para fazer upgrade');
    return;
  }

  try {
    // Chamar endpoint para criar checkout
    const response = await fetch('/api/billing/create-checkout', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      const error = await response.json();
      alert(`Erro: ${error.detail}`);
      return;
    }

    const data = await response.json();
    
    // Redirecionar para Stripe Checkout
    window.location.href = data.checkout_url;
  } catch (error) {
    console.error('Checkout error:', error);
    alert('Erro ao criar checkout');
  }
});
```

## 4. Página de Sucesso

```html
<!-- static/billing-success.html ou rota /billing/success -->
<div id="success-message">
  <h2>Obrigado!</h2>
  <p>Seu pagamento foi processado com sucesso.</p>
  <p id="status-text">Verificando seu status premium...</p>
  <button onclick="window.location.href='/'">Voltar ao Início</button>
</div>

<script>
async function checkPremiumStatus() {
  const token = localStorage.getItem('access_token');
  
  try {
    const response = await fetch('/api/billing/subscription', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    const data = await response.json();
    
    if (data.is_active) {
      document.getElementById('status-text').textContent = 
        'Sua subscription premium está ativa!';
    } else {
      document.getElementById('status-text').textContent = 
        'Ainda processando seu pagamento. Aguarde alguns minutos...';
      // Retry após 5 segundos
      setTimeout(checkPremiumStatus, 5000);
    }
  } catch (error) {
    console.error('Error checking status:', error);
  }
}

checkPremiumStatus();
</script>
```

## 5. Mostrar Status no Dashboard

```javascript
async function loadSubscriptionStatus() {
  const token = localStorage.getItem('access_token');
  
  if (!token) return;

  try {
    const response = await fetch('/api/billing/subscription', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    const data = await response.json();

    // Atualizar UI
    const statusDiv = document.getElementById('billing-status');
    
    if (data.is_active) {
      statusDiv.innerHTML = `
        <div class="alert alert-success">
          <h4>Premium Ativo</h4>
          <p>Plano: ${data.plan}</p>
          <p>Válido até: ${new Date(data.current_period_end).toLocaleDateString('pt-BR')}</p>
          <button id="manage-btn" class="btn btn-secondary">Gerenciar Subscription</button>
          <button id="cancel-btn" class="btn btn-danger">Cancelar</button>
        </div>
      `;

      // Anexar listeners
      document.getElementById('manage-btn').addEventListener('click', openBillingPortal);
      document.getElementById('cancel-btn').addEventListener('click', cancelSubscription);
    } else {
      statusDiv.innerHTML = `
        <div class="alert alert-info">
          <h4>Versão Gratuita</h4>
          <p>Faça upgrade para acessar recursos premium</p>
          <button onclick="document.getElementById('upgrade-btn').click()" class="btn btn-primary">
            Upgrade para Premium
          </button>
        </div>
      `;
    }
  } catch (error) {
    console.error('Error loading subscription:', error);
  }
}

// Chamar ao carregar página
loadSubscriptionStatus();
```

## 6. Gerenciar Subscription (Portal)

```javascript
async function openBillingPortal() {
  const token = localStorage.getItem('access_token');
  
  try {
    const response = await fetch('/api/billing/portal', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    const data = await response.json();
    
    // Redirecionar para portal do Stripe
    window.location.href = data.portal_url;
  } catch (error) {
    console.error('Portal error:', error);
    alert('Erro ao abrir portal');
  }
}
```

## 7. Cancelar Subscription

```javascript
async function cancelSubscription() {
  if (!confirm('Tem certeza que deseja cancelar sua subscription?')) {
    return;
  }

  const token = localStorage.getItem('access_token');
  
  try {
    const response = await fetch('/api/billing/cancel', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    const data = await response.json();
    
    alert('Subscription cancelada com sucesso');
    loadSubscriptionStatus(); // Atualizar status
  } catch (error) {
    console.error('Cancel error:', error);
    alert('Erro ao cancelar subscription');
  }
}
```

## 8. Proteção de Rotas Premium

```javascript
async function requirePremium() {
  const token = localStorage.getItem('access_token');
  
  if (!token) {
    // Redirecionar para login
    window.location.href = '/login';
    return false;
  }

  try {
    const response = await fetch('/api/billing/subscription', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    const data = await response.json();
    
    if (!data.is_active) {
      alert('Você precisa de uma subscription premium para acessar este recurso');
      window.location.href = '/';
      return false;
    }

    return true;
  } catch (error) {
    console.error('Premium check error:', error);
    window.location.href = '/';
    return false;
  }
}

// Usar em rotas premium:
// if (!await requirePremium()) return;
```

## 9. React Example (Se usar React)

```jsx
import { useState, useEffect } from 'react';

function BillingStatus() {
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSubscription();
  }, []);

  const loadSubscription = async () => {
    const token = localStorage.getItem('access_token');
    try {
      const response = await fetch('/api/billing/subscription', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setSubscription(data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const createCheckout = async () => {
    const token = localStorage.getItem('access_token');
    try {
      const response = await fetch('/api/billing/create-checkout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      const data = await response.json();
      window.location.href = data.checkout_url;
    } catch (error) {
      alert('Erro ao criar checkout');
    }
  };

  const cancelSub = async () => {
    if (!confirm('Cancelar subscription?')) return;
    
    const token = localStorage.getItem('access_token');
    try {
      await fetch('/api/billing/cancel', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      alert('Subscription cancelada');
      loadSubscription();
    } catch (error) {
      alert('Erro ao cancelar');
    }
  };

  if (loading) return <div>Carregando...</div>;

  return (
    <div>
      {subscription?.is_active ? (
        <div className="alert alert-success">
          <h4>Premium Ativo</h4>
          <p>Válido até: {new Date(subscription.current_period_end).toLocaleDateString('pt-BR')}</p>
          <button onClick={cancelSub} className="btn btn-danger">
            Cancelar
          </button>
        </div>
      ) : (
        <div className="alert alert-info">
          <h4>Versão Gratuita</h4>
          <button onClick={createCheckout} className="btn btn-primary">
            Upgrade para Premium
          </button>
        </div>
      )}
    </div>
  );
}

export default BillingStatus;
```

## 10. Vue.js Example

```vue
<template>
  <div>
    <div v-if="loading">Carregando...</div>
    
    <div v-else-if="subscription.is_active" class="alert alert-success">
      <h4>Premium Ativo</h4>
      <p>Válido até: {{ formatDate(subscription.current_period_end) }}</p>
      <button @click="cancelSubscription" class="btn btn-danger">
        Cancelar
      </button>
    </div>
    
    <div v-else class="alert alert-info">
      <h4>Versão Gratuita</h4>
      <button @click="createCheckout" class="btn btn-primary">
        Upgrade para Premium
      </button>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      subscription: {},
      loading: true
    };
  },
  
  mounted() {
    this.loadSubscription();
  },
  
  methods: {
    async loadSubscription() {
      const token = localStorage.getItem('access_token');
      try {
        const response = await fetch('/api/billing/subscription', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        this.subscription = await response.json();
      } catch (error) {
        console.error('Error:', error);
      } finally {
        this.loading = false;
      }
    },
    
    async createCheckout() {
      const token = localStorage.getItem('access_token');
      try {
        const response = await fetch('/api/billing/create-checkout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        const data = await response.json();
        window.location.href = data.checkout_url;
      } catch (error) {
        alert('Erro ao criar checkout');
      }
    },
    
    async cancelSubscription() {
      if (!confirm('Cancelar subscription?')) return;
      
      const token = localStorage.getItem('access_token');
      try {
        await fetch('/api/billing/cancel', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        alert('Subscription cancelada');
        this.loadSubscription();
      } catch (error) {
        alert('Erro ao cancelar');
      }
    },
    
    formatDate(dateString) {
      return new Date(dateString).toLocaleDateString('pt-BR');
    }
  }
};
</script>
```

## 11. CSS Styling Example

```css
/* Estilos para componentes de billing */

.billing-container {
  max-width: 600px;
  margin: 20px auto;
  padding: 20px;
}

.billing-status {
  border-radius: 8px;
  padding: 20px;
  margin: 20px 0;
  background: #f8f9fa;
  border-left: 4px solid #007bff;
}

.billing-status.premium {
  border-left-color: #28a745;
  background: #d4edda;
}

.billing-status h4 {
  margin-top: 0;
  color: #333;
}

.billing-status p {
  margin: 10px 0;
  color: #666;
}

.billing-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.billing-actions button {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover {
  background: #0056b3;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover {
  background: #c82333;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}
```

## Fluxo Completo (Resumo)

1. **Página inicial**: Exibir status (premium ou gratuito)
2. **Botão "Upgrade"**: Usuário clica
3. **API Call**: POST `/api/billing/create-checkout`
4. **Stripe Checkout**: Usuário preenche cartão
5. **Webhook**: Stripe envia confirmação ao backend
6. **Sucesso**: Usuário redirecionado para `/billing/success`
7. **Verificar Status**: GET `/api/billing/subscription`
8. **UI Atualizada**: Mostrar "Premium Ativo"

## Teste Local

```bash
# Terminal 1: Iniciar servidor FastAPI
python -m uvicorn main:app --reload

# Terminal 2: Iniciar Stripe CLI
stripe listen --forward-to http://localhost:8765/api/billing/webhooks/stripe

# Terminal 3: Simular evento
stripe trigger customer.subscription.created

# Browser: Acessar http://localhost:8765
```

## Troubleshooting

**Erro: "Stripe key not loaded"**
- Verificar se `/api/billing/public-key` retorna corretamente
- Verificar se `STRIPE_PUBLIC_KEY` está em `.env`

**Erro: "Invalid checkout URL"**
- Verificar token JWT
- Verificar se `STRIPE_SECRET_KEY` está em `.env`

**Webhook não recebido**
- Usar Stripe CLI: `stripe listen --forward-to localhost:8765/...`
- Verificar webhook secret em `.env`

**Subscription não aparece após pagamento**
- Aguardar alguns segundos (webhook é assíncrono)
- Verificar logs do Stripe Dashboard

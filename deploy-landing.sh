#!/bin/bash

# ==========================================
# Script: Deploy Landing Page - TimeMates no Render
# ==========================================
# Execute com: bash deploy-landing.sh
# Ou: chmod +x deploy-landing.sh && ./deploy-landing.sh

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções
log_success() { echo -e "${GREEN}✓ $1${NC}"; }
log_error() { echo -e "${RED}✗ $1${NC}"; }
log_info() { echo -e "${BLUE}→ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠ $1${NC}"; }

# ==========================================
# PASSO 1: Validar Git
# ==========================================
echo ""
echo -e "${BLUE}=== PASSO 1: Validar Repositório ===${NC}"

if [ ! -d ".git" ]; then
    log_error "Não é um repositório Git"
    exit 1
fi

log_success "Repositório Git validado"

# ==========================================
# PASSO 2: Criar Estrutura
# ==========================================
echo ""
echo -e "${BLUE}=== PASSO 2: Criar Estrutura ===${NC}"

mkdir -p public/landing
log_success "Diretório criado: public/landing/"

# ==========================================
# PASSO 3: Criar Arquivos
# ==========================================
echo ""
echo -e "${BLUE}=== PASSO 3: Criar Arquivos ===${NC}"

# HTML
cat > public/landing/index.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="TimeMates - Conectando pessoas que querem aprender juntas">
    <title>TimeMates - Plataforma de Encontros Educacionais</title>
    <link rel="stylesheet" href="./style.css">
</head>
<body>
    <nav class="navbar">
        <div class="container">
            <div class="nav-brand">⏰ TimeMates</div>
            <ul class="nav-menu">
                <li><a href="#features">Recursos</a></li>
                <li><a href="#how-it-works">Como Funciona</a></li>
                <li><a href="#pricing">Planos</a></li>
            </ul>
            <div class="nav-auth">
                <a href="/login" class="btn-login">Login</a>
                <a href="/signup" class="btn-signup">Começar Agora</a>
            </div>
        </div>
    </nav>

    <section class="hero">
        <div class="container">
            <h1>Encontre Seu Parceiro de Aprendizado</h1>
            <p class="hero-subtitle">Conecte-se com pessoas que querem aprender os mesmos assuntos</p>
            <div class="hero-buttons">
                <button class="btn btn-primary btn-large" onclick="window.location.href='/signup'">Começar Gratuitamente</button>
                <button class="btn btn-secondary btn-large" onclick="document.getElementById('how-it-works').scrollIntoView({behavior:'smooth'})">Saiba Mais</button>
            </div>
            <div class="hero-stats">
                <div class="stat">
                    <strong>5,000+</strong>
                    <span>Usuários Ativos</span>
                </div>
                <div class="stat">
                    <strong>1,200+</strong>
                    <span>Parcerias</span>
                </div>
                <div class="stat">
                    <strong>15</strong>
                    <span>Cidades</span>
                </div>
            </div>
        </div>
    </section>

    <section id="features" class="features">
        <div class="container">
            <h2>Recursos Principais</h2>
            <div class="features-grid">
                <div class="feature-card">
                    <span class="feature-icon">🔍</span>
                    <h3>Busca Inteligente</h3>
                    <p>Encontre pessoas baseado em área de interesse, horários e localização</p>
                </div>
                <div class="feature-card">
                    <span class="feature-icon">💬</span>
                    <h3>Chat Integrado</h3>
                    <p>Comunicação em tempo real com seus parceiros</p>
                </div>
                <div class="feature-card">
                    <span class="feature-icon">📅</span>
                    <h3>Agendamento</h3>
                    <p>Marque encontros online com calendário compartilhado</p>
                </div>
                <div class="feature-card">
                    <span class="feature-icon">⭐</span>
                    <h3>Avaliações</h3>
                    <p>Sistema de reputação para conectar com pessoas confiáveis</p>
                </div>
                <div class="feature-card">
                    <span class="feature-icon">🎓</span>
                    <h3>Áreas de Estudo</h3>
                    <p>Mais de 100 tópicos: idiomas, programação, exames e mais</p>
                </div>
                <div class="feature-card">
                    <span class="feature-icon">📱</span>
                    <h3>Acesso Mobile</h3>
                    <p>Use no navegador do seu celular, tablet ou computador</p>
                </div>
            </div>
        </div>
    </section>

    <section id="how-it-works" class="how-it-works">
        <div class="container">
            <h2>Como Funciona em 3 Passos</h2>
            <div class="steps">
                <div class="step">
                    <div class="step-number">1</div>
                    <h3>Cadastre-se</h3>
                    <p>Crie sua conta com email ou telefone</p>
                </div>
                <div class="step">
                    <div class="step-number">2</div>
                    <h3>Escolha o Assunto</h3>
                    <p>Indique o que quer aprender e qual horário prefere</p>
                </div>
                <div class="step">
                    <div class="step-number">3</div>
                    <h3>Conecte-se</h3>
                    <p>Encontre parceiros e comece a aprender</p>
                </div>
            </div>
        </div>
    </section>

    <section id="pricing" class="pricing">
        <div class="container">
            <h2>Planos e Preços</h2>
            <div class="pricing-grid">
                <div class="pricing-card">
                    <h3>Básico</h3>
                    <div class="price">Gratuito</div>
                    <ul class="features-list">
                        <li>✓ Criar perfil</li>
                        <li>✓ Buscar parceiros</li>
                        <li>✓ Chat ilimitado</li>
                        <li>✓ Até 5 salas</li>
                    </ul>
                </div>
                <div class="pricing-card featured">
                    <h3>Premium</h3>
                    <div class="price">R$ 29<span>/mês</span></div>
                    <ul class="features-list">
                        <li>✓ Tudo do Básico</li>
                        <li>✓ Salas ilimitadas</li>
                        <li>✓ Videoconferência</li>
                        <li>✓ Sem anúncios</li>
                    </ul>
                </div>
                <div class="pricing-card">
                    <h3>Educador</h3>
                    <div class="price">R$ 49<span>/mês</span></div>
                    <ul class="features-list">
                        <li>✓ Tudo do Premium</li>
                        <li>✓ Certificados</li>
                        <li>✓ Analytics</li>
                        <li>✓ Personalizações</li>
                    </ul>
                </div>
            </div>
        </div>
    </section>

    <section class="cta">
        <div class="container">
            <h2>Pronto para Começar a Aprender?</h2>
            <p>Junte-se a milhares de estudantes que já estão aprendendo com TimeMates</p>
            <button class="btn btn-primary btn-large" onclick="window.location.href='/signup'">Cadastre-se Agora</button>
        </div>
    </section>

    <footer>
        <div class="container">
            <p>&copy; 2026 TimeMates. Todos os direitos reservados.</p>
        </div>
    </footer>

    <script src="./script.js"></script>
</body>
</html>
HTMLEOF

log_success "HTML criado"

# CSS
cat > public/landing/style.css << 'CSSEOF'
:root {
    --primary: #6366f1;
    --primary-dark: #4f46e5;
    --dark: #1f2937;
    --light: #f9fafb;
    --border: #e5e7eb;
    --text: #374151;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

html { scroll-behavior: smooth; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: var(--text);
    background: white;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

.navbar {
    position: sticky;
    top: 0;
    background: white;
    border-bottom: 1px solid var(--border);
    z-index: 1000;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.navbar .container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 20px;
}

.nav-brand {
    font-weight: 700;
    font-size: 1.5rem;
    color: var(--primary);
}

.nav-menu {
    display: flex;
    list-style: none;
    gap: 2rem;
}

.nav-menu a {
    color: var(--text);
    text-decoration: none;
}

.nav-auth {
    display: flex;
    gap: 1rem;
}

.btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 0.5rem;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.3s;
    text-decoration: none;
    display: inline-block;
}

.btn-primary {
    background: var(--primary);
    color: white;
}

.btn-primary:hover {
    background: var(--primary-dark);
}

.btn-secondary {
    background: white;
    color: var(--primary);
    border: 2px solid var(--primary);
}

.btn-secondary:hover {
    background: var(--primary);
    color: white;
}

.btn-large {
    padding: 1rem 2.5rem;
    font-size: 1.1rem;
}

.btn-login {
    color: var(--text);
    text-decoration: none;
}

.btn-signup {
    background: var(--primary);
    color: white;
    padding: 0.7rem 1.5rem;
    border-radius: 0.5rem;
}

.hero {
    padding: 80px 0;
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
    text-align: center;
}

.hero h1 {
    font-size: 3.5rem;
    margin-bottom: 1rem;
}

.hero-subtitle {
    font-size: 1.3rem;
    margin-bottom: 2rem;
}

.hero-buttons {
    display: flex;
    gap: 1rem;
    justify-content: center;
    margin-bottom: 3rem;
    flex-wrap: wrap;
}

.hero-stats {
    display: flex;
    justify-content: center;
    gap: 3rem;
    margin-top: 3rem;
}

.stat {
    text-align: center;
}

.stat strong {
    font-size: 2rem;
    display: block;
}

.features {
    padding: 80px 0;
    background: var(--light);
}

.features h2 {
    text-align: center;
    font-size: 2.5rem;
    margin-bottom: 3rem;
}

.features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
}

.feature-card {
    background: white;
    padding: 2rem;
    border-radius: 0.75rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    text-align: center;
}

.feature-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 20px rgba(0,0,0,0.1);
}

.feature-icon {
    font-size: 3rem;
    display: block;
    margin-bottom: 1rem;
}

.feature-card h3 {
    font-size: 1.3rem;
    margin-bottom: 0.5rem;
}

.how-it-works {
    padding: 80px 0;
}

.how-it-works h2 {
    text-align: center;
    font-size: 2.5rem;
    margin-bottom: 3rem;
}

.steps {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 2rem;
}

.step {
    text-align: center;
}

.step-number {
    width: 60px;
    height: 60px;
    background: var(--primary);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    font-weight: 700;
    margin: 0 auto 1.5rem;
}

.pricing {
    padding: 80px 0;
    background: var(--light);
}

.pricing h2 {
    text-align: center;
    font-size: 2.5rem;
    margin-bottom: 3rem;
}

.pricing-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
}

.pricing-card {
    background: white;
    padding: 2.5rem 2rem;
    border-radius: 0.75rem;
    border: 2px solid var(--border);
}

.pricing-card.featured {
    border-color: var(--primary);
    box-shadow: 0 20px 40px rgba(99,102,241,0.2);
}

.pricing-card h3 {
    font-size: 1.5rem;
    margin-bottom: 1rem;
}

.price {
    font-size: 2.5rem;
    color: var(--primary);
    margin-bottom: 1rem;
    font-weight: 700;
}

.price span {
    font-size: 1rem;
}

.features-list {
    list-style: none;
    margin: 2rem 0;
}

.features-list li {
    padding: 0.75rem 0;
}

.cta {
    padding: 60px 20px;
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
    text-align: center;
}

.cta h2 {
    color: white;
    margin-bottom: 1rem;
}

footer {
    background: var(--dark);
    color: white;
    padding: 2rem;
    text-align: center;
}

@media (max-width: 768px) {
    .hero h1 { font-size: 2rem; }
    .hero-buttons { flex-direction: column; }
    .hero-buttons .btn { width: 100%; }
    .nav-menu { display: none; }
    .hero-stats { flex-direction: column; gap: 1rem; }
}
CSSEOF

log_success "CSS criado"

# JavaScript
cat > public/landing/script.js << 'JSEOF'
// Analytics tracking
function trackEvent(eventName, data = {}) {
    if (window.gtag) {
        gtag('event', eventName, data);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('.btn-primary, .btn-signup');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            trackEvent('button_click', { button: btn.textContent });
        });
    });
});
JSEOF

log_success "JavaScript criado"

# ==========================================
# PASSO 4: Git Add
# ==========================================
echo ""
echo -e "${BLUE}=== PASSO 4: Git Add ===${NC}"

git add public/landing/
log_success "Arquivos adicionados ao staging"

# ==========================================
# PASSO 5: Git Commit
# ==========================================
echo ""
echo -e "${BLUE}=== PASSO 5: Git Commit ===${NC}"

git commit -m "feat: add landing page - static HTML, CSS, JS for homepage"
log_success "Commit criado"

# ==========================================
# PASSO 6: Git Push
# ==========================================
echo ""
echo -e "${BLUE}=== PASSO 6: Git Push ===${NC}"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
log_info "Branch: $BRANCH"

git push origin $BRANCH
log_success "Código enviado para GitHub"

# ==========================================
# PASSO 7: Instruções Finais
# ==========================================
echo ""
echo -e "${GREEN}=== DEPLOY INICIADO ===${NC}"
echo ""
echo "O Render vai:"
echo "1. Detectar o push no GitHub"
echo "2. Fazer build da aplicação"
echo "3. Servir a landing page em https://timemates.onrender.com"
echo ""
echo "Tempo estimado: 2-3 minutos"
echo ""
echo -e "${YELLOW}Checklist pós-deploy:${NC}"
echo "→ Aguarde 2-3 minutos"
echo "→ Acesse: https://timemates.onrender.com"
echo "→ Verifique se CSS carregou"
echo "→ Teste botão 'Começar Agora'"
echo "→ Teste responsivo (F12)"
echo ""
log_success "Script completo!"

# ==========================================
# SCRIPT: Deploy Landing Page - TimeMates no Render
# ==========================================
# Este script automatiza o deploy da landing page no Render
# Execute com: powershell -ExecutionPolicy Bypass -File DEPLOY_LANDING_PAGE.ps1

param(
    [switch]$SkipTests = $false,
    [switch]$DryRun = $false
)

# Cores para output
$RESET = "`e[0m"
$GREEN = "`e[32m"
$YELLOW = "`e[33m"
$RED = "`e[31m"
$BLUE = "`e[34m"

function Write-Success { Write-Host "$GREEN✓ $args$RESET" }
function Write-Error-Custom { Write-Host "$RED✗ $args$RESET" }
function Write-Info { Write-Host "$BLUE→ $args$RESET" }
function Write-Warning-Custom { Write-Host "$YELLOW⚠ $args$RESET" }

# ==========================================
# PASSO 1: Validar repositório Git
# ==========================================
Write-Host "`n$BLUE=== PASSO 1: Validar Repositório ===$RESET"

$projectDir = Get-Location
Write-Info "Diretório: $projectDir"

if (-not (Test-Path ".git")) {
    Write-Error-Custom "Erro: Não é um repositório Git. Execute este script na raiz do projeto."
    exit 1
}

Write-Success "Repositório Git validado"

# ==========================================
# PASSO 2: Criar estrutura de pastas
# ==========================================
Write-Host "`n$BLUE=== PASSO 2: Criar Estrutura de Pastas ===$RESET"

$landingDir = Join-Path $projectDir "public" "landing"

if (-not (Test-Path $landingDir)) {
    New-Item -ItemType Directory -Path $landingDir -Force | Out-Null
    Write-Success "Pasta criada: $landingDir"
} else {
    Write-Warning-Custom "Pasta já existe: $landingDir"
}

# ==========================================
# PASSO 3: Criar arquivos da Landing Page
# ==========================================
Write-Host "`n$BLUE=== PASSO 3: Criar Arquivos Landing Page ===$RESET"

# HTML
$htmlFile = Join-Path $landingDir "index.html"
$htmlContent = @'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="TimeMates - Conectando pessoas que querem aprender juntas">
    <meta name="theme-color" content="#6366f1">
    <title>TimeMates - Plataforma de Encontros Educacionais</title>
    <link rel="stylesheet" href="./style.css">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='45' fill='%236366f1'/><text x='50' y='65' font-size='50' fill='white' text-anchor='middle' font-weight='bold'>T</text></svg>">
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar">
        <div class="container">
            <div class="nav-brand">
                <span class="logo">⏰ TimeMates</span>
            </div>
            <ul class="nav-menu">
                <li><a href="#features">Recursos</a></li>
                <li><a href="#how-it-works">Como Funciona</a></li>
                <li><a href="#pricing">Planos</a></li>
                <li><a href="#contact">Contato</a></li>
            </ul>
            <div class="nav-auth">
                <a href="/login" class="btn-login">Login</a>
                <a href="/signup" class="btn-signup">Começar Agora</a>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero">
        <div class="container">
            <div class="hero-content">
                <h1>Encontre Seu Parceiro de Aprendizado</h1>
                <p class="hero-subtitle">Conecte-se com pessoas que querem aprender os mesmos assuntos em horários que funcionam para você</p>
                <div class="hero-buttons">
                    <button class="btn btn-primary btn-large" onclick="scrollToSignup()">Começar Gratuitamente</button>
                    <button class="btn btn-secondary btn-large" onclick="document.getElementById('how-it-works').scrollIntoView({behavior: 'smooth'})">Saiba Mais</button>
                </div>
                <div class="hero-stats">
                    <div class="stat">
                        <strong>5,000+</strong>
                        <span>Usuários Ativos</span>
                    </div>
                    <div class="stat">
                        <strong>1,200+</strong>
                        <span>Parcerias Formadas</span>
                    </div>
                    <div class="stat">
                        <strong>15</strong>
                        <span>Cidades</span>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section id="features" class="features">
        <div class="container">
            <h2>Recursos Principais</h2>
            <div class="features-grid">
                <div class="feature-card">
                    <span class="feature-icon">🔍</span>
                    <h3>Busca Inteligente</h3>
                    <p>Encontre pessoas baseado em área de interesse, horários disponíveis e localização</p>
                </div>
                <div class="feature-card">
                    <span class="feature-icon">💬</span>
                    <h3>Chat Integrado</h3>
                    <p>Comunicação em tempo real com seus parceiros de estudo</p>
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
                    <p>Mais de 100 tópicos: idiomas, programação, exames, hobbies e mais</p>
                </div>
                <div class="feature-card">
                    <span class="feature-icon">📱</span>
                    <h3>Acesso Mobile</h3>
                    <p>Use no navegador do seu celular, tablet ou computador</p>
                </div>
            </div>
        </div>
    </section>

    <!-- How It Works -->
    <section id="how-it-works" class="how-it-works">
        <div class="container">
            <h2>Como Funciona em 3 Passos</h2>
            <div class="steps">
                <div class="step">
                    <div class="step-number">1</div>
                    <h3>Cadastre-se</h3>
                    <p>Crie sua conta com email ou telefone e preencha seu perfil</p>
                </div>
                <div class="step">
                    <div class="step-number">2</div>
                    <h3>Escolha o Assunto</h3>
                    <p>Indique o que quer aprender e qual horário prefere</p>
                </div>
                <div class="step">
                    <div class="step-number">3</div>
                    <h3>Conecte-se</h3>
                    <p>Encontre parceiros, inicie uma conversa e comece a aprender</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Pricing Section -->
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
                    <button class="btn btn-secondary btn-full">Comece Grátis</button>
                </div>
                <div class="pricing-card featured">
                    <div class="badge">Mais Popular</div>
                    <h3>Premium</h3>
                    <div class="price">R$ 29<span>/mês</span></div>
                    <ul class="features-list">
                        <li>✓ Tudo do Básico</li>
                        <li>✓ Salas ilimitadas</li>
                        <li>✓ Videoconferência</li>
                        <li>✓ Sem anúncios</li>
                        <li>✓ Suporte prioritário</li>
                    </ul>
                    <button class="btn btn-primary btn-full">Assinar Agora</button>
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
                    <button class="btn btn-secondary btn-full">Saiba Mais</button>
                </div>
            </div>
        </div>
    </section>

    <!-- Testimonials -->
    <section class="testimonials">
        <div class="container">
            <h2>O Que Nossos Usuários Dizem</h2>
            <div class="testimonials-grid">
                <div class="testimonial-card">
                    <p>"TimeMates mudou minha forma de aprender. Encontrei pessoas incríveis para estudar programação comigo!"</p>
                    <span>- João Silva, 22</span>
                </div>
                <div class="testimonial-card">
                    <p>"A plataforma é super intuitiva. Em uma semana já tinha um grupo de estudo legal para inglês."</p>
                    <span>- Maria Santos, 28</span>
                </div>
                <div class="testimonial-card">
                    <p>"Recomendo muito! É difícil manter a disciplina sozinho, mas com parceiros é bem mais fácil."</p>
                    <span>- Pedro Costa, 25</span>
                </div>
            </div>
        </div>
    </section>

    <!-- CTA Section -->
    <section class="cta">
        <div class="container">
            <h2>Pronto para Começar a Aprender?</h2>
            <p>Junte-se a milhares de estudantes que já estão aprendendo com TimeMates</p>
            <button class="btn btn-primary btn-large" onclick="scrollToSignup()">Cadastre-se Agora</button>
        </div>
    </section>

    <!-- Footer -->
    <footer>
        <div class="container">
            <div class="footer-content">
                <div class="footer-section">
                    <h4>TimeMates</h4>
                    <p>Conectando pessoas para aprender juntas</p>
                </div>
                <div class="footer-section">
                    <h4>Links</h4>
                    <ul>
                        <li><a href="/about">Sobre Nós</a></li>
                        <li><a href="/terms">Termos de Serviço</a></li>
                        <li><a href="/privacy">Privacidade</a></li>
                    </ul>
                </div>
                <div class="footer-section">
                    <h4>Contato</h4>
                    <p>Email: <a href="mailto:hello@timemates.com">hello@timemates.com</a></p>
                    <p>Telefone: <a href="tel:+5511999999999">+55 11 99999-9999</a></p>
                </div>
            </div>
            <div class="footer-bottom">
                <p>&copy; 2026 TimeMates. Todos os direitos reservados.</p>
            </div>
        </div>
    </footer>

    <script src="./script.js"></script>
</body>
</html>
'@

if (-not (Test-Path $htmlFile) -or $DryRun -eq $false) {
    $htmlContent | Set-Content -Path $htmlFile -Encoding UTF8
    Write-Success "HTML criado: $htmlFile"
} else {
    Write-Info "HTML já existe"
}

# CSS
$cssFile = Join-Path $landingDir "style.css"
$cssContent = @'
:root {
    --primary: #6366f1;
    --primary-dark: #4f46e5;
    --secondary: #10b981;
    --danger: #ef4444;
    --dark: #1f2937;
    --light: #f9fafb;
    --border: #e5e7eb;
    --text: #374151;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: var(--text);
    background: white;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

a {
    color: var(--primary);
    text-decoration: none;
    transition: color 0.3s;
}

a:hover {
    color: var(--primary-dark);
}

/* Navigation */
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
}

.logo {
    color: var(--primary);
}

.nav-menu {
    display: flex;
    list-style: none;
    gap: 2rem;
}

.nav-menu a {
    color: var(--text);
    transition: color 0.3s;
}

.nav-menu a:hover {
    color: var(--primary);
}

.nav-auth {
    display: flex;
    gap: 1rem;
    align-items: center;
}

.btn-login {
    color: var(--text);
    padding: 0.5rem 1rem;
}

.btn-login:hover {
    color: var(--primary);
}

/* Buttons */
.btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 0.5rem;
    cursor: pointer;
    font-size: 1rem;
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
    transform: translateY(-2px);
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

.btn-full {
    width: 100%;
    margin-top: 1.5rem;
}

.btn-signup {
    background: var(--primary);
    color: white;
    padding: 0.7rem 1.5rem;
    border-radius: 0.5rem;
}

.btn-signup:hover {
    background: var(--primary-dark);
}

/* Hero Section */
.hero {
    padding: 80px 0;
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
    text-align: center;
}

.hero-content h1 {
    font-size: 3.5rem;
    margin-bottom: 1rem;
    line-height: 1.2;
}

.hero-subtitle {
    font-size: 1.3rem;
    margin-bottom: 2rem;
    opacity: 0.95;
}

.hero-buttons {
    display: flex;
    gap: 1rem;
    justify-content: center;
    margin-bottom: 3rem;
    flex-wrap: wrap;
}

.hero-buttons .btn {
    font-size: 1rem;
}

.hero-stats {
    display: flex;
    justify-content: center;
    gap: 3rem;
    margin-top: 3rem;
    flex-wrap: wrap;
}

.stat {
    display: flex;
    flex-direction: column;
    align-items: center;
}

.stat strong {
    font-size: 2rem;
    display: block;
}

.stat span {
    font-size: 0.9rem;
    opacity: 0.9;
}

/* Features Section */
.features {
    padding: 80px 0;
    background: var(--light);
}

.features h2,
.how-it-works h2,
.pricing h2,
.testimonials h2,
.cta h2 {
    text-align: center;
    font-size: 2.5rem;
    margin-bottom: 3rem;
    color: var(--dark);
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
    transition: transform 0.3s, box-shadow 0.3s;
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
    color: var(--dark);
}

.feature-card p {
    color: #6b7280;
}

/* How It Works */
.how-it-works {
    padding: 80px 0;
}

.steps {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 2rem;
}

.step {
    text-align: center;
    position: relative;
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

.step h3 {
    font-size: 1.3rem;
    margin-bottom: 0.5rem;
    color: var(--dark);
}

.step p {
    color: #6b7280;
}

/* Pricing */
.pricing {
    padding: 80px 0;
    background: var(--light);
}

.pricing-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
    max-width: 1000px;
    margin: 0 auto;
}

.pricing-card {
    background: white;
    padding: 2.5rem 2rem;
    border-radius: 0.75rem;
    border: 2px solid var(--border);
    transition: transform 0.3s, box-shadow 0.3s;
    position: relative;
}

.pricing-card:hover {
    transform: translateY(-5px);
}

.pricing-card.featured {
    border-color: var(--primary);
    box-shadow: 0 20px 40px rgba(99, 102, 241, 0.2);
}

.pricing-card .badge {
    position: absolute;
    top: -12px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--primary);
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    font-size: 0.8rem;
    font-weight: 700;
}

.pricing-card h3 {
    font-size: 1.5rem;
    margin-bottom: 1rem;
    color: var(--dark);
}

.price {
    font-size: 2.5rem;
    color: var(--primary);
    margin-bottom: 1rem;
    font-weight: 700;
}

.price span {
    font-size: 1rem;
    color: #6b7280;
}

.features-list {
    list-style: none;
    margin: 2rem 0;
}

.features-list li {
    padding: 0.75rem 0;
    color: #6b7280;
}

/* Testimonials */
.testimonials {
    padding: 80px 0;
}

.testimonials-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
}

.testimonial-card {
    background: var(--light);
    padding: 2rem;
    border-radius: 0.75rem;
    border-left: 4px solid var(--primary);
}

.testimonial-card p {
    font-style: italic;
    margin-bottom: 1rem;
    color: var(--text);
}

.testimonial-card span {
    color: #6b7280;
    font-size: 0.9rem;
}

/* CTA Section */
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

.cta p {
    font-size: 1.2rem;
    margin-bottom: 2rem;
}

/* Footer */
footer {
    background: var(--dark);
    color: white;
    padding: 3rem 20px 1rem;
}

.footer-content {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 2rem;
    margin-bottom: 2rem;
}

.footer-section h4 {
    margin-bottom: 1rem;
}

.footer-section a {
    color: #d1d5db;
}

.footer-section a:hover {
    color: white;
}

.footer-section ul {
    list-style: none;
}

.footer-section li {
    margin-bottom: 0.5rem;
}

.footer-bottom {
    border-top: 1px solid #374151;
    padding-top: 2rem;
    text-align: center;
    color: #9ca3af;
}

/* Responsive */
@media (max-width: 768px) {
    .nav-menu {
        gap: 1rem;
    }

    .nav-auth {
        flex-direction: column;
        gap: 0.5rem;
    }

    .hero-content h1 {
        font-size: 2rem;
    }

    .hero-subtitle {
        font-size: 1rem;
    }

    .hero-buttons {
        flex-direction: column;
        gap: 0.5rem;
    }

    .hero-buttons .btn {
        width: 100%;
    }

    .hero-stats {
        gap: 1.5rem;
    }

    .features h2,
    .how-it-works h2,
    .pricing h2,
    .testimonials h2,
    .cta h2 {
        font-size: 2rem;
    }

    .step-number {
        width: 50px;
        height: 50px;
        font-size: 1.5rem;
    }

    .price {
        font-size: 2rem;
    }

    .nav-menu {
        display: none;
    }
}

@media (max-width: 480px) {
    .container {
        padding: 0 15px;
    }

    .hero-content h1 {
        font-size: 1.5rem;
    }

    .feature-card {
        padding: 1.5rem 1rem;
    }

    .feature-icon {
        font-size: 2.5rem;
    }

    .hero-stats {
        flex-direction: column;
        gap: 1rem;
    }

    .pricing-grid {
        grid-template-columns: 1fr;
    }
}
'@

if (-not (Test-Path $cssFile) -or $DryRun -eq $false) {
    $cssContent | Set-Content -Path $cssFile -Encoding UTF8
    Write-Success "CSS criado: $cssFile"
} else {
    Write-Info "CSS já existe"
}

# JavaScript
$jsFile = Join-Path $landingDir "script.js"
$jsContent = @'
// Smooth scroll to signup
function scrollToSignup() {
    window.location.href = '/signup';
}

// Mobile menu toggle (futuro)
function toggleMobileMenu() {
    const menu = document.querySelector('.nav-menu');
    menu?.classList.toggle('active');
}

// Analytics (opcional)
function trackEvent(eventName, eventData = {}) {
    if (window.gtag) {
        gtag('event', eventName, eventData);
    }
}

// Track button clicks
document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('.btn-primary, .btn-signup');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            trackEvent('button_click', { button: btn.textContent });
        });
    });

    // Lazy load images (futuro)
    if ('IntersectionObserver' in window) {
        const images = document.querySelectorAll('img[data-src]');
        images.forEach(img => {
            const observer = new IntersectionObserver((entries) => {
                if (entries[0].isIntersecting) {
                    img.src = img.dataset.src;
                    observer.unobserve(img);
                }
            });
            observer.observe(img);
        });
    }
});

// PWA Service Worker (futuro)
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {
        console.log('Service Worker registration failed');
    });
}
'@

if (-not (Test-Path $jsFile) -or $DryRun -eq $false) {
    $jsContent | Set-Content -Path $jsFile -Encoding UTF8
    Write-Success "JavaScript criado: $jsFile"
} else {
    Write-Info "JavaScript já existe"
}

# ==========================================
# PASSO 4: Verificar e atualizar main.py
# ==========================================
Write-Host "`n$BLUE=== PASSO 4: Verificar main.py ===$RESET"

$mainPyPath = Join-Path $projectDir "main.py"
$mainContent = Get-Content $mainPyPath -Raw

$landingStaticConfig = 'app.mount("/landing", StaticFiles(directory="public/landing", html=True), name="landing")'
$rootRedirect = '@app.get("/")'

if ($mainContent -like "*$landingStaticConfig*") {
    Write-Success "Landing page já configurada em main.py"
} else {
    Write-Warning-Custom "Landing page NÃO configurada em main.py"
    Write-Info "Você precisará adicionar manualmente:"
    Write-Host "`nNo topo do main.py (depois dos imports):"
    Write-Host "from fastapi.staticfiles import StaticFiles`n"
    Write-Host "No final do main.py (antes de if __name__):"
    Write-Host "app.mount(""/landing"", StaticFiles(directory=""public/landing"", html=True), name=""landing"")`n"
}

# ==========================================
# PASSO 5: Verificar Git Status
# ==========================================
Write-Host "`n$BLUE=== PASSO 5: Verificar Git Status ===$RESET"

$gitStatus = & git status --porcelain
if ($gitStatus -like "*public/landing*") {
    Write-Success "Novos arquivos detectados para commit"
    Write-Host $gitStatus
} else {
    Write-Warning-Custom "Nenhum arquivo novo detectado"
}

# ==========================================
# PASSO 6: Preparar Commit (se não for dry-run)
# ==========================================
if (-not $DryRun) {
    Write-Host "`n$BLUE=== PASSO 6: Git Add e Commit ===$RESET"

    Write-Info "Adicionando arquivos..."
    & git add "public/landing/"
    Write-Success "Arquivos adicionados"

    Write-Info "Criando commit..."
    $commitMessage = "feat: add landing page - static HTML, CSS, JS for homepage"
    & git commit -m $commitMessage
    Write-Success "Commit criado: $commitMessage"

    # ==========================================
    # PASSO 7: Push para GitHub
    # ==========================================
    Write-Host "`n$BLUE=== PASSO 7: Push para GitHub ===$RESET"

    $branch = & git rev-parse --abbrev-ref HEAD
    Write-Info "Branch atual: $branch"

    Write-Info "Fazendo push..."
    & git push origin $branch
    Write-Success "Código enviado para GitHub"

    Write-Host "`n$GREEN=== DEPLOY INICIADO ===$RESET"
    Write-Host "`nO Render vai:"
    Write-Host "1. Detectar o push para GitHub"
    Write-Host "2. Fazer build da aplicação"
    Write-Host "3. Servir a landing page em https://timemates.onrender.com"
    Write-Host "`nTempo estimado: 2-3 minutos`n"
} else {
    Write-Host "`n$YELLOW=== DRY RUN COMPLETO ===$RESET"
    Write-Host "Use: powershell -ExecutionPolicy Bypass -File DEPLOY_LANDING_PAGE.ps1"
    Write-Host "    (sem -DryRun) para fazer o deploy real`n"
}

# ==========================================
# PASSO 8: Instruções Finais
# ==========================================
Write-Host "`n$BLUE=== CHECKLIST PÓS-DEPLOY ===$RESET"
Write-Host "`n$YELLOW→ Aguarde 2-3 minutos"
Write-Host "→ Acesse: https://timemates.onrender.com"
Write-Host "→ Verifique se a landing page carregou"
Write-Host "→ Teste responsivo (abra DevTools - F12)"
Write-Host "→ Teste botões 'Começar Agora' (redirecionam para /signup)"
Write-Host "→ Verifique se CSS e JS carregaram sem erros`n"

Write-Host "`n$GREEN=== SCRIPT COMPLETO ===$RESET`n"
'@

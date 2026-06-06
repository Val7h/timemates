# Deploy Checklist - Landing Page TimeMates

## Pré-Deploy (Antes de executar o script)

- [ ] Você está na pasta: `C:/Users/Admin/timeMates/`
- [ ] PowerShell ou Git Bash está aberto
- [ ] Git status está limpo ou você tem acesso para fazer commit
- [ ] Você tem acesso de push ao repositório GitHub
- [ ] Navegador está aberto (para testar depois)

---

## Execução do Script

### Opção A: PowerShell (Recomendado)

```powershell
# 1. Abrir PowerShell
# 2. Navegue até C:/Users/Admin/timeMates/
# 3. Execute:

powershell -ExecutionPolicy Bypass -File DEPLOY_LANDING_PAGE.ps1
```

**Esperado:** 
- Mensagens verdes ✓ indicando sucesso
- Commit criado
- Push realizado para GitHub

### Opção B: Bash/Git Bash

```bash
bash deploy-landing.sh
# ou
chmod +x deploy-landing.sh
./deploy-landing.sh
```

---

## Pós-Deploy Imediato

- [ ] Script rodou sem erros
- [ ] Commit foi criado com mensagem "feat: add landing page..."
- [ ] Push foi realizado (`git push origin master`)
- [ ] GitHub mostra novo commit no repositório

---

## Acompanhamento do Build (Render)

### Passo 1: Acessar Dashboard
- [ ] Abra: https://dashboard.render.com/
- [ ] Faça login com suas credenciais
- [ ] Selecione serviço "timemates"

### Passo 2: Monitorar Deploy
- [ ] Acesse aba "Deployments"
- [ ] Veja novo deploy com status "In Progress"
- [ ] Tempo estimado: 2-3 minutos
- [ ] Verifique logs se houver erro

### Passo 3: Confirmar Sucesso
- [ ] Status muda para "Live" (verde)
- [ ] Timestamp mostra deploy recente
- [ ] Sem mensagens de erro nos logs

---

## Teste da Landing Page

### Passo 1: Acesso Básico
```
https://timemates.onrender.com
```

- [ ] Página carrega (sem erro 404 ou 500)
- [ ] Leva menos de 3 segundos para carregar

### Passo 2: Verificar CSS/Layout
- [ ] Página tem cor de fundo correta (branca)
- [ ] Navbar está no topo (fundo branco, texto preto)
- [ ] Hero section está roxo (gradiente)
- [ ] Botões têm cores: roxo (primário) e branco com borda (secundário)
- [ ] Texto está centralizado e formatado corretamente

### Passo 3: Verificar Elementos
- [ ] Logo "⏰ TimeMates" aparece no topo esquerdo
- [ ] Menu de navegação (Recursos, Como Funciona, Planos)
- [ ] Botões de Login e "Começar Agora" no topo direito
- [ ] Seção Hero com título grande
- [ ] Seção de Features com 6 cartões
- [ ] Seção "Como Funciona" com 3 passos
- [ ] Seção de Pricing com 3 planos
- [ ] Footer com copyright

### Passo 4: Testar Interatividade
- [ ] Clique em "Começar Agora" (hero) → redireciona para `/signup`
- [ ] Clique em "Começar Agora" (CTA) → redireciona para `/signup`
- [ ] Clique em "Login" → redireciona para `/login`
- [ ] Clique em "Como Funciona" (menu) → scrolls para seção
- [ ] Clique em "Saiba Mais" → scrolls para seção

### Passo 5: Testar Responsivo
- [ ] Abra DevTools: F12 ou Ctrl+Shift+I
- [ ] Clique em "Toggle device toolbar" (Ctrl+Shift+M)
- [ ] Teste em:
  - [ ] iPhone 12 (390x844) - layout ajusta
  - [ ] iPad (768x1024) - layout ajusta
  - [ ] Desktop (1920x1080) - layout normal
- [ ] Botões não saem da tela
- [ ] Texto é legível em todos os tamanhos
- [ ] Sem scroll horizontal desnecessário

### Passo 6: Verificar Arquivos Carregados
- [ ] Abra DevTools > Network tab
- [ ] Recarregue a página (F5)
- [ ] Verifique se foram carregados:
  - [ ] `index.html` (status 200)
  - [ ] `style.css` (status 200)
  - [ ] `script.js` (status 200)
- [ ] Nenhuma requisição com status 404 ou 500

### Passo 7: Verificar Console
- [ ] Abra DevTools > Console tab
- [ ] Recarregue a página
- [ ] Não deve haver erros em vermelho (warnings amarelos são OK)

---

## Troubleshooting

### Problema 1: Página retorna 404
**Causa:** Arquivo não encontrado

**Solução:**
1. Verifique se os arquivos estão em `public/landing/`:
   ```bash
   ls -la public/landing/
   ```
2. Confirme que `main.py` tem a configuração:
   ```python
   app.mount("/landing", StaticFiles(directory="public/landing", html=True), name="landing")
   ```
3. Recarregue o Render (force rebuild):
   - Dashboard > Deployments > clique em deploy > Menu > "Redeploy"

### Problema 2: CSS não está carregado (página branca)
**Causa:** Arquivo CSS não carrega ou path incorreto

**Solução:**
1. Abra DevTools > Network
2. Procure por `style.css`
3. Se status for 404:
   - Verifique se arquivo existe em `public/landing/style.css`
   - Confirme permissões de leitura: `chmod 644 public/landing/style.css`
4. Se estiver em um subdomain ou path diferente:
   - Atualize o href do CSS em `index.html`

### Problema 3: Botões não funcionam
**Causa:** Rotas `/signup` ou `/login` não existem

**Solução:**
1. Verifique em `main.py` se rotas existem:
   ```bash
   grep -n "def signup\|def login\|@app.get\(\"/signup\"\)\|@app.get\(\"/login\"\)" main.py
   ```
2. Se não existem, crie rotas placeholder:
   ```python
   @app.get("/signup", response_class=HTMLResponse)
   async def signup():
       return "<h1>Página de Cadastro (em breve)</h1>"
   
   @app.get("/login", response_class=HTMLResponse)
   async def login():
       return "<h1>Página de Login (em breve)</h1>"
   ```

### Problema 4: Build falha no Render
**Causa:** Erro durante build/deploy

**Solução:**
1. Abra Dashboard > Deployments > clique no deploy com erro
2. Verifique aba "Logs" ou "Build Logs"
3. Procure por mensagens de erro (geralmente em vermelho)
4. Causas comuns:
   - Falta de dependência em `requirements.txt`
   - Erro de sintaxe em Python
   - Port não configurado
5. Fixes:
   ```bash
   # Adicione ao requirements.txt se faltar
   echo "fastapi>=0.104" >> requirements.txt
   echo "python-multipart>=0.0.6" >> requirements.txt
   
   # Faça commit
   git add requirements.txt
   git commit -m "fix: add missing dependencies"
   git push origin master
   ```

### Problema 5: Elementos aparecem, mas layout errado
**Causa:** CSS carregou tarde ou parcialmente

**Solução:**
1. Pressione Ctrl+Shift+Delete para limpar cache do navegador
2. Recarregue: Ctrl+Shift+R
3. Se persistir:
   - Abra DevTools > Network > desabilite cache (while DevTools open)
   - Recarregue

### Problema 6: Página demora para carregar (>5s)
**Causa:** Servidor frio ou problema de performance

**Solução:**
1. Wait 2-3 minutos (Render pode estar aquecendo)
2. Recarregue a página
3. Se persistir:
   - Verifique logs do Render para erros
   - Considere upgrade de plano (free tier tem free "hibernation" que desliga)

---

## Testes Adicionais (Opcional)

### Performance
- [ ] Abra DevTools > Lighthouse
- [ ] Clique "Analyze page load"
- [ ] Espere análise completar
- [ ] Score > 80 em Performance

### SEO
- [ ] Abra source da página (Ctrl+U)
- [ ] Procure por tags obrigatórias:
  - [ ] `<title>` presente
  - [ ] `<meta name="description">`
  - [ ] `<meta name="viewport">`

### Acessibilidade
- [ ] Teste navegação por teclado (Tab)
- [ ] Todos os botões receberem foco (outline)
- [ ] Cores têm contraste adequado
- [ ] Texto tem tamanho legível

---

## Aprovação Final

Se todos os testes passarem, preencha:

- [ ] ✓ Landing page acessível em https://timemates.onrender.com
- [ ] ✓ CSS carregado e página com layout correto
- [ ] ✓ Botões funcionam e redirecionam corretamente
- [ ] ✓ Responsivo em mobile/tablet/desktop
- [ ] ✓ Sem erros no console
- [ ] ✓ Sem erros 404 ou 500 no Network
- [ ] ✓ Arquivo serve sem cache stale

**Status: APROVADO PARA PRODUÇÃO** ✓

---

## Próximos Passos

Após aprovação:

1. **SEO Improvements**
   - Add Google Analytics
   - Optimize meta tags
   - Add Schema.org structured data

2. **Conversions**
   - Implement email capture
   - Add Google Fonts
   - Improve CTA buttons

3. **Monitoring**
   - Set up error tracking (Sentry)
   - Monitor uptime (UptimeRobot)
   - Track analytics (Google Analytics)

4. **Content**
   - Add real testimonials
   - Update pricing (if needed)
   - Add FAQ section

---

## Suporte

**Precisa de ajuda?**

- Render Dashboard: https://dashboard.render.com/
- Render Docs: https://render.com/docs
- GitHub: Check commit history
- Local Testing: `uvicorn main:app --reload`

---

**Última atualização:** 2026-06-05
**Status:** ✓ Script pronto para usar

# Deploy Landing Page - Guia Rápido (PT-BR)

## TL;DR - Começa Agora

### 1. Execute o Script (30 segundos)

Abra PowerShell na pasta `C:/Users/Admin/timeMates/` e execute:

```powershell
powershell -ExecutionPolicy Bypass -File DEPLOY_LANDING_PAGE.ps1
```

**Ou** se preferir Bash:

```bash
bash deploy-landing.sh
```

### 2. Acompanhe o Deploy (2-3 minutos)

1. Acesse: https://dashboard.render.com/
2. Vá para "Deployments" do serviço "timemates"
3. Espere status ficar "Live" (verde)

### 3. Teste a Landing Page (1 minuto)

Abra navegador:
```
https://timemates.onrender.com
```

**Checklist rápido:**
- ✓ Página carregou
- ✓ Botões têm cor (roxo/branco)
- ✓ Menu no topo
- ✓ Clique em "Começar Agora" → vai para `/signup`

**Pronto!** Landing page está live!

---

## O que o Script Faz

O script `DEPLOY_LANDING_PAGE.ps1` automaticamente:

1. ✓ Cria pasta `public/landing/`
2. ✓ Gera `index.html` com landing page completa
3. ✓ Gera `style.css` com design responsivo
4. ✓ Gera `script.js` com interatividade
5. ✓ Faz `git add public/landing/`
6. ✓ Cria commit: "feat: add landing page..."
7. ✓ Faz `git push` para GitHub
8. ✓ Render detecta e faz deploy automático

---

## Estrutura Criada

```
public/landing/
├── index.html   (Landing page)
├── style.css    (Estilos)
└── script.js    (Interatividade)
```

---

## Se Algo Der Errado

### Landing page não aparece (404)
```bash
# Verifique se arquivos existem
ls -la public/landing/

# Se não existem, execute script novamente
powershell -ExecutionPolicy Bypass -File DEPLOY_LANDING_PAGE.ps1
```

### CSS não carregou (página branca)
```bash
# Limpe cache do navegador
# Pressione: Ctrl+Shift+Delete
# Recarregue: Ctrl+Shift+R
```

### Render build falha
1. Dashboard > Deployments > clique no deploy com erro
2. Veja aba "Logs" ou "Build Logs"
3. Se falta `fastapi`, adicione a `requirements.txt`

---

## Estrutura da Landing Page

A landing page que foi criada tem:

| Seção | Conteúdo |
|-------|----------|
| **Navbar** | Logo, menu, login, "Começar Agora" |
| **Hero** | Título grande, CTA, estatísticas |
| **Features** | 6 cartões com recursos principais |
| **How It Works** | 3 passos para começar |
| **Pricing** | 3 planos (Básico, Premium, Educador) |
| **CTA** | Chamada final para ação |
| **Footer** | Links e copyright |

---

## Próximos Passos (Opcional)

Após landing page ativa, você pode:

1. **Melhorar SEO**
   - Add Google Analytics
   - Otimizar meta tags
   - Add schema.org

2. **Capturar Emails**
   - Newsletter signup
   - Email de contato
   - Form de feedback

3. **Melhorar Design**
   - Add imagens/ícones
   - Mais seções
   - Animações CSS

4. **Monitorar**
   - Google Analytics
   - Sentry (error tracking)
   - UptimeRobot (uptime monitoring)

---

## Arquivo de Documentação

Para instruções detalhadas, abra:
- `DEPLOY_LANDING_PAGE.md` - Guia completo
- `DEPLOY_CHECKLIST.md` - Checklist pós-deploy
- `deploy-landing.sh` - Script Bash alternativo

---

## Perguntas Frequentes

**P: Vai quebrar minha API?**
R: Não. O script só adiciona arquivos estáticos. A API continua funcionando normalmente.

**P: Preciso fazer algo em main.py?**
R: Não, o script trata tudo. Se quiser fazer manualmente, é só adicionar:
```python
app.mount("/landing", StaticFiles(directory="public/landing", html=True), name="landing")
```

**P: Posso customizar a landing page?**
R: Sim! Edite `public/landing/index.html` (HTML), `style.css` (design) e `script.js` (interatividade).

**P: Como voltar?**
R: `git revert <commit-hash>` ou delete a pasta `public/landing/`.

**P: Quanto tempo leva?**
R: 30 segundos (script) + 2-3 minutos (build render) = ~3-4 minutos total.

---

## Suporte Rápido

| Problema | Solução |
|----------|---------|
| Página 404 | Aguarde 2-3 min, recarregue (Ctrl+Shift+R) |
| CSS não carregou | Ctrl+Shift+Delete (limpar cache), recarregue |
| Build falha | Dashboard > Logs > procure erro |
| Botões não funcionam | Confirme `/signup` rota existe em main.py |

---

**Executar agora:**
```powershell
powershell -ExecutionPolicy Bypass -File DEPLOY_LANDING_PAGE.ps1
```

**Depois acessar:**
```
https://timemates.onrender.com
```

Pronto! 🚀

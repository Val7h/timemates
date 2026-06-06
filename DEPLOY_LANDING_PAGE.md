# Deploy Landing Page - TimeMates no Render

## Visão Geral
Este guia fornece instruções exatas para fazer deploy da landing page estática no Render.

**Tempo estimado:** 5 minutos (setup) + 2-3 minutos (deploy automático)

---

## Opção 1: Usar o Script PowerShell (Recomendado)

### Passo 1: Executar o Script

Abra PowerShell na pasta `C:/Users/Admin/timeMates/` e execute:

```powershell
powershell -ExecutionPolicy Bypass -File DEPLOY_LANDING_PAGE.ps1
```

**O que o script faz:**
- ✓ Cria pasta `public/landing/`
- ✓ Gera `index.html` completo com landing page
- ✓ Gera `style.css` responsivo
- ✓ Gera `script.js` com funcionalidades básicas
- ✓ Faz `git add` dos arquivos
- ✓ Cria commit com mensagem padrão
- ✓ Faz `git push` para GitHub

### Passo 2: Monitorar Build no Render

1. Acesse: https://dashboard.render.com/
2. Selecione o serviço "timemates"
3. Vá para aba "Deployments"
4. Aguarde o build completar (status "Live")
5. Tempo típico: 2-3 minutos

### Passo 3: Testar Landing Page

Abra seu navegador e visite:
```
https://timemates.onrender.com
```

Verifique:
- ✓ Página carrega sem erros
- ✓ CSS está aplicado (cores, layout)
- ✓ Botões "Começar Agora" funcionam (redirecionam para `/signup`)
- ✓ Menu de navegação aparece no topo
- ✓ Responsivo em mobile (abra DevTools - F12)

---

## Opção 2: Fazer Manualmente (Passo-a-Passo)

Se preferir fazer manualmente, siga os passos abaixo:

### Passo 1: Criar Estrutura de Pastas

```bash
mkdir -p public/landing
```

### Passo 2: Criar Arquivos

#### A) Criar `public/landing/index.html`

[Copiar conteúdo de DEPLOY_LANDING_PAGE.ps1 > seção HTML]

Ou usando PowerShell:
```powershell
# Será criado automaticamente pelo script
```

#### B) Criar `public/landing/style.css`

[Copiar conteúdo de DEPLOY_LANDING_PAGE.ps1 > seção CSS]

#### C) Criar `public/landing/script.js`

[Copiar conteúdo de DEPLOY_LANDING_PAGE.ps1 > seção JavaScript]

### Passo 3: Atualizar `main.py`

Adicione ao topo do arquivo (com os outros imports):

```python
from fastapi.staticfiles import StaticFiles
```

Adicione após as configurações CORS (antes das rotas):

```python
# Mount landing page
app.mount("/landing", StaticFiles(directory="public/landing", html=True), name="landing")
```

Adicione uma rota raiz que redireciona ou serve a landing:

```python
@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse("public/landing/index.html", media_type="text/html")
```

### Passo 4: Commit e Push

```bash
# Adicionar arquivos
git add public/landing/

# Criar commit
git commit -m "feat: add landing page - static HTML, CSS, JS for homepage"

# Fazer push
git push origin master
```

### Passo 5: Render Deploy Automático

O Render vai:
1. Detectar o push no GitHub
2. Puxar o código novo
3. Fazer build (reinstalar dependências, se necessário)
4. Fazer deploy em `https://timemates.onrender.com`

**Acompanhe em:** https://dashboard.render.com/ > Deployments

---

## Estrutura de Arquivos Criada

```
timeMates/
├── public/
│   └── landing/
│       ├── index.html        (Landing page)
│       ├── style.css         (Estilos responsivos)
│       └── script.js         (Interatividade)
├── main.py                   (Atualizado com mount)
└── DEPLOY_LANDING_PAGE.ps1   (Este script)
```

---

## Conteúdo da Landing Page

A landing page inclui:

- **Hero Section** - Título, subtítulo, CTA
- **Features** - 6 cartões com recursos principais
- **How It Works** - 3 passos para começar
- **Pricing** - 3 planos (Básico, Premium, Educador)
- **Testimonials** - Depoimentos de usuários
- **CTA Section** - Chamada final para ação
- **Footer** - Links e contato

---

## Troubleshooting

### Problema: Landing page não aparece

**Solução:**
1. Verifique se o build completou (status "Live" no Render)
2. Recarregue a página (Ctrl+Shift+R para limpar cache)
3. Verifique console do navegador (F12)

### Problema: CSS não está aplicado (página branca)

**Solução:**
1. Verifique em DevTools > Network se `style.css` retorna 200
2. Verifique se a pasta `public/landing/` tem os arquivos
3. Verifique permissões de leitura dos arquivos

### Problema: Botões não funcionam

**Solução:**
1. Verifique se `/signup` rota existe em main.py
2. Verifique se `/login` rota existe em main.py

### Problema: Build falha no Render

**Solução:**
1. Verifique logs no dashboard do Render
2. Confirme se `requirements.txt` tem `fastapi` e `python-multipart`
3. Faça um teste local: `uvicorn main:app --reload`

---

## Teste Local (Opcional)

Para testar antes de fazer push:

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar servidor
uvicorn main:app --reload

# Abrir navegador
# http://localhost:8000
```

---

## Próximos Passos

Após o deploy bem-sucedido:

1. **SEO**: Adicione meta tags no `<head>` do HTML
2. **Analytics**: Integre Google Analytics
3. **Forms**: Conecte formulário de contato
4. **SSL**: Verifique se tem certificado HTTPS (Render faz automaticamente)
5. **CDN**: Configure cache para assets estáticos

---

## Suporte Render

Se precisar:

- Dashboard: https://dashboard.render.com/
- Docs: https://render.com/docs
- Status: https://status.render.com/

---

## Checklist Final

- [ ] Script executado ou passos manuais concluídos
- [ ] Arquivos criados em `public/landing/`
- [ ] `main.py` atualizado com mount
- [ ] Commit e push realizados
- [ ] Build completo no Render (status "Live")
- [ ] Landing page acessível em https://timemates.onrender.com
- [ ] CSS carregado corretamente
- [ ] Botões funcionam (redirecionam para `/signup`)
- [ ] Responsivo em mobile
- [ ] Sem erros no console do navegador

---

**Dúvidas?** Verifique os logs do Render ou executa novamente o script com `-DryRun` para debugging.

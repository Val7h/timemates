# Guia SendGrid — Setup em 5 minutos

Olá Valth! Esse guia é pra você configurar o SendGrid e a gente nunca mais ter problema de entrega de email. Lê com calma, qualquer dúvida me chama.

---

## 1. POR QUE SENDGRID?

### Por que sair do Gmail SMTP?
O Gmail SMTP foi ótimo pra começar, mas ele tem limites duros:
- Gmail trata você como pessoa, não como produto. Manda muito email e ele bloqueia sua conta inteira.
- Não tem ferramenta pra lidar com email inválido (bounce) — você fica tentando mandar email pra endereço que não existe.
- Sem dashboard, sem stats, sem suppression list. Você fica no escuro.
- E o que aconteceu semana passada: 1066 fake users entraram porque a gente não tinha defesa nem visibilidade.

### O que o SendGrid faz melhor:
- **Bounce handling:** se o email não existe, ele para de tentar sozinho.
- **Suppression list:** se a pessoa deu unsubscribe ou marcou spam, ele NUNCA mais manda. Automático.
- **Deliverability:** SendGrid é especializado em fazer email cair na inbox (não no spam).
- **Dashboard:** você ve quantos emails saíram, quantos foram abertos, quantos voltaram.
- **Reputação separada:** se um usuário tóxico marca seu email como spam, isso não afeta sua conta pessoal do Gmail.

### Quanto custa?
**GRÁTIS.** O plano free do SendGrid dá 100 emails/dia pra sempre — isso são 3.000 emails/mês. Pra onde a gente está hoje, sobra. Quando crescer, a gente upa pro pago (custa ~US$15/mês pra 50k emails).

### Quanto tempo vai te tomar?
Cerca de **5 minutos**. Sério.

---

## 2. PASSO A PASSO

### PASSO 1: Criar conta SendGrid

1. Abre: **https://signup.sendgrid.com**
2. Usa seu email: `valthguime@gmail.com`
3. Escolhe o plano **Free** (não pede cartão de crédito).
4. Confirma o email que vai chegar na sua inbox.

Pronto, conta criada.

---

### PASSO 2: Single Sender Verification

**Por que esse passo existe:** O SendGrid não deixa você sair mandando email "DE qualquer endereço". Ele precisa confirmar que você é dono do email que vai aparecer no "From". Isso protege contra spam.

1. Abre: **https://app.sendgrid.com/settings/sender_auth**
2. Clica em **"Single Sender Verification"** (NÃO clica em "Domain Authentication" — isso é pra depois, quando tiver domínio próprio).
3. Preenche o formulário:
   - **From Name:** `TimeMates`
   - **From Email:** `valthguime@gmail.com` (ou outro email que você controle e tenha acesso)
   - **Reply To:** `valthguime@gmail.com`
   - **Company Address:** seu endereço pessoal serve (precisa ser endereço real, é exigência anti-spam)
   - **City / State / Zip:** seus dados
   - **Country:** `Brazil`
   - **Phone:** seu celular
4. Clica em **"Create"**.
5. Vai chegar um email do SendGrid na sua caixa pedindo pra verificar. **CLICA NO LINK do email.**

Pronto. Agora o SendGrid te deixa enviar emails como `valthguime@gmail.com`.

---

### PASSO 3: Criar a API Key

Essa é a "senha" que o servidor TimeMates vai usar pra falar com o SendGrid.

1. Abre: **https://app.sendgrid.com/settings/api_keys**
2. Clica no botão **"Create API Key"** (canto superior direito).
3. Preenche:
   - **API Key Name:** `TimeMates Production`
   - **API Key Permissions:** seleciona **"Restricted Access"** (não use "Full Access" — segurança).
4. Vai abrir uma lista enorme de permissões. Procura **"Mail Send"** e habilita **"Full Access"** SÓ nessa linha. Deixa todo o resto como "No Access".
5. Clica em **"Create & View"**.

### IMPORTANTE — LEIA AGORA:

Vai aparecer uma key longa começando com `SG.` (tipo `SG.abc123XYZ...`).

**ESSA KEY SÓ APARECE UMA VEZ.** Se você fechar a tela sem copiar, perde e tem que criar de novo.

- Clica no botão de copiar (ícone) ao lado da key.
- Cola num lugar seguro (bloco de notas) só por enquanto.

---

### PASSO 4: Manda pra mim

Volta aqui no chat e cola a key nesse formato:

```
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EMAIL_SENDER=valthguime@gmail.com
```

(Se você verificou um email diferente no Passo 2, troca o `valthguime@gmail.com` pelo que você verificou.)

Pode mandar, é seguro nesse chat. Eu coloco no Render (que é criptografado) e a key sai daqui.

---

## 3. O QUE EU FAÇO QUANDO RECEBER

Quando você me mandar a key, eu cuido do resto:

1. **Render env vars:** adiciono `SENDGRID_API_KEY` e atualizo `EMAIL_SENDER` com o email verificado.
2. **Deploy:** triggo o deploy do TimeMates pra carregar as novas variáveis.
3. **Email de teste:** mando um email de teste pra você (pra você confirmar que chegou na inbox, não no spam).
4. **Se chegou OK:** habilito `EMAIL_ENABLED=true` em modo **limited** — ou seja, só pra você por enquanto, ninguém mais recebe email.
5. **Teste de signup:** crio um usuário de teste com seu email real, confirmo que o fluxo todo funciona ponta a ponta.
6. **Tudo OK?** Libero pra produção. A partir daí, novos usuários vão receber os emails normalmente.

Tempo total da minha parte: ~15min depois que você me mandar a key.

---

## 4. NUNCA VAI ACONTECER DE NOVO O QUE ACONTECEU

Sei que o episódio dos 1066 fake users assustou. Quero deixar claro: as defesas que a gente construiu **continuam ativas** mesmo com SendGrid. SendGrid é uma camada A MAIS, não substitui as outras.

### Defesas que a gente já tem em produção:
- **Default-ghost:** usuários novos não aparecem em search/descoberta até confirmarem ações reais. Bot que cria conta não vira "perfil descobrível".
- **EMAIL_ENABLED kill switch:** se algo der errado, eu desligo email todo com 1 flag. Sem rebuild, sem deploy. Imediato.
- **BLOCK_INVALID_DOMAINS:** signup com email terminando em `.local`, `.test`, `.invalid` é bloqueado no momento do cadastro. Bot que usa esses domínios não passa.
- **1066 fake users deletados:** o banco está limpo.
- **Rate limits:** todos os endpoints têm limite de requests por IP/usuário. Bot não consegue criar 1000 contas em 5min de novo.

### Defesas extras que o SendGrid traz:
- **Suppression list automática:** quem deu unsubscribe ou marcou spam NUNCA mais recebe email. Automático, sem eu precisar codar.
- **Bounce handling:** email que volta (endereço inexistente, caixa cheia) é marcado e não tenta de novo. Protege a reputação.
- **Dashboard com stats:** eu vejo em tempo real quantos emails saíram, quantos abriram, quantos voltaram. Se algo estranho acontecer, eu vejo NO MESMO DIA.
- **Reputação isolada:** se um usuário tóxico tentar sabotar, a reputação afetada é a do SendGrid Sender, não a do seu Gmail pessoal.

**Resumo:** a gente passou de "Gmail SMTP no escuro" pra "SendGrid com camadas de defesa redundantes". Pra repetir o que aconteceu, o atacante teria que furar 5 camadas ao mesmo tempo.

---

## 5. CHECKLIST FINAL

Vai marcando conforme for fazendo:

### Pra você (Valth):
- [ ] Conta SendGrid criada (Passo 1)
- [ ] Single Sender Verification feita (Passo 2)
- [ ] Email de verificação confirmado (clicou no link)
- [ ] API Key criada e copiada (Passo 3)
- [ ] API Key colada no chat (Passo 4)

### Pra mim (Claude/dev):
- [ ] Render env vars atualizadas (`SENDGRID_API_KEY`, `EMAIL_SENDER`)
- [ ] Deploy triggado
- [ ] Email de teste enviado pra você

### Confirmação conjunta:
- [ ] Email de teste recebido na sua inbox (não no spam)
- [ ] `EMAIL_ENABLED=true` habilitado em modo limited
- [ ] Signup de teste com email real funcionou
- [ ] Liberado pra produção

---

Qualquer dúvida no meio do caminho, manda screenshot aqui que eu te ajudo. Bora!

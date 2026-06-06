/**
 * reactions.js
 * Gerencia reações em mensagens (emojis) com broadcast em tempo real
 */

class ReactionsManager {
  constructor() {
    this.messageReactions = {};
    this.emojiOptions = ['👍', '❤️', '😂', '🔥', '✨', '👏', '🎉', '🤔'];
  }

  /**
   * Adiciona reação a uma mensagem
   */
  async addReaction(messageId, emoji) {
    try {
      const response = await fetch(`/api/messages/${messageId}/reactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emoji })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('[Reactions] Reação adicionada:', result);
        // Atualiza UI localmente
        this.updateReactionUI(messageId);
        return true;
      }
    } catch (error) {
      console.error('[Reactions] Erro ao adicionar reação:', error);
    }
    return false;
  }

  /**
   * Remove reação de uma mensagem
   */
  async removeReaction(messageId, emoji) {
    try {
      const response = await fetch(
        `/api/messages/${messageId}/reactions/${encodeURIComponent(emoji)}`,
        { method: 'DELETE' }
      );

      if (response.ok) {
        console.log('[Reactions] Reação removida');
        this.updateReactionUI(messageId);
        return true;
      }
    } catch (error) {
      console.error('[Reactions] Erro ao remover reação:', error);
    }
    return false;
  }

  /**
   * Carrega reações de uma mensagem
   */
  async loadReactions(messageId) {
    try {
      const response = await fetch(`/api/messages/${messageId}/reactions`);
      if (!response.ok) return null;

      const data = await response.json();
      this.messageReactions[messageId] = data.reactions;
      return data.reactions;
    } catch (error) {
      console.error('[Reactions] Erro ao carregar reações:', error);
      return null;
    }
  }

  /**
   * Atualiza UI de reações para uma mensagem
   */
  updateReactionUI(messageId) {
    const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
    if (!messageElement) return;

    const reactionsContainer = messageElement.querySelector('.reactions-container');
    if (!reactionsContainer) return;

    // Limpa reações antigas
    reactionsContainer.innerHTML = '';

    const reactions = this.messageReactions[messageId] || [];

    reactions.forEach(reaction => {
      const chip = document.createElement('button');
      chip.className = 'reaction-chip';
      chip.textContent = `${reaction.emoji} ${reaction.count}`;
      chip.style.cssText = `
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 4px 8px;
        font-size: 0.75rem;
        margin-right: 4px;
        cursor: pointer;
        transition: all 0.2s;
      `;

      chip.onclick = async () => {
        await this.removeReaction(messageId, reaction.emoji);
      };

      chip.onmouseenter = () => {
        chip.style.background = 'var(--primary)';
        chip.style.color = 'white';
      };

      chip.onmouseleave = () => {
        chip.style.background = 'var(--bg)';
        chip.style.color = 'inherit';
      };

      reactionsContainer.appendChild(chip);
    });

    // Adiciona botão de + para novas reações
    const addBtn = document.createElement('button');
    addBtn.className = 'reaction-add-btn';
    addBtn.textContent = '+';
    addBtn.style.cssText = `
      background: transparent;
      border: 1px dashed var(--border);
      border-radius: 16px;
      padding: 4px 8px;
      font-size: 0.75rem;
      cursor: pointer;
      color: var(--muted);
      transition: all 0.2s;
    `;

    addBtn.onclick = (e) => this.showEmojiPicker(e, messageId);

    addBtn.onmouseenter = () => {
      addBtn.style.borderColor = 'var(--primary)';
      addBtn.style.color = 'var(--primary)';
    };

    addBtn.onmouseleave = () => {
      addBtn.style.borderColor = 'var(--border)';
      addBtn.style.color = 'var(--muted)';
    };

    reactionsContainer.appendChild(addBtn);
  }

  /**
   * Mostra picker de emojis
   */
  showEmojiPicker(event, messageId) {
    event.stopPropagation();

    // Remove picker anterior se existir
    const existing = document.querySelector('.emoji-picker');
    if (existing) existing.remove();

    const picker = document.createElement('div');
    picker.className = 'emoji-picker';
    picker.style.cssText = `
      position: fixed;
      background: white;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px;
      box-shadow: var(--shadow-lg);
      z-index: 1000;
      display: flex;
      gap: 4px;
    `;

    const rect = event.target.getBoundingClientRect();
    picker.style.top = (rect.bottom + 8) + 'px';
    picker.style.left = rect.left + 'px';

    this.emojiOptions.forEach(emoji => {
      const btn = document.createElement('button');
      btn.textContent = emoji;
      btn.style.cssText = `
        background: none;
        border: none;
        font-size: 1.2rem;
        cursor: pointer;
        padding: 4px;
        transition: all 0.2s;
      `;

      btn.onclick = async () => {
        await this.addReaction(messageId, emoji);
        picker.remove();
      };

      btn.onmouseenter = () => btn.style.transform = 'scale(1.3)';
      btn.onmouseleave = () => btn.style.transform = 'scale(1)';

      picker.appendChild(btn);
    });

    document.body.appendChild(picker);

    // Fecha picker ao clicar fora
    setTimeout(() => {
      document.addEventListener('click', () => picker.remove(), { once: true });
    }, 0);
  }

  /**
   * Obtém top messages por reações (para highlights)
   */
  getTopMessages(messages, limit = 5) {
    const ranked = messages.map(msg => {
      const reactions = this.messageReactions[msg.id] || [];
      const totalReactions = reactions.reduce((sum, r) => sum + r.count, 0);
      return { ...msg, totalReactions };
    });

    return ranked
      .sort((a, b) => b.totalReactions - a.totalReactions)
      .slice(0, limit);
  }

  /**
   * Renderiza seção de destaques (top messages)
   */
  renderHighlights(container, messages) {
    const topMessages = this.getTopMessages(messages);

    if (topMessages.length === 0) {
      container.innerHTML = '<p style="color: var(--muted); text-align: center;">Sem destaques ainda</p>';
      return;
    }

    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        ${topMessages.map((msg, idx) => `
          <div style="
            background: var(--bg);
            padding: 12px;
            border-radius: 8px;
            border-left: 3px solid var(--accent);
          ">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
              <span style="
                background: var(--primary);
                color: white;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                font-size: 0.8rem;
              ">${idx + 1}</span>
              <strong style="color: var(--primary); flex: 1;">${msg.user?.full_name || 'Anônimo'}</strong>
              <span style="color: var(--muted); font-size: 0.8rem;">${msg.totalReactions} reações</span>
            </div>
            <p style="color: var(--text); margin-bottom: 8px; line-height: 1.4;">${msg.content}</p>
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              ${(this.messageReactions[msg.id] || []).map(r => `
                <span style="
                  background: white;
                  padding: 2px 6px;
                  border-radius: 12px;
                  border: 1px solid var(--border);
                  font-size: 0.8rem;
                ">${r.emoji} ${r.count}</span>
              `).join('')}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }
}

window.reactionsManager = new ReactionsManager();

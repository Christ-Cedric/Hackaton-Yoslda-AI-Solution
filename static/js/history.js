class HistoryManager {
    constructor() {
        this.historyContainer = document.querySelector('.history-container');
        this.currentConversationId = null;
        this.conversations = [];
        this.refreshInterval = null;
        document.addEventListener('DOMContentLoaded', () => this.initializeHistory());
    }

    async initializeHistory() {
        await this.loadConversations();
        this.setupHistoryRefresh();
        this.setupKeyboardShortcuts();
    }

    setupHistoryRefresh() {
        if (this.refreshInterval) clearInterval(this.refreshInterval);
        this.refreshInterval = setInterval(() => this.loadConversations(), 30000);
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                this.showSearchDialog();
            }
        });
    }

    async loadConversations() {
        try {
            const response = await fetch('/api/conversations');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            this.conversations = await response.json();
            this.displayConversations(this.conversations);
        } catch (error) {
            console.error('Erreur lors du chargement des conversations:', error);
            this.showError('Impossible de charger l\'historique');
        }
    }

    displayConversations(conversations) {
        if (!this.historyContainer) return;

        const grouped = this.groupByDate(conversations);
        let html = `
            <div class="history-header">
                <button class="new-chat-btn">+ Nouvelle conversation</button>
                <button class="search-history-btn">🔍 Rechercher</button>
            </div>
        `;

        Object.entries(grouped).forEach(([period, convs]) => {
            html += `
                <div class="history-section">
                    <div class="section-header">${period}</div>
                    ${convs.map(conv => this.createConversationItem(conv)).join('')}
                </div>
            `;
        });

        this.historyContainer.innerHTML = html;
        this.setupEventListeners();
    }

    groupByDate(conversations) {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
        const lastWeek = new Date(today); lastWeek.setDate(today.getDate() - 7);
        const lastMonth = new Date(today); lastMonth.setMonth(today.getMonth() - 1);

        const groups = {
            "Aujourd'hui": [],
            "Hier": [],
            "7 derniers jours": [],
            "30 derniers jours": [],
            "Plus ancien": []
        };

        conversations.forEach(conv => {
            const date = new Date(conv.updated_at);
            if (date >= today) groups["Aujourd'hui"].push(conv);
            else if (date >= yesterday && date < today) groups["Hier"].push(conv);
            else if (date >= lastWeek && date < yesterday) groups["7 derniers jours"].push(conv);
            else if (date >= lastMonth && date < lastWeek) groups["30 derniers jours"].push(conv);
            else groups["Plus ancien"].push(conv);
        });

        // Supprimer les groupes vides
        Object.keys(groups).forEach(key => { if (!groups[key].length) delete groups[key]; });
        return groups;
    }

    createConversationItem(conv) {
        const isActive = conv.id === this.currentConversationId;
        const title = this.generateTitle(conv);

        return `
            <div class="history-entry ${isActive ? 'active' : ''}" data-conversation-id="${conv.id}">
                <div class="history-content">
                    <span class="icon">💬</span>
                    <span class="conversation-title">${this.escapeHtml(title)}</span>
                </div>
                <div class="history-actions">
                    <button class="action-btn rename-btn" title="Renommer">✏️</button>
                    <button class="action-btn delete-btn" title="Supprimer">🗑️</button>
                </div>
            </div>
        `;
    }

    generateTitle(conv) {
        if (conv.title && conv.title.trim()) return conv.title;
        if (conv.messages && conv.messages.length > 0) {
            const firstUserMsg = conv.messages.find(m => m.sender === 'user');
            if (firstUserMsg) {
                const text = firstUserMsg.content.trim();
                return text.length > 40 ? text.substring(0, 40) + '...' : text;
            }
        }
        return 'Nouvelle conversation';
    }

    setupEventListeners() {
        // Nouvelle conversation
        const newBtn = this.historyContainer.querySelector('.new-chat-btn');
        if (newBtn) newBtn.addEventListener('click', () => this.createNewChat());

        // Rechercher
        const searchBtn = this.historyContainer.querySelector('.search-history-btn');
        if (searchBtn) searchBtn.addEventListener('click', () => this.showSearchDialog());

        // Entrées de conversation
        const entries = this.historyContainer.querySelectorAll('.history-entry');
        entries.forEach(entry => {
            const convId = entry.dataset.conversationId;

            entry.addEventListener('click', () => this.loadConversation(convId));

            const renameBtn = entry.querySelector('.rename-btn');
            if (renameBtn) renameBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.renameConversation(convId);
            });

            const deleteBtn = entry.querySelector('.delete-btn');
            if (deleteBtn) deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteConversation(convId);
            });
        });
    }

    async loadConversation(conversationId) {
        try {
            this.currentConversationId = conversationId;
            const response = await fetch(`/api/conversations/${conversationId}/history`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();

            this.displayConversations(this.conversations);
            window.dispatchEvent(new CustomEvent('conversationLoaded', { detail: { conversationId, history: data.history } }));
        } catch (error) {
            console.error('Erreur lors du chargement de la conversation:', error);
            this.showError('Impossible de charger cette conversation');
        }
    }

    async createNewChat() {
        try {
            const response = await fetch('/api/conversations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: 'Nouvelle conversation' })
            });
            if (!response.ok) throw new Error(response.statusText);
            const newConv = await response.json();
            this.currentConversationId = newConv.conversation_id || newConv.id;
            await this.loadConversations();
            window.dispatchEvent(new CustomEvent('newConversation', { detail: { conversationId: this.currentConversationId } }));
        } catch (error) {
            console.error(error);
            this.showError('Impossible de créer une nouvelle conversation');
        }
    }

    async renameConversation(conversationId) {
        const conv = this.conversations.find(c => c.id === conversationId);
        const currentTitle = conv ? this.generateTitle(conv) : '';
        const newTitle = prompt('Nouveau titre:', currentTitle);

        if (newTitle && newTitle.trim()) {
            try {
                const response = await fetch(`/api/conversations/${conversationId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: newTitle.trim() })
                });
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                await this.loadConversations();
            } catch (error) {
                console.error('Erreur lors du renommage:', error);
                this.showError('Impossible de renommer cette conversation');
            }
        }
    }

    async deleteConversation(conversationId) {
        if (!confirm('Êtes-vous sûr de vouloir supprimer cette conversation ?')) return;
        try {
            const response = await fetch(`/api/conversations/${conversationId}`, { method: 'DELETE' });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            if (this.currentConversationId === conversationId) {
                this.currentConversationId = null;
                window.dispatchEvent(new CustomEvent('conversationDeleted'));
            }
            await this.loadConversations();
        } catch (error) {
            console.error('Erreur lors de la suppression:', error);
            this.showError('Impossible de supprimer cette conversation');
        }
    }

    showSearchDialog() {
        const dialog = document.createElement('dialog');
        dialog.className = 'search-dialog';
        dialog.innerHTML = `
            <div class="dialog-content">
                <h2>Rechercher dans l'historique</h2>
                <input type="text" class="search-input" placeholder="Rechercher..." autofocus>
                <div class="search-results"></div>
                <button class="close-dialog">Fermer</button>
            </div>
        `;

        const searchInput = dialog.querySelector('.search-input');
        const searchResults = dialog.querySelector('.search-results');

        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            searchResults.innerHTML = '';
            if (query.length < 2) {
                searchResults.innerHTML = '<p class="search-hint">Tapez au moins 2 caractères</p>';
                return;
            }

            const filtered = this.conversations.filter(conv => this.generateTitle(conv).toLowerCase().includes(query));

            if (!filtered.length) {
                searchResults.innerHTML = '<p class="no-results">Aucun résultat trouvé</p>';
                return;
            }

            filtered.forEach(conv => {
                const item = document.createElement('div');
                item.className = 'search-result-item';
                item.innerHTML = `<strong>${this.escapeHtml(this.generateTitle(conv))}</strong>
                                  <small>${new Date(conv.updated_at).toLocaleDateString()}</small>`;
                item.addEventListener('click', () => {
                    this.loadConversation(conv.id);
                    dialog.close();
                });
                searchResults.appendChild(item);
            });
        });

        dialog.querySelector('.close-dialog').addEventListener('click', () => dialog.close());
        document.body.appendChild(dialog);
        dialog.showModal();
    }

    async saveMessage(message, response, sources = []) {
        if (!this.currentConversationId) await this.createNewChat();

        try {
            const historyResponse = await fetch(`/api/conversations/${this.currentConversationId}/history`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, response, sources })
            });
            if (!historyResponse.ok) throw new Error(`HTTP error! status: ${historyResponse.status}`);
            await this.loadConversations();
        } catch (error) {
            console.error('Erreur lors de la sauvegarde du message:', error);
        }
    }

    showError(message) {
        const notification = document.createElement('div');
        notification.className = 'error-notification';
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 500);
        }, 3000);
    }

    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe.replace(/&/g, "&amp;")
                     .replace(/</g, "&lt;")
                     .replace(/>/g, "&gt;")
                     .replace(/"/g, "&quot;")
                     .replace(/'/g, "&#039;");
    }
}

// Initialisation
window.historyManager = new HistoryManager();

const API_BASE_URL = "http://127.0.0.1:8000"; // URL de ton backend FastAPI

async function apiFetch(endpoint, options) {
    return fetch(`${API_BASE_URL}${endpoint}`, options);
}

class ChatApp {
    constructor() {
        this.conversations = {};         // Stockage local
        this.currentConversationId = null;
        this.isFirstMessage = true;

        this.initEventListeners();
        this.loadConversations();
    }

    initEventListeners() {
        const textarea = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const newChatBtn = document.getElementById('newChatBtn');
        const menuToggle = document.getElementById('menuToggle');
        const sidebarOverlay = document.getElementById('sidebarOverlay');

        sendButton.addEventListener('click', () => this.sendMessage());
        textarea.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        textarea.addEventListener('input', () => this.autoResizeTextarea(textarea));

        newChatBtn.addEventListener('click', () => this.startNewConversation());

        menuToggle.addEventListener('click', () => this.toggleSidebar());
        sidebarOverlay.addEventListener('click', () => this.closeSidebar());
        // Suggestions rapides (chips)
        document.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', (e) => {
                const prompt = chip.dataset.prompt || chip.getAttribute('data-prompt') || '';
                if (!prompt) return;
                const textarea = document.getElementById('messageInput');
                textarea.value = prompt;
                this.autoResizeTextarea(textarea);
                // Envoie immédiatement la suggestion
                this.sendMessage();
            });
        });
    }

    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
    }

    generateId() {
        return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    async startNewConversation() {
        // Création locale
        this.currentConversationId = this.generateId();
        this.conversations[this.currentConversationId] = {
            id: this.currentConversationId,
            title: 'Nouvelle conversation',
            messages: [],
            timestamp: new Date().toISOString()
        };

        this.isFirstMessage = true;
        this.clearChat();
        this.showWelcomeScreen();
        this.renderConversationsList();
        this.closeSidebar();
        document.getElementById('messageInput').focus();
    }

    async sendMessage() {
        const textarea = document.getElementById('messageInput');
        const message = textarea.value.trim();
        if (!message) return;

        if (!this.currentConversationId) await this.startNewConversation();

        if (this.isFirstMessage) {
            this.hideWelcomeScreen();
            this.isFirstMessage = false;

            // Met à jour le titre sur le backend si nécessaire
            await this.updateConversationTitle(
                this.currentConversationId,
                message.substring(0, 50) + (message.length > 50 ? '...' : '')
            );
        }

        this.addMessage(message, 'user');
        this.conversations[this.currentConversationId].messages.push({
            content: message,
            sender: 'user',
            timestamp: new Date().toISOString()
        });

        textarea.value = '';
        this.autoResizeTextarea(textarea);
        document.getElementById('sendButton').disabled = true;

        try {
            await this.sendMessageToAPI(message);
        } catch (err) {
            console.error('Erreur API, fallback local:', err);
            await this.simulateAIResponse(message);
        }

        document.getElementById('sendButton').disabled = false;
        this.saveConversations();
        this.renderConversationsList();
        textarea.focus();
    }

    async sendMessageToAPI(userMessage) {
        const response = await apiFetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: userMessage,
                conversation_id: this.currentConversationId
            })
        });

        if (!response.ok) throw new Error(`Erreur HTTP: ${response.status}`);
        const data = await response.json();

        this.addMessage(data.response, 'ai');
        this.conversations[this.currentConversationId].messages.push({
            content: data.response,
            sender: 'ai',
            timestamp: new Date().toISOString()
        });
    }

    addMessage(content, sender) {
        const messagesContainer = document.getElementById('messagesContainer');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-${sender === 'user' ? 'user' : 'robot'}"></i>
            </div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;
        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    clearChat() {
        document.getElementById('messagesContainer').innerHTML = '';
    }

    hideWelcomeScreen() {
        document.getElementById('welcomeScreen').style.display = 'none';
    }

    showWelcomeScreen() {
        document.getElementById('welcomeScreen').style.display = 'flex';
    }

    scrollToBottom() {
        const chatContainer = document.getElementById('chatContainer');
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    toggleSidebar() {
        document.getElementById('sidebar').classList.toggle('open');
        document.getElementById('sidebarOverlay').classList.toggle('active');
    }

    closeSidebar() {
        document.getElementById('sidebar').classList.remove('open');
        document.getElementById('sidebarOverlay').classList.remove('active');
    }

    async loadConversations() {
        try {
            const response = await apiFetch('/api/conversations');
            if (response.ok) {
                const data = await response.json();
                // Supporte deux formats possibles :
                // 1) un tableau directement (ex: [ {id, title, ...}, ... ])
                // 2) un objet { conversations: [...] }
                const conversationsArray = Array.isArray(data) ? data : (data.conversations || []);
                conversationsArray.forEach(conv => {
                    this.conversations[conv.id] = {
                        id: conv.id,
                        title: conv.title,
                        messages: conv.messages || [],
                        snippet: conv.snippet || null,
                        timestamp: conv.updated_at || conv.created_at || new Date().toISOString()
                    };
                });
                if (conversationsArray.length > 0) {
                    this.currentConversationId = conversationsArray[0].id;
                    this.loadConversation(this.currentConversationId);
                }
            }
        } catch (err) {
            console.error('Erreur chargement API:', err);
            this.loadConversationsFromLocalStorage();
        }

        this.renderConversationsList();
    }

    loadConversationsFromLocalStorage() {
        const saved = localStorage.getItem('chatConversations');
        if (!saved) return;

        const data = JSON.parse(saved);
        data.conversations.forEach(conv => {
            this.conversations[conv.id] = conv;
        });
        this.currentConversationId = data.currentId;
        if (this.currentConversationId) this.loadConversation(this.currentConversationId);
    }

    async saveConversations() {
        const conversationsData = Object.values(this.conversations).filter(c => c.messages.length > 0);
        try {
            for (const conv of conversationsData) {
                await apiFetch(`/api/conversations/${conv.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: conv.title, messages: conv.messages })
                });
            }
        } catch (err) {
            console.error('Erreur sauvegarde API, fallback local:', err);
            localStorage.setItem('chatConversations', JSON.stringify({
                conversations: conversationsData,
                currentId: this.currentConversationId
            }));
        }
    }

    renderConversationsList() {
        const list = document.getElementById('conversationsList');
        const conversations = Object.values(this.conversations)
            .filter(c => c.messages.length > 0)
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        if (conversations.length === 0) {
            list.innerHTML = '<div class="empty-state">Aucune conversation</div>';
            return;
        }

        list.innerHTML = conversations.map(c => `
            <button class="conversation-item ${c.id === this.currentConversationId ? 'active' : ''}" data-id="${c.id}">
                <div class="conversation-icon"><i class="fas fa-message"></i></div>
                <div class="conversation-content">
                    <div class="conversation-title">${this.escapeHtml(c.title)}</div>
                    <div class="conversation-preview">${this.getLastMessagePreview(c)}</div>
                </div>
            </button>
        `).join('');

        list.querySelectorAll('.conversation-item').forEach(btn => {
            btn.addEventListener('click', () => {
                this.loadConversation(btn.dataset.id);
                this.closeSidebar();
            });
        });
    }

    getLastMessagePreview(conv) {
        // Prefer snippet if available (Deepseek-like preview)
        if (conv.snippet && conv.snippet.length > 0) {
            return conv.snippet.length > 60 ? conv.snippet.substring(0, 60) + '...' : conv.snippet;
        }
        if (!conv.messages || conv.messages.length === 0) return 'Nouvelle conversation';
        const lastMsg = conv.messages[conv.messages.length - 1];
        return lastMsg.content.length > 60 ? lastMsg.content.substring(0, 60) + '...' : lastMsg.content;
    }

    async loadConversation(convId) {
        const conv = this.conversations[convId];
        if (!conv) return;

        this.currentConversationId = convId;
        this.isFirstMessage = false;
        this.clearChat();
        this.hideWelcomeScreen();

        conv.messages.forEach(msg => this.addMessage(msg.content, msg.sender));
        this.renderConversationsList();
    }

    async updateConversationTitle(convId, title) {
        try {
            await apiFetch(`/api/conversations/${convId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            });
            this.conversations[convId].title = title;
        } catch (err) {
            console.error('Erreur mise à jour titre:', err);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async simulateAIResponse(message) {
        // fallback local
        const reply = `Simulé : je n'ai pas pu contacter le serveur pour "${message}"`;
        this.addMessage(reply, 'ai');
        this.conversations[this.currentConversationId].messages.push({
            content: reply,
            sender: 'ai',
            timestamp: new Date().toISOString()
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new ChatApp());

function appendMiniMessage(type, content) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('chat-message', `${type}-message`, 'mb-2', 'text-sm');
    
    const textDiv = document.createElement('div');
    textDiv.textContent = content;
    messageDiv.appendChild(textDiv);
    
    miniChatMessages.appendChild(messageDiv);
}

function showMiniTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.classList.add('typing-indicator');
    indicator.id = 'mini-typing-indicator';
    
    for (let i = 0; i < 3; i++) {
        const dot = document.createElement('span');
        indicator.appendChild(dot);
    }
    
    miniChatMessages.appendChild(indicator);
    miniChatMessages.scrollTop = miniChatMessages.scrollHeight;
}

function hideMiniTypingIndicator() {
    const indicator = document.getElementById('mini-typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

function initMiniChatAssistant() {
    // Add welcome message
    appendMiniMessage('ai', 'Hello! 👋 I am your health assistant. How can I help you today? Remember, I am not a substitute for professional medical advice.');
}

// Initialize mini chat when it's opened
document.getElementById('chat-assistant-button').addEventListener('click', function() {
    const assistant = document.getElementById('chat-assistant');
    if (assistant.classList.contains('hidden')) {
        // Initialize chat when opened for the first time
        if (!assistant.dataset.initialized) {
            initMiniChatAssistant();
            assistant.dataset.initialized = 'true';
        }
    }
});

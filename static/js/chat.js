document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatContainer = document.getElementById('chat-container');
    const miniChatForm = document.getElementById('mini-chat-form');
    const miniChatInput = document.getElementById('mini-chat-input');
    const miniChatMessages = document.getElementById('mini-chat-messages');
    
    // Initialize speech recognition if available
    let recognition = null;
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
        };
    }
    
    // Initialize mini chat assistant
    if (miniChatForm) {
        miniChatForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const message = miniChatInput.value.trim();
            if (!message) return;
            
            // Add user message to chat
            appendMiniMessage('user', message);
            miniChatInput.value = '';
            
            // Show typing indicator
            showMiniTypingIndicator();
            
            try {
                // Send message to server
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message })
                });
                
                const data = await response.json();
                
                // Remove typing indicator and add AI response
                hideMiniTypingIndicator();
                appendMiniMessage('ai', data.response);
                
                // Scroll to bottom
                miniChatMessages.scrollTop = miniChatMessages.scrollHeight;
                
            } catch (error) {
                console.error('Error:', error);
                hideMiniTypingIndicator();
                appendMiniMessage('ai', 'Sorry, there was an error processing your request.');
            }
        });
    }
    
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = userInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        appendMessage('user', message);
        userInput.value = '';
        
        // Show typing indicator
        showTypingIndicator();
        
        try {
            // Send message to server
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });
            
            const data = await response.json();
            
            // Remove typing indicator and add AI response
            hideTypingIndicator();
            appendMessage('ai', data.response);
            
            // Scroll to bottom
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
        } catch (error) {
            console.error('Error:', error);
            hideTypingIndicator();
            appendMessage('ai', 'Sorry, there was an error processing your request.');
        }
    });
    
    function appendMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message', `${type}-message`);
        
        const textDiv = document.createElement('div');
        textDiv.textContent = content;
        messageDiv.appendChild(textDiv);
        
        chatContainer.appendChild(messageDiv);
    }
    
    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.classList.add('typing-indicator');
        indicator.id = 'typing-indicator';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            indicator.appendChild(dot);
        }
        
        chatContainer.appendChild(indicator);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    function hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
});

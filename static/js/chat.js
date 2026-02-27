/**
 * Health AI - Chat JavaScript
 * Handles main chat functionality
 */

document.addEventListener('DOMContentLoaded', function () {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatContainer = document.getElementById('chat-container');
    const sendBtn = document.getElementById('send-btn');

    // Check if elements exist
    if (!chatForm || !userInput || !chatContainer) {
        console.log('Chat form not found on this page');
        return;
    }

    // Initialize speech recognition if available
    let recognition = null;
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onresult = function (event) {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
            autoResize(userInput);
        };

        recognition.onerror = function (event) {
            console.error('Speech recognition error:', event.error);
        };
    }

    // Add voice input button if speech recognition is available
    if (recognition) {
        const inputContainer = userInput.parentElement;
        const voiceBtn = document.createElement('button');
        voiceBtn.type = 'button';
        voiceBtn.className = 'absolute right-3 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-slate-400 hover:text-primary-500 hover:bg-primary-50 transition-colors';
        voiceBtn.innerHTML = '<i class="fas fa-microphone text-sm"></i>';
        voiceBtn.title = 'Voice input';

        voiceBtn.addEventListener('click', function () {
            try {
                recognition.start();
            } catch (e) {
                console.error('Error starting recognition:', e);
            }
        });

        inputContainer.style.position = 'relative';
        inputContainer.appendChild(voiceBtn);
    }

    // Chat form submission
    chatForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const message = userInput.value.trim();
        if (!message) return;

        // Disable send button during processing
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        // Add user message to chat
        appendMessage('user', message);
        userInput.value = '';
        autoResize(userInput);

        // Show typing indicator
        showTypingIndicator();

        // Scroll to bottom
        scrollToBottom();

        try {
            // Get current session ID if available
            const sessionId = window.currentSessionId || null;

            // Send message to server
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    session_id: sessionId
                })
            });

            const data = await response.json();

            // Remove typing indicator
            hideTypingIndicator();

            if (data.success) {
                // Add AI response
                appendMessage('ai', data.response);

                // Store session ID for future requests
                if (data.session_id) {
                    window.currentSessionId = data.session_id;
                }

                // Display detected symptoms
                if (data.symptoms && data.symptoms.length > 0) {
                    displaySymptoms(data.symptoms);
                }

                // Handle emergency warnings
                if (data.is_emergency) {
                    showEmergencyWarning();
                }
            } else {
                // Show error message
                appendMessage('ai', data.error || 'Sorry, there was an error processing your request.');

                // Show fallback if available
                if (data.fallback_response) {
                    console.log('Showing fallback response');
                }
            }

        } catch (error) {
            console.error('Error:', error);
            hideTypingIndicator();
            appendMessage('ai', 'Sorry, there was an error processing your request. Please try again.');
        }

        // Re-enable send button
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';

        // Scroll to bottom
        scrollToBottom();
    });

    function appendMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message-enter');

        const isUser = type === 'user';

        let html = '';
        if (isUser) {
            html = `
                <div class="flex items-start gap-4 flex-row-reverse">
                    <div class="w-10 h-10 rounded-2xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center flex-shrink-0">
                        <i class="fas fa-user text-white"></i>
                    </div>
                    <div class="bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-2xl rounded-tr-md px-5 py-4 max-w-[80%] shadow-md">
                        <p class="leading-relaxed">${formatMessage(content)}</p>
                    </div>
                </div>
            `;
        } else {
            html = `
                <div class="flex items-start gap-4">
                    <div class="w-10 h-10 rounded-2xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center flex-shrink-0">
                        <i class="fas fa-robot text-white"></i>
                    </div>
                    <div class="bg-white rounded-2xl rounded-tl-md shadow-sm border border-slate-100 px-5 py-4 max-w-[80%]">
                        <p class="leading-relaxed text-slate-700">${formatMessage(content)}</p>
                    </div>
                </div>
            `;
        }

        messageDiv.innerHTML = html;
        chatContainer.appendChild(messageDiv);
    }

    function formatMessage(text) {
        // Convert line breaks to HTML
        text = text.replace(/\n/g, '<br>');

        // Bold text
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Links
        text = text.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" class="text-primary-600 hover:underline" target="_blank">$1</a>');

        return text;
    }

    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'typing-indicator';
        indicator.className = 'message-enter';
        indicator.innerHTML = `
            <div class="flex items-start gap-4">
                <div class="w-10 h-10 rounded-2xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center flex-shrink-0">
                    <i class="fas fa-robot text-white"></i>
                </div>
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

        chatContainer.appendChild(indicator);
        scrollToBottom();
    }

    function hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
    }

    // Display symptoms in the dedicated area
    function displaySymptoms(symptoms) {
        const symptomsDisplay = document.getElementById('symptoms-display');
        const symptomsList = document.getElementById('symptoms-list');

        if (!symptomsDisplay || !symptomsList) return;

        symptomsList.innerHTML = symptoms.map(s => `
            <span class="inline-flex items-center gap-1 px-3 py-1 bg-white rounded-full text-sm text-primary-700 border border-primary-200 shadow-sm">
                <i class="fas fa-check-circle text-primary-500"></i>
                ${s.name || s}
            </span>
        `).join('');

        symptomsDisplay.classList.remove('hidden');

        // Auto-hide after 10 seconds
        setTimeout(() => {
            symptomsDisplay.classList.add('hidden');
        }, 10000);
    }

    function showEmergencyWarning() {
        alert('⚠️ IMPORTANT: Based on your symptoms, please seek immediate medical attention if you are experiencing a medical emergency. Call your local emergency services (911) or go to your nearest emergency room.');
    }

    // Auto-resize textarea on input
    userInput.addEventListener('input', function () {
        autoResize(this);
    });

    // Initialize auto-resize
    autoResize(userInput);
});

// Global function for quick messages
function setQuickMessage(message) {
    const input = document.getElementById('user-input');
    if (input) {
        input.value = message;
        input.dispatchEvent(new Event('input'));
    }
}

// Global function to start new chat
function startNewChat() {
    window.currentSessionId = null;
    const container = document.getElementById('chat-container');
    if (container) {
        window.location.reload();
    }
}

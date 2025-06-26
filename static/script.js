
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('questionForm');
    const input = document.getElementById('questionInput');
    const submitBtn = document.getElementById('submitBtn');
    const messagesContainer = document.getElementById('messages');
    const relatedQuestions = document.getElementById('relatedQuestions');
    const relatedList = document.getElementById('relatedList');
    const loadingOverlay = document.getElementById('loadingOverlay');

    // Auto-resize textarea
    input.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 150) + 'px';
    });

    // Handle form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const question = input.value.trim();
        if (!question) return;

        // Add user message
        addMessage(question, 'user');
        
        // Clear input and show loading
        input.value = '';
        input.style.height = 'auto';
        showLoading(true);
        
        try {
            const response = await fetch('/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `question=${encodeURIComponent(question)}`
            });

            const data = await response.json();
            
            if (data.error) {
                addMessage(`Error: ${data.error}`, 'bot', true);
            } else {
                addMessage(data.response, 'bot');
                
                // Show similarity score if available
                if (data.similarity_score > 0) {
                    addSimilarityScore(data.similarity_score);
                }
                
                // Show related questions
                showRelatedQuestions(data.related_questions || []);
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage('Sorry, I encountered an error. Please try again.', 'bot', true);
        } finally {
            showLoading(false);
        }
    });

    // Handle Enter key (Shift+Enter for new line)
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            form.dispatchEvent(new Event('submit'));
        }
    });

    function addMessage(text, sender, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const icon = sender === 'user' ? 'fas fa-user' : 'fas fa-robot';
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <i class="${icon} message-icon"></i>
                <div class="message-text ${isError ? 'error-message' : ''}">
                    ${text}
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function addSimilarityScore(score) {
        const lastMessage = messagesContainer.lastElementChild;
        const scoreDiv = document.createElement('div');
        scoreDiv.className = 'similarity-score';
        scoreDiv.textContent = `Confidence: ${(score * 100).toFixed(1)}%`;
        lastMessage.querySelector('.message-text').appendChild(scoreDiv);
    }

    function showRelatedQuestions(questions) {
        if (questions && questions.length > 0) {
            relatedList.innerHTML = '';
            questions.forEach(q => {
                const li = document.createElement('li');
                li.textContent = q.question;
                li.addEventListener('click', function() {
                    input.value = q.question;
                    input.focus();
                    form.dispatchEvent(new Event('submit'));
                });
                relatedList.appendChild(li);
            });
            relatedQuestions.style.display = 'block';
        } else {
            relatedQuestions.style.display = 'none';
        }
    }

    function showLoading(show) {
        if (show) {
            loadingOverlay.style.display = 'flex';
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Processing...</span>';
        } else {
            loadingOverlay.style.display = 'none';
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i><span>Ask</span>';
        }
    }

    // Contact support function
    window.showContact = function() {
        alert('For additional support, please:\n\n' +
              '• Visit Jupiter Help Centre\n' +
              '• Email: support@jupiter.money\n' +
              '• Call: 1800-XXX-XXXX\n' +
              '• Chat: Available in the Jupiter app');
    }

    // Add typing indicator
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot-message typing-indicator';
        typingDiv.innerHTML = `
            <div class="message-content">
                <i class="fas fa-robot message-icon"></i>
                <div class="message-text">
                    <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return typingDiv;
    }

    function removeTypingIndicator(element) {
        if (element && element.parentNode) {
            element.parentNode.removeChild(element);
        }
    }
});

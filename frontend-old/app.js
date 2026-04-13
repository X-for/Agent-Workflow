const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');

// Auto-resize textarea
messageInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight < 128 ? this.scrollHeight : 128) + 'px';
    
    // Toggle button state
    sendBtn.disabled = this.value.trim() === '';
});

// Handle Enter key
messageInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);

function addMessage(content, isUser = false) {
    const wrapper = document.createElement('div');
    wrapper.className = `flex gap-4 max-w-4xl mx-auto w-full ${isUser ? 'flex-row-reverse' : ''}`;
    
    const avatar = document.createElement('div');
    avatar.className = `w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 shadow-sm ${
        isUser ? 'bg-gray-800 text-white' : 'bg-blue-100 text-blue-600'
    }`;
    avatar.innerHTML = isUser ? '<i class="fa-solid fa-user text-sm"></i>' : '<i class="fa-solid fa-robot text-sm"></i>';
    
    const messageBox = document.createElement('div');
    messageBox.className = `p-4 rounded-2xl shadow-sm border max-w-[85%] ${
        isUser 
            ? 'bg-gray-800 text-white rounded-tr-none border-gray-700' 
            : 'bg-white text-gray-800 rounded-tl-none border-gray-100 markdown-body'
    }`;
    
    if (isUser) {
        // Safe rendering for user input
        messageBox.textContent = content;
    } else {
        messageBox.innerHTML = marked.parse(content);
    }
    
    wrapper.appendChild(avatar);
    wrapper.appendChild(messageBox);
    chatContainer.appendChild(wrapper);
    
    scrollToBottom();
}

function addTypingIndicator() {
    const wrapper = document.createElement('div');
    wrapper.id = 'typing-indicator';
    wrapper.className = `flex gap-4 max-w-4xl mx-auto w-full`;
    
    const avatar = document.createElement('div');
    avatar.className = `w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 flex-shrink-0 mt-1 shadow-sm`;
    avatar.innerHTML = '<i class="fa-solid fa-robot text-sm"></i>';
    
    const messageBox = document.createElement('div');
    messageBox.className = `bg-white px-4 py-3 rounded-2xl rounded-tl-none shadow-sm border border-gray-100 flex flex-col justify-center gap-1`;
    messageBox.innerHTML = '<div class="text-xs text-blue-500 font-medium mb-1"><i class="fa-solid fa-bolt mr-1"></i>Agent 工作流执行中...</div><div class="typing-indicator"><span></span><span></span><span></span></div>';
    
    wrapper.appendChild(avatar);
    wrapper.appendChild(messageBox);
    chatContainer.appendChild(wrapper);
    
    scrollToBottom();
    return wrapper;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

function scrollToBottom() {
    // Small timeout to allow DOM to render before scrolling
    setTimeout(() => {
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: 'smooth'
        });
    }, 50);
}

async function sendMessage() {
    const content = messageInput.value.trim();
    if (!content) return;
    
    // Reset input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    sendBtn.disabled = true;
    
    // Add user message
    addMessage(content, true);
    
    // Add loading indicator
    addTypingIndicator();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: content })
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const data = await response.json();
        
        removeTypingIndicator();
        addMessage(data.result || "未找到结果");
        
    } catch (error) {
        console.error('Error:', error);
        removeTypingIndicator();
        addMessage(`❌ 处理请求时发生错误: ${error.message}\n请检查后端服务是否正常运行。`);
    }
}

// Initial setup
sendBtn.disabled = true;

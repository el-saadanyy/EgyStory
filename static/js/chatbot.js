/* ================================================================
   EgyStory - Chatbot Client-side JavaScript
   Supports Bilingual Toggle (Arabic / English), Suggestions, History
   ================================================================ */

document.addEventListener('DOMContentLoaded', function () {
  const wrapper = document.getElementById('egyStoryChatbot');
  if (!wrapper) return;

  const toggleBtn = document.getElementById('chatToggleBtn');
  const closeBtn = document.getElementById('chatCloseBtn');
  const clearBtn = document.getElementById('chatClearBtn');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const chatMessages = document.getElementById('chatMessages');
  const sendBtn = document.getElementById('chatSendBtn');
  const langBtns = document.querySelectorAll('.egystory-chat-lang-switch .lang-btn');

  // Current language state (saved in localStorage, default: 'ar')
  let currentLang = localStorage.getItem('egystory_chat_lang') || 'ar';

  const I18N = {
    ar: {
      placeholder: 'اكتب استفسارك هنا...',
      greeting: `<div class="chat-greeting-title">أهلاً بك في EgyStory!</div><div class="chat-greeting-desc">أنا مساعدك الذكي. كيف يمكنني مساعدتك اليوم؟ يمكنك سؤالي عن الحالات المتاحة، خطوات التبرع، أو إنشاء قصة جديدة.</div>`,
      chips: [
        { label: 'حالات حرجة', query: 'رشحلي حالات حرجة ومحتاجة تبرع' },
        { label: 'إنشاء حملة', query: 'إزاي أبدأ قصة حملة تبرع جديدة؟' },
        { label: 'طريقة التبرع', query: 'إزاي أتبرع لحالة على المنصة؟' }
      ],
      cleared: `تم مسح المحادثة. كيف يمكنني مساعدتك الآن؟`,
      networkErr: 'تعذر الاتصال بالخادم، يرجى المحاولة مرة أخرى.',
      direction: 'rtl'
    },
    en: {
      placeholder: 'Type your question here...',
      greeting: `<div class="chat-greeting-title">Welcome to EgyStory!</div><div class="chat-greeting-desc">I am your smart assistant. How can I help you today? You can ask about available campaigns, donation steps, or starting a new campaign.</div>`,
      chips: [
        { label: 'Critical Cases', query: 'Recommend critical and urgent campaigns' },
        { label: 'Start a Story', query: 'How do I start a new crowdfunding campaign?' },
        { label: 'How to Donate', query: 'How can I donate to a campaign?' }
      ],
      cleared: `Conversation cleared. How can I help you now?`,
      networkErr: 'Unable to connect to the server, please try again.',
      direction: 'ltr'
    }
  };

  // Apply language UI
  function applyLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('egystory_chat_lang', lang);

    // Update active button state
    langBtns.forEach(btn => {
      if (btn.dataset.lang === lang) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Update input placeholder and direction
    const config = I18N[lang] || I18N.ar;
    chatInput.placeholder = config.placeholder;
    chatInput.style.direction = config.direction;

    // If chat only contains the initial greeting, re-render it in chosen language
    if (chatMessages.children.length <= 1) {
      renderInitialGreeting();
    }
  }

  function renderInitialGreeting(isCleared = false) {
    const config = I18N[currentLang] || I18N.ar;
    const bodyText = isCleared ? config.cleared : config.greeting;
    
    let chipsHtml = '';
    config.chips.forEach(c => {
      chipsHtml += `<button type="button" class="chat-chip" data-query="${c.query}">${c.label}</button>`;
    });

    chatMessages.innerHTML = `
      <div class="chat-msg assistant">
        <div class="chat-msg-bubble">
          ${bodyText}
          <div class="chat-quick-suggestions">
            ${chipsHtml}
          </div>
        </div>
      </div>
    `;
    scrollToBottom();
  }

  // Language buttons click listener
  langBtns.forEach(btn => {
    btn.addEventListener('click', function () {
      applyLanguage(this.dataset.lang);
    });
  });

  // Helper to get CSRF token from form or cookie
  function getCsrfToken() {
    const input = chatForm.querySelector('[name=csrfmiddlewaretoken]');
    if (input) return input.value;

    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, 10) === 'csrftoken=') {
          cookieValue = decodeURIComponent(cookie.substring(10));
          break;
        }
      }
    }
    return cookieValue;
  }

  // Toggle chat modal
  toggleBtn.addEventListener('click', function () {
    wrapper.classList.toggle('is-active');
    if (wrapper.classList.contains('is-active')) {
      chatInput.focus();
      scrollToBottom();
    }
  });

  closeBtn.addEventListener('click', function () {
    wrapper.classList.remove('is-active');
  });

  // Scroll messages container to bottom
  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Safe markdown/text formatting for rich chatbot responses
  function formatMessageText(text) {
    if (!text) return '';
    
    // First escape HTML special characters to prevent XSS
    let safe = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Format bold: **text** -> <strong>text</strong>
    safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Format inline code / paths: `text` -> <code>text</code>
    safe = safe.replace(/`([^`]+)`/g, '<code class="chat-inline-code">$1</code>');

    // Format links: [text](url) -> <a href="url">text</a>
    safe = safe.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="chat-link">$1 ↗</a>');

    // Convert newlines to paragraphs / linebreaks
    const paragraphs = safe.split(/\n\s*\n/);
    if (paragraphs.length > 1) {
      safe = paragraphs.map(p => `<p class="chat-p">${p.replace(/\n/g, '<br>')}</p>`).join('');
    } else {
      safe = safe.replace(/\n/g, '<br>');
    }

    return safe;
  }

  // Safe element creation with formatted markdown for assistant
  function appendMessage(role, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-msg ' + role;

    const bubble = document.createElement('div');
    bubble.className = 'chat-msg-bubble';

    if (role === 'assistant') {
      bubble.innerHTML = formatMessageText(text);
    } else {
      bubble.textContent = text;
    }

    msgDiv.appendChild(bubble);
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
    return msgDiv;
  }

  // Show typing indicator
  function showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-msg assistant';
    typingDiv.id = 'chatTypingIndicator';

    const typingBubble = document.createElement('div');
    typingBubble.className = 'chat-msg-typing';
    typingBubble.innerHTML = '<span></span><span></span><span></span>';

    typingDiv.appendChild(typingBubble);
    chatMessages.appendChild(typingDiv);
    scrollToBottom();
  }

  function hideTyping() {
    const typing = document.getElementById('chatTypingIndicator');
    if (typing) {
      typing.remove();
    }
  }

  // Load existing session history on initial load
  function loadSessionHistory() {
    fetch('/chatbot/history/')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.status === 'success' && Array.isArray(data.history) && data.history.length > 0) {
          chatMessages.innerHTML = '';
          data.history.forEach(function (turn) {
            appendMessage(turn.role, turn.text);
          });
        }
      })
      .catch(function () {
        // Silently fail if history cannot be fetched
      });
  }

  // Send message handler
  function sendMessage(messageText) {
    const text = (messageText || chatInput.value || '').trim();
    if (!text) return;

    // Append User Message to UI
    appendMessage('user', text);
    chatInput.value = '';
    sendBtn.disabled = true;
    chatInput.disabled = true;

    showTyping();

    const csrfToken = getCsrfToken();

    fetch('/chatbot/message/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({
        message: text,
        lang: currentLang
      })
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        hideTyping();
        sendBtn.disabled = false;
        chatInput.disabled = false;
        chatInput.focus();

        if (result.ok && result.data.status === 'success') {
          appendMessage('assistant', result.data.reply);
        } else {
          const errMsg = (result.data && result.data.message) || (I18N[currentLang] || I18N.ar).networkErr;
          appendMessage('assistant', '⚠️ ' + errMsg);
        }
      })
      .catch(function () {
        hideTyping();
        sendBtn.disabled = false;
        chatInput.disabled = false;
        chatInput.focus();
        appendMessage('assistant', (I18N[currentLang] || I18N.ar).networkErr);
      });
  }

  chatForm.addEventListener('submit', function (e) {
    e.preventDefault();
    sendMessage();
  });

  // Clear history handler
  clearBtn.addEventListener('click', function () {
    const csrfToken = getCsrfToken();
    fetch('/chatbot/clear/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      }
    })
      .then(function (res) { return res.json(); })
      .then(function () {
        renderInitialGreeting(true);
      });
  });

  // Quick suggestion chips handler (Event delegation)
  chatMessages.addEventListener('click', function (e) {
    const chip = e.target.closest('.chat-chip');
    if (chip && chip.dataset.query) {
      sendMessage(chip.dataset.query);
    }
  });

  // Initialize
  applyLanguage(currentLang);
  loadSessionHistory();
});

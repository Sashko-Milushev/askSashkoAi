/* ── State ─────────────────────────────────────────────────────────────────── */
const SESSION_LIMIT = 20;
const SESSION_KEY = 'sashko_session_id';
const COUNT_KEY = 'sashko_msg_count';

let sessionId = sessionStorage.getItem(SESSION_KEY);
if (!sessionId) {
  sessionId = crypto.randomUUID();
  sessionStorage.setItem(SESSION_KEY, sessionId);
}

let msgCount = parseInt(sessionStorage.getItem(COUNT_KEY) || '0', 10);
let currentAskMeQuestion = '';
let chatLocked = false;

/* ── Tab switching ─────────────────────────────────────────────────────────── */
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${tab}`).classList.add('active');
  });
});

/* ── Counter UI ────────────────────────────────────────────────────────────── */
function updateCounter() {
  const el = document.getElementById('msg-counter');
  if (el) el.textContent = `${msgCount} / ${SESSION_LIMIT} messages used`;
}
updateCounter();

/* ── Bubble helpers ────────────────────────────────────────────────────────── */
function addBubble(text, role, action) {
  const messages = document.getElementById('chat-messages');

  const row = document.createElement('div');
  row.className = `bubble-row ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'bubble-avatar';
  avatar.textContent = role === 'user' ? 'You' : 'SM';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;

  row.appendChild(avatar);

  const bubbleWrap = document.createElement('div');

  if (role === 'bot' && action === 'no_info') {
    const hint = document.createElement('p');
    hint.className = 'bubble-action-hint';
    hint.textContent = '📬 Send me this question directly →';
    hint.addEventListener('click', () => openAskMeModal(text));
    bubbleWrap.appendChild(bubble);
    bubbleWrap.appendChild(hint);
  } else if (role === 'bot' && action === 'off_topic') {
    const hint = document.createElement('p');
    hint.className = 'bubble-action-hint';
    hint.textContent = '📬 Go to the Contact tab →';
    hint.addEventListener('click', () => {
      document.querySelector('[data-tab="contact"]').click();
    });
    bubbleWrap.appendChild(bubble);
    bubbleWrap.appendChild(hint);
  } else {
    bubbleWrap.appendChild(bubble);
  }

  row.appendChild(bubbleWrap);
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
  return row;
}

function addTypingIndicator() {
  const messages = document.getElementById('chat-messages');
  const row = document.createElement('div');
  row.className = 'bubble-row bot';
  row.id = 'typing-indicator';

  const avatar = document.createElement('div');
  avatar.className = 'bubble-avatar';
  avatar.textContent = 'SM';

  const bubble = document.createElement('div');
  bubble.className = 'bubble typing-dots';
  bubble.innerHTML = '<span></span><span></span><span></span>';

  row.appendChild(avatar);
  row.appendChild(bubble);
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

/* ── Chat form ─────────────────────────────────────────────────────────────── */
document.getElementById('chat-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (chatLocked) return;

  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;

  // Client-side session limit check
  if (msgCount >= SESSION_LIMIT) {
    lockChat();
    return;
  }

  input.value = '';
  addBubble(message, 'user', null);
  addTypingIndicator();
  setInputEnabled(false);

  try {
    const res = await fetch('/chat/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message }),
    });

    removeTypingIndicator();

    if (!res.ok) {
      addBubble('Something went wrong — please try again.', 'bot', null);
      return;
    }

    const data = await res.json();
    addBubble(data.reply, 'bot', data.action);

    if (data.action === 'limit_reached') {
      lockChat(data.reply);
    } else {
      msgCount++;
      sessionStorage.setItem(COUNT_KEY, String(msgCount));
      updateCounter();
    }

  } catch {
    removeTypingIndicator();
    addBubble('Connection error — please check your internet and try again.', 'bot', null);
  } finally {
    setInputEnabled(true);
    input.focus();
  }
});

function setInputEnabled(enabled) {
  document.getElementById('chat-input').disabled = !enabled;
  document.getElementById('chat-send-btn').disabled = !enabled;
}

function lockChat(message) {
  chatLocked = true;
  setInputEnabled(false);
  const banner = document.getElementById('chat-limit-banner');
  if (message) banner.textContent = message;
  banner.classList.remove('hidden');
}

/* ── Ask-me modal ──────────────────────────────────────────────────────────── */
function openAskMeModal(question) {
  currentAskMeQuestion = question;
  document.getElementById('ask-me-question-preview').textContent = question;
  document.getElementById('ask-me-modal').classList.remove('hidden');
}

document.getElementById('ask-me-cancel').addEventListener('click', () => {
  document.getElementById('ask-me-modal').classList.add('hidden');
});

document.getElementById('ask-me-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = document.getElementById('ask-me-email').value.trim() || null;

  try {
    await fetch('/contact/ask-me', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: currentAskMeQuestion, email }),
    });
  } finally {
    document.getElementById('ask-me-modal').classList.add('hidden');
    addBubble("Got it — I've noted your question. I'll dig into it and have an answer ready next time!", 'bot', null);
  }
});

/* ── Contact form ──────────────────────────────────────────────────────────── */
document.getElementById('contact-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('contact-submit');
  const status = document.getElementById('contact-status');
  const name = document.getElementById('c-name').value.trim();
  const email = document.getElementById('c-email').value.trim();
  const message = document.getElementById('c-message').value.trim();

  if (!name || !email || !message) {
    showStatus(status, 'Please fill in all fields.', 'error');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Sending…';
  status.classList.add('hidden');

  try {
    const res = await fetch('/contact/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, message }),
    });

    if (res.ok) {
      showStatus(status, '✅ Message sent! I\'ll get back to you soon.', 'success');
      document.getElementById('contact-form').reset();
    } else {
      const err = await res.json().catch(() => ({}));
      showStatus(status, err.detail || 'Something went wrong — please try again.', 'error');
    }
  } catch {
    showStatus(status, 'Connection error — please try again.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Send message';
  }
});

function showStatus(el, text, type) {
  el.textContent = text;
  el.className = `form-status ${type}`;
  el.classList.remove('hidden');
}


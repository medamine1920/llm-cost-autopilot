"""Self-contained visitor chat page for GET /."""

CHAT_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#121417">
<title>LLM Cost Autopilot</title>
<meta name="description" content="Ask a question and see which model answered, why it was chosen, and what it cost.">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='16' fill='%23121417'/%3E%3Cpath d='M17 32h30M32 17l-9 15 9 15' fill='none' stroke='%23c1703a' stroke-width='5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
<style>
:root {
  color-scheme: dark;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #121417;
  color: #e8e4de;
  font-size: 16px;
}
* { box-sizing: border-box; }
body { margin: 0; min-height: 100svh; }
button, textarea { font: inherit; }
button { cursor: pointer; }
a { color: inherit; }

.shell {
  width: min(100% - 32px, 920px);
  margin: auto;
  min-height: 100svh;
  display: flex;
  flex-direction: column;
  padding: 28px 0 24px;
}
.top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 36px;
}
.eyebrow {
  font-size: 12px;
  letter-spacing: .16em;
  text-transform: uppercase;
  color: #c1703a;
  font-weight: 800;
  margin: 0 0 11px;
}
.top h1 {
  font-size: clamp(1.8rem, 5vw, 2.65rem);
  letter-spacing: -.045em;
  line-height: 1.1;
  margin: 0 0 12px;
}
.tagline { color: #aaa9a5; line-height: 1.5; margin: 0; max-width: 530px; }
.stats-link {
  white-space: nowrap;
  text-decoration: none;
  color: #c99b7b;
  font-weight: 650;
  font-size: 14px;
  margin-top: 5px;
}
.stats-link:hover { text-decoration: underline; }

.workspace {
  background: #1b1e22;
  border: 1px solid #34383c;
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  min-height: 490px;
  flex: 1;
  overflow: hidden;
  box-shadow: 0 24px 70px #0003;
}
.examples { padding: 22px 24px 18px; border-bottom: 1px solid #303439; }
.examples-label { margin: 0 0 12px; font-size: 13px; font-weight: 700; color: #aeadab; }
.examples-list { display: flex; flex-wrap: wrap; gap: 8px; }
.example {
  border: 1px solid #3d4246;
  color: #e8e4de;
  background: #262a2e;
  padding: 9px 12px;
  border-radius: 10px;
  font-size: 13px;
  text-align: left;
  line-height: 1.35;
  transition: background .15s, border-color .15s;
}
.example:hover, .example:focus-visible { background: #31363a; border-color: #c1703a; }
.example:disabled { opacity: .55; cursor: default; }

.conversation {
  flex: 1;
  min-height: 210px;
  max-height: 53vh;
  overflow-y: auto;
  padding: 26px 24px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  scroll-behavior: smooth;
}
.empty { margin: auto; text-align: center; color: #aaa9a5; max-width: 310px; line-height: 1.55; }
.message { max-width: min(82%, 670px); min-width: 0; }
.message.user { align-self: flex-end; }
.message.assistant { align-self: flex-start; }
.bubble {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.6;
  padding: 13px 16px;
  border-radius: 14px;
  background: #272b2f;
}
.user .bubble { background: #343638; border-bottom-right-radius: 4px; }
.assistant .bubble { border-bottom-left-radius: 4px; }

.badge {
  margin: 9px 0 0 4px;
  padding: 10px 12px;
  border-left: 3px solid #2f7d52;
  border-radius: 4px 9px 9px 4px;
  background: #233028;
  font-size: 13px;
  color: #d2e5d7;
  display: inline-block;
  max-width: 100%;
}
.badge.paid { border-color: #c1703a; background: #352920; color: #f0d4bd; }
.badge-main { display: flex; align-items: baseline; gap: 7px 10px; flex-wrap: wrap; font-weight: 700; }
.model-id { font-size: 12px; font-weight: 400; opacity: .78; }
.badge-meta { font-weight: 500; }
.reason { font-size: 12px; opacity: .8; margin-top: 4px; overflow-wrap: anywhere; }

.thinking { display: flex; align-items: center; gap: 10px; color: #aaa9a5; }
.spinner {
  height: 13px;
  width: 13px;
  border: 2px solid #555b5d;
  border-top-color: #c1703a;
  border-radius: 50%;
  animation: spin .8s linear infinite;
  flex: none;
}
@keyframes spin { to { transform: rotate(360deg); } }
.slow-note { color: #aaa9a5; font-size: 13px; margin: 8px 0 0 4px; }

.composer {
  border-top: 1px solid #303439;
  padding: 16px 20px;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.composer textarea {
  background: #121417;
  color: #e8e4de;
  border: 1px solid #42474b;
  border-radius: 12px;
  resize: vertical;
  min-height: 48px;
  max-height: 150px;
  flex: 1;
  padding: 12px 14px;
  outline: none;
  font-size: 16px;
  line-height: 1.5;
}
.composer textarea:focus { border-color: #c1703a; box-shadow: 0 0 0 3px #c1703a30; }
.composer textarea:disabled { opacity: .65; }
.composer button {
  border: 0;
  border-radius: 11px;
  background: #c1703a;
  color: #17130f;
  font-weight: 750;
  padding: 13px 20px;
  min-height: 48px;
}
.composer button:hover:not(:disabled) { background: #d98a53; }
.composer button:disabled { opacity: .5; cursor: default; }

.savings { padding: 21px 4px 0; }
.savings-primary { font-weight: 700; font-size: 14px; line-height: 1.5; margin: 0; color: #e8e4de; }
.savings-note { font-size: 12px; color: #92928e; line-height: 1.5; margin: 7px 0 0; }

@media (max-width: 600px) {
  .shell { width: min(100% - 24px, 920px); padding: 22px 0; }
  .top { margin-bottom: 24px; }
  .tagline { font-size: 14px; }
  .workspace { min-height: 65svh; border-radius: 16px; }
  .examples { padding: 17px 15px; }
  .conversation { padding: 20px 14px; max-height: 55svh; }
  .message { max-width: 92%; }
  .composer { padding: 12px; gap: 8px; }
  .composer button { padding: 12px 15px; }
  .savings { padding-top: 16px; }
}
</style>
</head>
<body>
<main class="shell">

  <header class="top">
    <div>
      <p class="eyebrow">A smarter way to ask</p>
      <h1>LLM Cost Autopilot</h1>
      <p class="tagline">Ask anything. Each question goes to the cheapest model that can answer it well.</p>
    </div>
    <a class="stats-link" href="/dashboard">stats &rarr;</a>
  </header>

  <section class="workspace" aria-label="Chat">
    <div class="examples">
      <p class="examples-label">Try one:</p>
      <div class="examples-list">
        <button class="example" type="button">Capital of Japan?</button>
        <button class="example" type="button">Jacket costs $80, 25% off then 8% tax &mdash; final price?</button>
        <button class="example" type="button">Summarize: remote work raised productivity but hurt collaboration.</button>
        <button class="example" type="button">How many times does 'r' appear in 'strawberry raspberry'?</button>
      </div>
    </div>

    <div id="conversation" class="conversation" role="log" aria-label="Conversation" aria-live="polite">
      <p id="empty" class="empty">Ask something. You'll see which model answered and what it cost.</p>
    </div>

    <form id="form" class="composer">
      <textarea id="prompt" maxlength="2000" rows="1" placeholder="Ask a question&hellip;" aria-label="Your question"></textarea>
      <button id="send" type="submit">Send</button>
    </form>
  </section>

  <footer class="savings">
    <p id="savings" class="savings-primary" aria-live="polite">Your savings will appear here after you ask.</p>
    <p class="savings-note">Costs use published list prices. Routing decisions are made by rules derived from a 140-prompt benchmark.</p>
  </footer>

</main>

<script>
const conversation = document.getElementById('conversation');
const promptInput  = document.getElementById('prompt');
const sendButton   = document.getElementById('send');
const form         = document.getElementById('form');
const savings      = document.getElementById('savings');
const examples     = [...document.querySelectorAll('.example')];
let busy = false;

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => (
    {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]
  ));
}

function scrollBottom() {
  conversation.scrollTop = conversation.scrollHeight;
}

function bubble(kind, content) {
  const wrap = document.createElement('div');
  wrap.className = 'message ' + kind;
  wrap.innerHTML = '<div class="bubble">' + escapeHtml(content) + '</div>';
  conversation.append(wrap);
  scrollBottom();
  return wrap;
}

function setBusy(value) {
  busy = value;
  promptInput.disabled = value;
  sendButton.disabled = value;
  examples.forEach(button => button.disabled = value);
}

function money(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number === 0) return 'free';
  if (number < 0.0001) return '<$0.0001';
  return '$' + number.toFixed(4);
}

function badge(data) {
  const free    = Number(data.cost_usd) === 0;
  const model   = free ? 'Fast free model' : 'Smarter paid model';
  const cost    = free ? 'free' : money(data.cost_usd);
  const latency = Number(data.latency_ms);
  const seconds = Number.isFinite(latency) ? (latency / 1000).toFixed(1) + 's' : '—';

  return '<div class="badge ' + (free ? '' : 'paid') + '">' +
           '<div class="badge-main">' +
             '<span>' + model + '</span>' +
             '<span class="model-id">' + escapeHtml(data.model ?? '') + '</span>' +
             '<span class="badge-meta">' + cost + ' · ' + seconds + '</span>' +
           '</div>' +
           '<div class="reason">' + escapeHtml(data.routing_reason ?? '') + '</div>' +
         '</div>';
}

async function refreshStats() {
  try {
    const response = await fetch('/v1/stats?days=7');
    if (!response.ok) return;

    const data     = await response.json();
    const requests = Number(data.requests) || 0;
    const byModel  = Array.isArray(data.by_model) ? data.by_model : [];
    const free     = byModel
      .filter(m => Number(m.cost) === 0)
      .reduce((sum, m) => sum + (Number(m.requests) || 0), 0);
    const saved = Number(data.saved_usd) || 0;
    const pct   = Number(data.savings_pct) || 0;

    savings.textContent =
      `${requests} ${requests === 1 ? 'question' : 'questions'} · ` +
      `${free} answered free · $${saved.toFixed(4)} saved · ` +
      `${Math.round(pct)}% cheaper than always using the paid model`;
  } catch {
    /* stats are decoration: never break the page over them */
  }
}

async function send(question) {
  const value = question.trim();
  if (!value || busy) return;

  document.getElementById('empty')?.remove();
  bubble('user', value);
  promptInput.value = '';
  setBusy(true);

  const pending = bubble('assistant', '');
  pending.querySelector('.bubble').innerHTML =
    '<span class="thinking"><span class="spinner" aria-hidden="true"></span>thinking&hellip;</span>';

  const timer = setTimeout(() => {
    if (pending.isConnected) {
      const note = document.createElement('p');
      note.className = 'slow-note';
      note.textContent = 'the free model is slower — this is the tradeoff';
      pending.append(note);
      scrollBottom();
    }
  }, 3000);

  try {
    const response = await fetch('/v1/completions', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt: value})
    });

    if (!response.ok) {
      const message =
        response.status === 429 ? 'Too many questions at once — wait a minute and try again.' :
        response.status === 502 ? "The model providers aren't responding right now." :
                                  "Couldn't complete that question. Please try again.";
      pending.querySelector('.bubble').textContent = message;
      return;
    }

    const data = await response.json();
    pending.querySelector('.bubble').textContent = String(data.text || '(empty response)');
    pending.insertAdjacentHTML('beforeend', badge(data));
    await refreshStats();
  } catch {
    pending.querySelector('.bubble').textContent = "Couldn't reach the service.";
  } finally {
    clearTimeout(timer);
    pending.querySelector('.spinner')?.remove();
    pending.querySelector('.slow-note')?.remove();
    setBusy(false);
    promptInput.focus();
    scrollBottom();
  }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  send(promptInput.value);
});

promptInput.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    send(promptInput.value);
  }
});

examples.forEach(button => button.addEventListener('click', () => {
  promptInput.value = button.textContent;
  send(promptInput.value);
}));

refreshStats();
</script>
</body>
</html>'''


def render(app_name: str, version: str) -> str:
    """Return the visitor chat page."""
    return CHAT_HTML
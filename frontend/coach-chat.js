// Access code is kept only in the current tab, never in URLs or persistent localStorage.
const coachChat = {code: '', id: null, context: {kind: 'today'}, turns: [], ready: false, busy: false, loading: false, pending: null};
function chatStore(key, value) {
    try { if (value == null) sessionStorage.removeItem(key); else sessionStorage.setItem(key, JSON.stringify(value)); } catch {}
}
function chatRead(key, fallback) {
    try { return JSON.parse(sessionStorage.getItem(key)) ?? fallback; } catch { return fallback; }
}
function chatStatus(text) { document.getElementById('coach-chat-status').textContent = text; }
function renderChatContext() {
    const c = coachChat.context;
    document.getElementById('coach-chat-context').textContent = c.kind === 'week'
        ? `Rozmawiamy o tygodniu od ${formatWeeklyDate(c.week_start)}.`
        : c.kind === 'workout' ? `Rozmawiamy o treningu z ${formatWeeklyDate(c.date)}.`
        : 'Kontekst: dzisiejszy trening i aktualne dane.';
    document.getElementById('coach-clear-context').hidden = c.kind === 'today';
}
function chatControls() {
    const busy = coachChat.busy || coachChat.loading;
    document.querySelectorAll('#coach-chat-body button, #coach-chat-body select, #coach-message').forEach(node => { node.disabled = busy; });
    document.getElementById('coach-send').textContent = coachChat.busy ? 'Trener odpowiada…' : 'Wyślij';
    document.getElementById('coach-message-form').setAttribute('aria-busy', String(coachChat.busy));
}
function lockCoachChat() {
    Object.assign(coachChat, {code: '', ready: false, id: null, turns: [], pending: null});
    ['coach-code', 'coach-conversation', 'coach-pending'].forEach(key => chatStore(key, null));
    document.getElementById('coach-access-code').value = '';
    document.getElementById('coach-chat-body').hidden = true;
    document.getElementById('coach-unlock-form').hidden = false;
    document.getElementById('coach-chat-messages').replaceChildren();
}
async function chatRequest(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}/coach${path}`, {
        ...options, cache: 'no-store', signal: AbortSignal.timeout(120000),
        headers: {'Content-Type': 'application/json', Authorization: `Bearer ${coachChat.code}`},
    });
    if (!response.ok) {
        if (response.status === 401) lockCoachChat();
        const data = await response.json().catch(() => ({}));
        throw new Error(typeof data.detail === 'string' ? data.detail : 'Nie udało się wykonać tej operacji. Spróbuj ponownie.');
    }
    return response.json();
}
function renderChatMessages() {
    const log = document.getElementById('coach-chat-messages');
    log.replaceChildren();
    const message = (role, text) => {
        const article = document.createElement('article');
        article.className = 'coach-chat-message';
        article.dataset.role = role;
        const label = document.createElement('strong');
        label.textContent = role === 'athlete' ? 'Ty' : 'Trener';
        const body = document.createElement('p');
        body.textContent = text;
        article.append(label, body);
        log.appendChild(article);
        return article;
    };
    if (!coachChat.turns.length) {
        const empty = document.createElement('p');
        empty.className = 'muted';
        empty.textContent = 'Zacznij od pytania. Trener pobierze aktualne dane dopiero po jego wysłaniu.';
        log.appendChild(empty);
    }
    for (const turn of coachChat.turns) {
        message('athlete', turn.message);
        const reply = message('coach', turn.answer);
        const details = document.createElement('details');
        const summary = document.createElement('summary');
        summary.textContent = 'Na czym opieram odpowiedź?';
        details.appendChild(summary);
        const list = document.createElement('ul');
        for (const source of turn.sources || []) {
            const item = document.createElement('li');
            const period = source.week_start || source.date || '';
            item.textContent = `${source.label}${period ? ` (${period})` : ''}`;
            list.appendChild(item);
        }
        for (const limitation of turn.limitations || []) {
            const item = document.createElement('li');
            item.textContent = limitation;
            list.appendChild(item);
        }
        const asOf = document.createElement('p');
        asOf.className = 'muted';
        asOf.textContent = `Dane pobrane: ${new Date(turn.as_of).toLocaleString('pl-PL')}.`;
        details.append(list, asOf);
        reply.appendChild(details);
    }
    log.scrollTop = log.scrollHeight;
}
async function refreshCoachConversations() {
    const data = await chatRequest('/conversations');
    const select = document.getElementById('coach-conversation-select');
    select.replaceChildren(new Option('Nowa rozmowa', ''));
    data.items.forEach(item => select.appendChild(new Option(item.title, item.id)));
    select.value = coachChat.id || '';
    return data.items;
}
async function loadCoachHistory() {
    if (!coachChat.id) { coachChat.turns = []; renderChatMessages(); return; }
    const history = await chatRequest(`/conversations/${encodeURIComponent(coachChat.id)}`);
    coachChat.turns = history.turns;
    const last = history.turns.at(-1);
    if (last && !coachChat.pending) coachChat.context = last.context;
    if (coachChat.pending && history.turns.some(t => t.id === coachChat.pending.request_id)) {
        coachChat.pending = null;
        chatStore('coach-pending', null);
        document.getElementById('coach-message').value = '';
    }
    renderChatContext();
    renderChatMessages();
    document.getElementById('coach-retry').hidden = !coachChat.pending;
}
async function openCoachChat() {
    if (!coachChat.code || coachChat.ready || coachChat.loading) return;
    coachChat.loading = true;
    chatControls();
    chatStatus('Wczytywanie rozmowy…');
    try {
        const items = await refreshCoachConversations();
        if (!items.some(item => item.id === coachChat.id)) coachChat.id = null;
        await loadCoachHistory();
        coachChat.ready = true;
        document.getElementById('coach-chat-body').hidden = false;
        document.getElementById('coach-unlock-form').hidden = true;
        chatStatus('Rozmowa jest prywatna. Pytanie nie zmienia planu ani zapisanych ocen.');
    } catch (error) {
        chatStatus(error.message || 'Nie można wczytać rozmowy. Spróbuj ponownie.');
    } finally {
        coachChat.loading = false;
        chatControls();
    }
}
function newCoachConversation(context = {kind: 'today'}) {
    if (coachChat.busy || coachChat.loading) return;
    Object.assign(coachChat, {id: null, turns: [], pending: null, context});
    chatStore('coach-conversation', null);
    chatStore('coach-pending', null);
    chatStore('coach-context', context);
    document.getElementById('coach-message').value = '';
    document.getElementById('coach-conversation-select').value = '';
    document.getElementById('coach-retry').hidden = true;
    renderChatContext();
    renderChatMessages();
}
function startCoachDiscussion(context, question) {
    if (coachChat.busy || coachChat.loading) return;
    newCoachConversation(context);
    document.getElementById('coach-message').value = question;
    location.hash = 'coach';
    if (currentAppView() === 'coach') openCoachChat();
}
async function sendCoachMessage() {
    if (!coachChat.ready || coachChat.busy || coachChat.loading) return;
    const input = document.getElementById('coach-message');
    const text = input.value.trim();
    if (!text || text.length > 2000) return;
    coachChat.busy = true;
    chatControls();
    chatStatus('Trener analizuje aktualne dane i przygotowuje odpowiedź…');
    document.getElementById('coach-retry').hidden = true;
    try {
        if (!coachChat.id) {
            coachChat.id = crypto.randomUUID();
            chatStore('coach-conversation', coachChat.id);
        }
        await chatRequest('/conversations', {method: 'POST', body: JSON.stringify({id: coachChat.id})});
        const pending = coachChat.pending;
        const same = pending && pending.message === text && pending.conversation_id === coachChat.id
            && JSON.stringify(pending.context) === JSON.stringify(coachChat.context);
        coachChat.pending = same ? pending : {conversation_id: coachChat.id, request_id: crypto.randomUUID(), message: text, context: {...coachChat.context}};
        chatStore('coach-pending', coachChat.pending);
        const turn = await chatRequest('/chat', {method: 'POST', body: JSON.stringify(coachChat.pending)});
        if (!coachChat.turns.some(t => t.id === turn.id)) coachChat.turns.push(turn);
        coachChat.pending = null;
        chatStore('coach-pending', null);
        input.value = '';
        renderChatMessages();
        chatStatus('Odpowiedź zapisana w historii rozmowy.');
        // History-list failures must not turn a completed answer into a failed send.
        await refreshCoachConversations().catch(() => {});
    } catch (error) {
        chatStatus(error.message || 'Nie udało się odebrać odpowiedzi. Ponów pytanie, aby sprawdzić jego wynik.');
        document.getElementById('coach-retry').hidden = !coachChat.code;
    } finally {
        coachChat.busy = false;
        chatControls();
    }
}
function initializeCoachChat() {
    coachChat.code = chatRead('coach-code', '');
    coachChat.id = chatRead('coach-conversation', null);
    coachChat.pending = chatRead('coach-pending', null);
    coachChat.context = coachChat.pending?.context || chatRead('coach-context', {kind: 'today'});
    if (coachChat.pending) document.getElementById('coach-message').value = coachChat.pending.message;
    renderChatContext();
    document.getElementById('coach-unlock-form').addEventListener('submit', async event => {
        event.preventDefault();
        if (coachChat.loading) return;
        coachChat.code = document.getElementById('coach-access-code').value.trim();
        chatStore('coach-code', coachChat.code);
        await openCoachChat();
    });
    document.getElementById('coach-message-form').addEventListener('submit', event => { event.preventDefault(); sendCoachMessage(); });
    document.getElementById('coach-retry').addEventListener('click', sendCoachMessage);
    document.getElementById('coach-new-conversation').addEventListener('click', () => newCoachConversation());
    document.getElementById('coach-clear-context').addEventListener('click', () => {
        coachChat.context = {kind: 'today'};
        chatStore('coach-context', coachChat.context);
        renderChatContext();
    });
    document.getElementById('coach-lock').addEventListener('click', () => {lockCoachChat(); chatStatus('Dostęp zamknięty.');});
    document.getElementById('coach-conversation-select').addEventListener('change', async event => {
        if (!event.target.value) { newCoachConversation(); return; }
        coachChat.id = event.target.value;
        coachChat.pending = null;
        chatStore('coach-pending', null);
        chatStore('coach-conversation', coachChat.id);
        document.getElementById('coach-message').value = '';
        coachChat.loading = true;
        chatControls();
        try {
            await loadCoachHistory();
            document.getElementById('coach-history-retry').hidden = true;
            chatStatus('Historia wczytana.');
        } catch (error) {
            coachChat.turns = [];
            renderChatMessages();
            chatStatus(error.message);
            document.getElementById('coach-history-retry').hidden = false;
        } finally { coachChat.loading = false; chatControls(); }
    });
    document.getElementById('coach-history-retry').addEventListener('click', () => {
        document.getElementById('coach-conversation-select').dispatchEvent(new Event('change'));
    });
    document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => {
        document.getElementById('coach-message').value = button.dataset.question;
        document.getElementById('coach-message').focus();
    }));
}

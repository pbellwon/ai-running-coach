// Confirmed knowledge is stored on the server; edits always produce a review first.
(() => {
    const el = name => document.getElementById(`profile-${name}`);
    const root = document.getElementById('athlete-knowledge');
    const categories = {training_agreement:'Ustalenie treningowe', injury:'Kontuzja', restriction:'Ograniczenie', training_response:'Reakcja na obciążenie', other:'Inne'};
    const states = {current:'Aktualne', historical:'Historyczne', resolved:'Ustąpiło / nieaktualne', unreviewed:'Starszy wpis — stan niepotwierdzony'};
    let profile = null, calendar = null, proposal = null, edit = {}, pending = null, busy = false, epoch = 0;
    const text = (tag, value) => { const node = document.createElement(tag); node.textContent = value; return node; };
    const status = value => { el('status').textContent = value; };
    async function request(path='', options) {
        const current = epoch;
        const result = await chatRequest(`/profile${path}`, options);
        if (epoch !== current) throw new Error('Dostęp został zamknięty.');
        return result;
    }
    function controls() {
        root.querySelectorAll('button,input,select,textarea').forEach(node => { node.disabled = busy; });
        el('accept').hidden = !proposal || proposal.status !== 'pending';
        el('reject').hidden = !proposal || proposal.status !== 'pending';
        el('accept').disabled = busy || !proposal || proposal.status !== 'pending';
        el('reject').disabled = busy || !proposal || proposal.status !== 'pending';
    }
    async function run(fn) {
        if (busy) return;
        busy = true; controls(); const current = epoch;
        try { await fn(); } catch (error) { if (current === epoch) status(error.message); }
        finally { busy = false; controls(); }
    }
    function describe(value, kind) {
        if (!value) return 'Brak potwierdzonej informacji.';
        if (kind === 'goal') return `${value.name}\n${value.date} · ${value.distance_km} km · A\nCel: ${value.target_time || 'ukończenie'}\n${value.notes || ''}`;
        if (kind === 'cycle') return `Cykl ${value.cycle_days}-dniowy. Dzień 1: ${value.anchor_date || 'początek nieustalony'}.`;
        return `${categories[value.category] || value.category}\n${value.text}\nStan: ${states[value.fact_status || value.status]}\nZgłoszone: ${value.observed_on || 'brak daty'}`;
    }
    function showProposal(value) {
        proposal = value; root.open = true; el('preview').hidden = false;
        const kind = value.change.kind;
        el('preview-title').textContent = value.status === 'applied' ? 'Ustalenie potwierdzone' : value.status === 'rejected' ? 'Propozycja odrzucona' : kind === 'goal' ? 'Potwierdzić ten cel główny?' : kind === 'cycle' ? 'Potwierdzić początek cyklu?' : 'Zapamiętać to ustalenie?';
        el('before').textContent = describe(value.before, kind); el('after').textContent = describe(value.after, kind);
        el('source').textContent = value.quote ? `Twoja wiadomość: „${value.quote}”` : kind === 'goal' ? 'Źródło: race_calendar. Arkusz nie będzie zmieniany.' : 'Źródło: Twoje potwierdzenie w profilu.';
        el('accept').textContent = kind === 'goal' ? 'Potwierdź cel' : kind === 'cycle' ? 'Potwierdź początek cyklu' : 'Zapamiętaj';
        controls(); el('preview').scrollIntoView({block:'nearest', behavior:'smooth'});
    }
    async function refresh() {
        profile = await request();
        el('goal').textContent = profile.goal ? describe(profile.goal, 'goal') : 'Cel nie został jeszcze potwierdzony. Wybierz start A z kalendarza.';
        el('cycle').textContent = describe(profile.cycle, 'cycle') + (profile.cycle_day ? ` Dziś dzień ${profile.cycle_day}/10.` : '');
        el('anchor').value = profile.cycle.anchor_date || '';
        if (!el('observed').value) el('observed').value = profile.today;
        el('observed').max = profile.today;
        el('memory').replaceChildren();
        if (!profile.memory.length) el('memory').append(text('p', 'Brak zapisanych ustaleń. Możesz je zapamiętać z rozmowy lub dodać tutaj.'));
        for (const memory of profile.memory) {
            const article = document.createElement('article'), button = document.createElement('button'); button.type = 'button';
            article.append(text('p', describe(memory, 'memory')));
            article.append(text('p', memory.confirmed_at ? `Potwierdzone: ${new Date(memory.confirmed_at+'Z').toLocaleString('pl-PL')}` : 'Wpis z wcześniejszej wersji aplikacji; wymaga określenia aktualnego stanu.'));
            button.textContent = 'Popraw lub oznacz ustąpienie';
            button.addEventListener('click', () => fillEditor({text:memory.text, category:memory.category, fact_status:memory.status, replace_id:memory.id,
                source_turn_id:memory.source_turn_id, quote:memory.source_quote}));
            article.append(button); el('memory').append(article);
        }
        el('pending').replaceChildren(); el('history').replaceChildren();
        for (const item of profile.proposals) {
            if (item.status === 'pending') {
                const button = document.createElement('button'); button.type = 'button';
                button.textContent = `Sprawdź propozycję: ${item.change.kind === 'memory' ? item.after.text : item.change.kind === 'goal' ? item.after.name : 'początek cyklu'}`;
                button.addEventListener('click', () => showProposal(item)); el('pending').append(button);
            } else {
                const details = document.createElement('details');
                details.append(text('summary', `${item.status === 'applied' ? 'Potwierdzone' : 'Odrzucone'} · ${new Date(item.created_at+'Z').toLocaleString('pl-PL')}`));
                details.append(text('pre', `Przed:\n${describe(item.before,item.change.kind)}\n\nPo:\n${describe(item.after,item.change.kind)}${item.quote ? `\n\nŹródło: ${item.quote}` : ''}`));
                el('history').append(details);
            }
        }
        for (const memory of profile.memory_history) {
            const details = document.createElement('details'); details.append(text('summary', 'Poprzednia wersja ustalenia'), text('pre', describe(memory,'memory'))); el('history').append(details);
        }
    }
    function fillEditor(value={}) {
        edit = value;
        root.open = true; el('editor').open = true;
        el('text').value = value.text || ''; el('category').value = categories[value.category] ? value.category : 'training_agreement';
        el('fact-status').value = states[value.fact_status] && value.fact_status !== 'unreviewed' ? value.fact_status : 'current';
        el('observed').value = profile?.today || new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Warsaw'}).format(new Date());
        el('editor-source').textContent = value.quote ? `Źródło: „${value.quote}”` : value.replace_id ? 'Powstanie nowa wersja. Oryginał pozostanie w historii.' : 'Nowe ustalenie potwierdzisz po podglądzie.';
        el('editor').scrollIntoView({block:'nearest', behavior:'smooth'});
    }
    async function stage(change, source={}) {
        await refresh();
        const body = {version:profile.version, change, source_turn_id:source.source_turn_id || null, quote:source.quote || null};
        const hash = JSON.stringify(body);
        if (!pending || pending.hash !== hash) pending = {hash,id:crypto.randomUUID()};
        showProposal(await request('/proposals',{method:'POST',body:JSON.stringify({id:pending.id,...body})}));
        pending = null; status('Sprawdź treść i źródło. Pamięć zmieni się dopiero po potwierdzeniu.');
    }
    el('load').addEventListener('click', () => run(async () => { await refresh(); status('Profil wczytany.'); }));
    root.addEventListener('toggle', () => { if (root.open && !profile && !busy) run(refresh); });
    el('calendar-load').addEventListener('click', () => run(async () => {
        calendar = await request('/calendar');
        el('race').replaceChildren(...calendar.items.map(r => new Option(`${r.date} — ${r.name} — ${r.distance_km} km${r.target_time ? ` — ${r.target_time}` : ''}`,r.key)));
        el('goal-form').hidden = !calendar.items.length;
        status(calendar.items.length ? 'Wybierz start główny i sprawdź zmianę celu.' : 'Brak przyszłych startów A. Uzupełnij race_calendar.');
    }));
    el('goal-form').addEventListener('submit', event => { event.preventDefault(); run(() => stage({kind:'goal',calendar_version:calendar.version,race_key:el('race').value})); });
    el('cycle-form').addEventListener('submit', event => { event.preventDefault(); run(() => stage({kind:'cycle',cycle_days:10,anchor_date:el('anchor').value || null})); });
    el('memory-form').addEventListener('submit', event => { event.preventDefault(); run(() => stage({kind:'memory',category:el('category').value,text:el('text').value,
        fact_status:el('fact-status').value,observed_on:el('observed').value,replace_id:edit.replace_id || null},edit)); });
    el('editor-clear').addEventListener('click', () => fillEditor());
    for (const decision of ['accept','reject']) el(decision).addEventListener('click', () => run(async () => {
        const result = await request(`/proposals/${proposal.id}/decision`,{method:'POST',body:JSON.stringify({decision})});
        showProposal(result); await refresh(); status(result.status === 'applied' ? 'Ustalenie potwierdzone i zapisane w pamięci PaceMind.' : 'Propozycja odrzucona.');
        document.dispatchEvent(new Event('athlete-profile-updated'));
        if (coachChat.id && !coachChat.busy) await loadCoachHistory();
    }));
    window.openAthleteMemoryDraft = value => run(async () => { await refresh(); fillEditor(value); });
    window.renderProfileSuggestion = value => {
        const article = document.createElement('article');
        article.append(text('strong','Zapamiętać to ustalenie?'),text('p',value.after.text));
        const button = document.createElement('button'); button.type = 'button';
        button.textContent = value.status === 'applied' ? 'Ustalenie zapamiętane — pokaż' : value.status === 'rejected' ? 'Ustalenie odrzucone — pokaż' : 'Sprawdź i potwierdź';
        button.addEventListener('click', () => run(async () => { await refresh(); showProposal(profile.proposals.find(p => p.id === value.id) || value); }));
        article.append(button); return article;
    };
    document.addEventListener('coach-access-closed', () => {
        epoch++; profile = calendar = proposal = pending = null; edit = {};
        ['memory','pending','history','race'].forEach(name => el(name).replaceChildren());
        ['goal','cycle','source','before','after','editor-source'].forEach(name => { el(name).textContent = ''; });
        ['text','anchor','observed'].forEach(name => { el(name).value = ''; });
        el('preview').hidden = el('goal-form').hidden = true; root.open = false; status('');
    });
    controls();
})();

// The athlete asks for a proposal; PaceMind chooses the ten-day training cycle from evidence.
(() => {
    const el = name => document.getElementById(`race-${name}`);
    const labels = {preview: 'Do akceptacji', writing: 'Zapis do sprawdzenia', applied: 'Zapisany', rejected: 'Odrzucony', stale: 'Nieaktualny'};
    let context = null, preview = null, busy = false, epoch = 0, pending = null, clarificationId = null;
    let profile = null, calendar = null, goalPending = null;
    const text = (tag, value) => { const node = document.createElement(tag); node.textContent = value; return node; };
    const status = value => { el('status').textContent = value; };
    async function request(path, options) {
        const current = epoch;
        const value = await chatRequest(`/race-plans${path}`, options);
        if (current !== epoch) throw new Error('Dostęp został zamknięty.');
        return value;
    }
    function outcome(value) {
        const changes = Number(value.summary?.added || 0) + Number(value.summary?.replaced || 0);
        if (value.status === 'applied') return ['Plan zapisany', 'Zaakceptowany plan został zapisany w Google Sheets.'];
        if (value.status === 'writing') return ['Sprawdź wynik zapisu', 'Zapis rozpoczęto. Przycisk poniżej sprawdza wynik tej samej operacji.'];
        if (value.status === 'rejected') return ['Propozycja odrzucona', 'Ta propozycja nie została zapisana do arkusza.'];
        if (value.status === 'stale') return ['Podgląd nieaktualny', 'Dane zmieniły się. Poproś o nową propozycję planu.'];
        if (value.coaching && value.coaching.status !== 'ready') return ['Trener potrzebuje odpowiedzi', 'Odpowiedz na pytanie poniżej w polu „Dopowiedz trenerowi”, a następnie przygotuj nową propozycję.'];
        if (!changes) return ['Brak zmian do zapisania', 'Nie powstała propozycja zmiany treningów. To nie potwierdza, że obecny plan jest optymalny. Sprawdź powód poniżej — jednostki mogą być zachowane lub chronione.'];
        if (!value.can_accept) return ['Propozycja wymaga wyjaśnienia', 'Zapis jest zablokowany. Najpierw rozstrzygnij wskazane poniżej pytania lub konflikty.'];
        return ['Propozycja planu gotowa', `PaceMind proponuje ${value.summary.added} nowych i ${value.summary.replaced} przebudowanych jednostek. Nic nie zostało jeszcze zapisane. Pierwsze zmiany są rozwinięte poniżej — sprawdź porównanie „Przed / Po” przed akceptacją.`];
    }
    function controls() {
        document.querySelectorAll('#race-generate button, #race-generate input, #race-generate textarea, #race-generate select, #race-load, #race-history button').forEach(node => { node.disabled = busy; });
        const chosen = calendar?.items.find(r => r.key === el('goal').value);
        const confirmed = chosen && Object.entries(chosen).every(([key,value]) => key === 'key' || profile?.goal?.[key] === value);
        el('goal-confirm').hidden = !chosen || confirmed;
        el('goal-help').textContent = confirmed ? `Cel potwierdzony: ${chosen.name} · ${chosen.date} · ${chosen.target_time || 'ukończenie'}.`
            : chosen ? `Wybrany: ${chosen.name} · ${chosen.date} · ${chosen.target_time || 'ukończenie'}. Obecny cel: ${profile?.goal?.name || 'nieustalony'}. Potwierdź zmianę przed planowaniem.` : 'Dodaj przyszły start z priorytetem A w race_calendar i odśwież kalendarz.';
        const changes = Number(preview?.summary?.added || 0) + Number(preview?.summary?.replaced || 0);
        const writable = ['long-term-10-day-v1','adaptation-10-day-v1'].includes(preview?.planning_mode) && preview.can_accept && changes > 0;
        el('accept').hidden = !preview || !(preview.status === 'writing' || (preview.status === 'preview' && writable));
        if (preview) {
            const [title, message] = outcome(preview);
            el('outcome-title').textContent = title; el('outcome').textContent = message;
        }
        el('accept').disabled = busy || !preview || !(preview.status === 'writing' || (preview.status === 'preview' && writable));
        el('reject').disabled = busy || !preview || preview.status !== 'preview';
        el('generate').setAttribute('aria-busy', String(busy));
        const updating = context?.active_plan && el('start').value === context.active_plan.start;
        el('generate').querySelector('button[type=submit]').textContent = busy ? 'Przetwarzanie…' : updating ? 'Przygotuj aktualizację planu' : 'Przygotuj propozycję planu';
        el('generate').querySelector('button[type=submit]').disabled = busy || !confirmed;
        el('accept').textContent = preview?.status === 'writing' ? 'Sprawdź wynik poprzedniego zapisu planu' : 'Akceptuję plan i zapisuję do Google Sheets';
    }
    const stateLabel = value => value.status === 'preview' && ['clarify','pause'].includes(value.generation_status || value.coaching?.status) ? 'Wymaga odpowiedzi' : labels[value.status] || value.status;
    async function run(fn) {
        if (busy) return;
        const current = epoch;
        busy = true; controls();
        try { await fn(); } catch (error) { if (current === epoch) { status(el('error').hidden ? error.message : ''); const target=el('error').hidden ? el('status') : el('error-title'); target.tabIndex = -1; target.focus({preventScroll:true}); target.scrollIntoView({block:'center'}); } }
        finally { busy = false; controls(); }
    }
    const workout = row => row ? `${row.date} — ${row.title}\nDystans: ${row.planned_distance_km || 'nie określono'} km\nCzas: ${row.planned_duration_min || 'nie określono'} min\n\n${row.description}` : 'Brak treningu.';
    function showPreview(value) {
        el('error').hidden = true;
        preview = value; clarificationId = value.status === 'preview' && ['clarify','pause'].includes(value.coaching?.status) ? value.id : null; el('preview').hidden = false; el('coaching').replaceChildren();
        if (value.adaptation_assessment) el('coaching').append(text('h4','Korekta istniejącego planu'),text('p',value.adaptation_assessment.reason));
        const campaign = value.long_term;
        if (campaign) {
            el('coaching').append(text('h4',`Droga do ${campaign.goal.name} — ${campaign.goal.date}`));
            const phases = document.createElement('ol');
            campaign.phases.forEach(phase => phases.append(text('li',`${phase.start} – ${phase.end}: ${phase.name}. ${phase.role}`)));
            el('coaching').append(phases);
            campaign.assumptions.forEach(item => el('coaching').append(text('p',item)));
        }
        const coaching = value.coaching;
        if (coaching) {
            el('coaching').append(text('h4', 'Dlaczego taki plan?'), text('p', coaching.explanation), text('p', coaching.anchor_note));
            const evidence = document.createElement('ul');
            coaching.evidence.forEach(id => evidence.append(text('li', (value.sources || []).find(source => source.id === id)?.label || ({calendar: 'Kalendarz startów', athlete_note: 'Twoje bieżące dopowiedzenie'}[id] || id))));
            el('coaching').append(evidence);
            if (coaching.questions.length) { el('extra').open = true; el('coaching').append(text('p', 'Odpowiedz w polu „Dopowiedz trenerowi” i poproś o nową propozycję.')); }
        }
        if (value.limitations?.length) {
            const details = document.createElement('details'); details.append(text('summary', 'Źródła i ograniczenia danych'));
            value.limitations.forEach(item => details.append(text('p', item))); el('coaching').append(details);
        }
        el('summary').textContent = `${value.start} – ${value.end}: dodane ${value.summary.added}, przebudowane ${value.summary.replaced}, zachowane ${value.summary.kept}. Stan: ${stateLabel(value)}.`;
        for (const [name, items] of [['warnings', value.warnings], ['blockers', value.blockers]]) el(name).replaceChildren(...items.map(item => text('li', item)));
        const table = document.createElement('table'), header = document.createElement('tr');
        ['Cykl od', 'Do', 'Etap', 'Propozycja km', 'Plan km'].forEach(name => header.append(text('th', name))); table.append(header);
        (value.cycles || value.weeks || []).forEach(cycle => {
            const row = document.createElement('tr');
            [cycle.start || cycle.week_start, cycle.end || 'Archiwalny tydzień', cycle.phase + (cycle.role ? `: ${cycle.role}` : ''), cycle.budget_km, cycle.planned_km].forEach(item => row.append(text('td', item))); table.append(row);
        });
        el('weeks').replaceChildren(table); el('entries').replaceChildren();
        let opened = 0;
        for (const entry of value.entries) {
            const details = document.createElement('details');
            if (entry.action !== 'keep' && opened < 3) { details.open = true; opened++; }
            const action = {add: 'Dodany', replace: 'Przebudowany', keep: 'Zachowany'}[entry.action];
            details.append(text('summary', `${entry.after.date}${entry.cycle_day ? ` · dzień ${entry.cycle_day}/10` : ''} — ${entry.after.title} — ${action}`));
            if (entry.preservation_reason) details.append(text('p', entry.preservation_reason));
            const comparison = document.createElement('div'); comparison.className = 'correction-comparison';
            for (const [label, row] of [['Przed', entry.before], ['Po', entry.after]]) {
                const column = document.createElement('div'); column.append(text('h5', label), text('pre', workout(row))); comparison.append(column);
            }
            details.append(comparison); el('entries').append(details);
        }
        el('weeks').hidden = !(value.cycles?.length || value.weeks?.length);
        controls();
        el('outcome-title').tabIndex = -1;
        el('outcome-title').focus({preventScroll:true});
        el('outcome-title').scrollIntoView({block:'start',behavior:'smooth'});
    }
    async function history() {
        const result = await request(''); el('history').replaceChildren();
        result.items.forEach(item => {
            const button = document.createElement('button'); button.type = 'button';
            button.textContent = `${item.start} – ${item.end} — ${stateLabel(item)}`;
            button.addEventListener('click', () => run(async () => { showPreview(await request(`/${item.id}`)); status('Otwarta zapisana wersja planu.'); }));
            el('history').append(button);
        });
    }
    async function profileRequest(path='',options) {
        const current = epoch, result = await chatRequest(`/profile${path}`, options);
        if (current !== epoch) throw new Error('Dostęp został zamknięty.');
        return result;
    }
    async function load() {
        const selected = el('goal').value, emptyStart = !el('start').value;
        [calendar, profile] = await Promise.all([profileRequest('/calendar'), profileRequest()]);
        const confirmed = calendar.items.find(r => Object.entries(r).every(([key,value]) => key === 'key' || profile.goal?.[key] === value));
        el('goal').replaceChildren(...calendar.items.map(r => new Option(`${r.name} · ${r.date} · ${r.distance_km} km · ${r.target_time || 'ukończenie'}`,r.key)));
        if (calendar.items.some(r => r.key === selected)) el('goal').value = selected;
        else if (confirmed) el('goal').value = confirmed.key;
        if (emptyStart) { const day = new Date(`${profile.today}T12:00:00Z`); day.setUTCDate(day.getUTCDate()+1); el('start').value = day.toISOString().slice(0,10); }
        context = null;
        if (confirmed && el('goal').value === confirmed.key) {
            context = await request('/context');
            el('calendar').replaceChildren(...context.races.map(race => text('p', `${race.date} — ${race.name} — ${race.distance_km} km — ${race.priority}`)));
            if (emptyStart) el('start').value = context.default_start;
        }
        await history(); controls();
    }
    el('goal').addEventListener('change', () => { context = null; clarificationId = null; preview = null; el('preview').hidden = el('error').hidden = true; controls(); });
    el('start').addEventListener('change', () => { preview=null; el('preview').hidden=el('error').hidden=true; controls(); });
    el('goal-confirm').addEventListener('click', () => run(async () => {
        if (!profile || !calendar || !el('goal').value) return;
        const body = {version:profile.version,change:{kind:'goal',calendar_version:calendar.version,race_key:el('goal').value}}, hash=JSON.stringify(body);
        if (!goalPending || goalPending.hash !== hash) goalPending={hash,id:crypto.randomUUID()};
        const proposal = await profileRequest('/proposals',{method:'POST',body:JSON.stringify({id:goalPending.id,...body})});
        await profileRequest(`/proposals/${proposal.id}/decision`,{method:'POST',body:JSON.stringify({decision:'accept'})});
        goalPending=null; context=null; preview=null; clarificationId=null; el('preview').hidden=true;
        document.dispatchEvent(new Event('athlete-profile-updated'));
        await load(); status('Cel potwierdzony. Ustal początek przygotowań i poproś o propozycję planu.');
    }));
    el('load').addEventListener('click', () => run(async () => { await load(); status(context?.active_plan?.calendar_changed ? 'Kalendarz zmienił się. Przygotuj aktualizację przyszłej części planu i sprawdź podgląd.' : 'Aktualny kalendarz wczytany.'); }));
    document.addEventListener('coach-access-opened', () => run(async () => { await load(); status(context?.active_plan?.calendar_changed ? 'Kalendarz zmienił się. Przygotuj aktualizację przyszłej części planu.' : ''); }));
    el('generate').addEventListener('submit', event => {
        event.preventDefault(); run(async () => {
            const current = epoch;
            el('error').hidden = true;
            try {
                preview = null; el('preview').hidden = true; el('coaching').replaceChildren(); controls();
                status('Pobieram aktualne dane i przygotowuję propozycję…');
                await load();
                if (!context) throw new Error('Potwierdź wybrany cel główny przed przygotowaniem planu.');
                const body = {plan_version: context.plan_version, calendar_version: context.calendar_version, athlete_version: context.athlete_version,
                    start: el('start').value, end: context.default_end, replace_existing: true, note: el('note').value};
                if (context.active_plan && body.start === context.active_plan.start) body.parent_plan_id = context.active_plan.id;
                if (clarificationId) body.clarification_id = clarificationId;
                const hash = JSON.stringify(body);
                if (!pending || pending.hash !== hash) pending = {hash, id: crypto.randomUUID()};
                status('Trener analizuje historię i układa cykl 10-dniowy…');
                showPreview(await request('/preview', {method: 'POST', body: JSON.stringify({id: pending.id, ...body})}));
                pending = null; status(outcome(preview)[0] + '. Szczegóły poniżej.');
                await history();
            } catch (error) {
                if (current === epoch && !preview) {
                    el('error').hidden = false;
                    el('error-message').textContent = error.message;
                    el('error-issues').replaceChildren(...(error.issues || []).map(item => text('li',item)));
                    el('error-reference').textContent = error.reference ? `Kod zgłoszenia: ${error.reference}. Podaj go, jeśli problem się powtórzy.` : '';
                }
                throw error;
            }
        });
    });
    el('error-retry').addEventListener('click', () => { if (!busy) el('generate').requestSubmit(); });
    for (const decision of ['accept', 'reject']) el(decision).addEventListener('click', () => run(async () => {
        if (decision === 'accept') { preview.status = 'writing'; controls(); }
        showPreview(await request(`/${preview.id}/decision`, {method: 'POST', body: JSON.stringify({decision})}));
        status(preview.status === 'applied' ? 'Plan zapisany i potwierdzony w Google Sheets.' : 'Wersja odrzucona.'); await load();
    }));
    document.addEventListener('athlete-profile-updated', () => {
        context = null;
        el('error').hidden = true;
        if (preview?.status === 'preview') { preview.status = 'stale'; controls(); }
        if (!busy && coachChat.ready) run(load);
    });
    document.addEventListener('coach-access-closed', () => {
        epoch++; context = preview = pending = clarificationId = profile = calendar = goalPending = null;
        ['calendar', 'history', 'entries', 'weeks', 'warnings', 'blockers', 'coaching'].forEach(name => el(name).replaceChildren());
        el('preview').hidden = true; ['start', 'note'].forEach(name => { el(name).value = ''; }); el('goal').replaceChildren(); el('extra').open = false;
        el('error').hidden = true; el('error-message').textContent = el('error-reference').textContent = ''; el('error-issues').replaceChildren();
        el('summary').textContent = ''; status('');
    });
    controls();
})();

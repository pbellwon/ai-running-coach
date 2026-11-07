// The athlete asks for a proposal; PaceMind chooses the ten-day training cycle from evidence.
(() => {
    const el = name => document.getElementById(`race-${name}`);
    const labels = {preview: 'Do akceptacji', writing: 'Zapis do sprawdzenia', applied: 'Zapisany', rejected: 'Odrzucony', stale: 'Nieaktualny'};
    let context = null, preview = null, busy = false, epoch = 0, pending = null;
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
        if (value.coaching && value.coaching.status !== 'ready') return ['Trener potrzebuje odpowiedzi', 'Plan nie został jeszcze ułożony. Odpowiedz na pytanie poniżej w polu „Dopowiedz trenerowi”, a następnie kliknij „Zaproponuj mój plan”.'];
        if (!changes) return ['Brak zmian do zapisania', 'Nie powstała propozycja zmiany treningów. To nie potwierdza, że obecny plan jest optymalny. Sprawdź powód poniżej — jednostki mogą być zachowane lub chronione.'];
        if (!value.can_accept) return ['Propozycja wymaga wyjaśnienia', 'Zapis jest zablokowany. Najpierw rozstrzygnij wskazane poniżej pytania lub konflikty.'];
        return ['Propozycja planu gotowa', `PaceMind proponuje ${value.summary.added} nowych i ${value.summary.replaced} przebudowanych jednostek. Nic nie zostało jeszcze zapisane. Pierwsze zmiany są rozwinięte poniżej — sprawdź porównanie „Przed / Po” przed akceptacją.`];
    }
    function controls() {
        document.querySelectorAll('#race-planning button, #race-planning input, #race-planning textarea').forEach(node => { node.disabled = busy; });
        const changes = Number(preview?.summary?.added || 0) + Number(preview?.summary?.replaced || 0);
        const writable = preview?.planning_mode === 'personal-10-day' && preview.can_accept && changes > 0;
        el('accept').hidden = !preview || !(preview.status === 'writing' || (preview.status === 'preview' && writable));
        if (preview) {
            const [title, message] = outcome(preview);
            el('outcome-title').textContent = title; el('outcome').textContent = message;
        }
        el('accept').disabled = busy || !preview || !(preview.status === 'writing' || (preview.status === 'preview' && writable));
        el('reject').disabled = busy || !preview || preview.status !== 'preview';
        el('generate').setAttribute('aria-busy', String(busy));
        el('generate').querySelector('button[type=submit]').textContent = busy ? 'Przetwarzanie…' : 'Zaproponuj mój plan';
        el('accept').textContent = preview?.status === 'writing' ? 'Sprawdź wynik poprzedniego zapisu planu' : 'Akceptuję plan i zapisuję do Google Sheets';
    }
    async function run(fn) {
        if (busy) return;
        const current = epoch;
        busy = true; controls();
        try { await fn(); } catch (error) { if (current === epoch) status(error.message); }
        finally { busy = false; controls(); }
    }
    const workout = row => row ? `${row.date} — ${row.title}\nDystans: ${row.planned_distance_km || 'nie określono'} km\nCzas: ${row.planned_duration_min || 'nie określono'} min\n\n${row.description}` : 'Brak treningu.';
    function showPreview(value) {
        preview = value; el('preview').hidden = false; el('coaching').replaceChildren();
        const coaching = value.coaching;
        if (coaching) {
            el('coaching').append(text('h4', 'Dlaczego taki plan?'), text('p', coaching.explanation), text('p', coaching.anchor_note));
            const evidence = document.createElement('ul');
            coaching.evidence.forEach(id => evidence.append(text('li', (value.sources || []).find(source => source.id === id)?.label || ({calendar: 'Kalendarz startów', athlete_note: 'Twoje bieżące dopowiedzenie'}[id] || id))));
            el('coaching').append(evidence);
            if (coaching.questions.length) el('coaching').append(text('p', 'Odpowiedz w polu „Dopowiedz trenerowi” i poproś o nową propozycję.'));
        }
        if (value.limitations?.length) {
            const details = document.createElement('details'); details.append(text('summary', 'Źródła i ograniczenia danych'));
            value.limitations.forEach(item => details.append(text('p', item))); el('coaching').append(details);
        }
        el('summary').textContent = `${value.start} – ${value.end}: dodane ${value.summary.added}, przebudowane ${value.summary.replaced}, zachowane ${value.summary.kept}. Stan: ${labels[value.status] || value.status}.`;
        for (const [name, items] of [['warnings', value.warnings], ['blockers', value.blockers]]) el(name).replaceChildren(...items.map(item => text('li', item)));
        const table = document.createElement('table'), header = document.createElement('tr');
        ['Cykl od', 'Do', 'Etap', 'Propozycja km', 'Plan km'].forEach(name => header.append(text('th', name))); table.append(header);
        (value.cycles || value.weeks || []).forEach(cycle => {
            const row = document.createElement('tr');
            [cycle.start || cycle.week_start, cycle.end || 'Archiwalny tydzień', cycle.phase, cycle.budget_km, cycle.planned_km].forEach(item => row.append(text('td', item))); table.append(row);
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
    }
    async function history() {
        const result = await request(''); el('history').replaceChildren();
        result.items.forEach(item => {
            const button = document.createElement('button'); button.type = 'button';
            button.textContent = `${item.start} – ${item.end} — ${labels[item.status] || item.status}`;
            button.addEventListener('click', () => run(async () => { showPreview(await request(`/${item.id}`)); status('Otwarta zapisana wersja planu.'); }));
            el('history').append(button);
        });
    }
    async function load() {
        context = await request('/context'); await history();
        el('calendar').replaceChildren(...context.races.map(race => text('p', `${race.date} — ${race.name} — ${race.distance_km} km — ${race.priority}`)));
        if (!el('start').value) el('start').value = context.default_start;
        if (!el('end').value) el('end').value = context.default_end || '';
    }
    el('load').addEventListener('click', () => run(async () => { await load(); status('Aktualne dane wczytane.'); }));
    el('generate').addEventListener('submit', event => {
        event.preventDefault(); run(async () => {
            preview = null; el('preview').hidden = true; el('coaching').replaceChildren(); controls();
            status('Pobieram aktualne dane i przygotowuję propozycję…');
            await load();
            const body = {plan_version: context.plan_version, calendar_version: context.calendar_version, athlete_version: context.athlete_version,
                start: el('start').value, end: el('end').value, replace_existing: el('replace').checked, note: el('note').value};
            const hash = JSON.stringify(body);
            if (!pending || pending.hash !== hash) pending = {hash, id: crypto.randomUUID()};
            status('Trener analizuje historię i układa cykl 10-dniowy…');
            showPreview(await request('/preview', {method: 'POST', body: JSON.stringify({id: pending.id, ...body})}));
            pending = null; status(outcome(preview)[0] + '. Szczegóły poniżej.');
            await history();
        });
    });
    for (const decision of ['accept', 'reject']) el(decision).addEventListener('click', () => run(async () => {
        if (decision === 'accept') { preview.status = 'writing'; controls(); }
        showPreview(await request(`/${preview.id}/decision`, {method: 'POST', body: JSON.stringify({decision})}));
        status(preview.status === 'applied' ? 'Plan zapisany i potwierdzony w Google Sheets.' : 'Wersja odrzucona.'); await history();
    }));
    document.addEventListener('athlete-profile-updated', () => {
        context = null;
        if (preview?.status === 'preview') { preview.status = 'stale'; controls(); }
    });
    document.addEventListener('coach-access-closed', () => {
        epoch++; context = preview = pending = null;
        ['calendar', 'history', 'entries', 'weeks', 'warnings', 'blockers', 'coaching'].forEach(name => el(name).replaceChildren());
        el('preview').hidden = true; ['start', 'end', 'note'].forEach(name => { el(name).value = ''; });
        el('summary').textContent = ''; status('');
    });
    controls();
})();

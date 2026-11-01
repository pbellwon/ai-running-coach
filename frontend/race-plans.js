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
    function controls() {
        document.querySelectorAll('#race-planning button, #race-planning input, #race-planning textarea').forEach(node => { node.disabled = busy; });
        const writable = preview?.planning_mode === 'personal-10-day' && preview.can_accept;
        el('accept').disabled = busy || !preview || !(preview.status === 'writing' || (preview.status === 'preview' && writable));
        el('reject').disabled = busy || !preview || preview.status !== 'preview';
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
        for (const entry of value.entries) {
            const details = document.createElement('details');
            const action = {add: 'Dodany', replace: 'Przebudowany', keep: 'Zachowany'}[entry.action];
            details.append(text('summary', `${entry.after.date}${entry.cycle_day ? ` · dzień ${entry.cycle_day}/10` : ''} — ${entry.after.title} — ${action}`));
            const comparison = document.createElement('div'); comparison.className = 'correction-comparison';
            for (const [label, row] of [['Przed', entry.before], ['Po', entry.after]]) {
                const column = document.createElement('div'); column.append(text('h5', label), text('pre', workout(row))); comparison.append(column);
            }
            details.append(comparison); el('entries').append(details);
        }
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
            await load();
            const body = {plan_version: context.plan_version, calendar_version: context.calendar_version, athlete_version: context.athlete_version,
                start: el('start').value, end: el('end').value, replace_existing: el('replace').checked, note: el('note').value};
            const hash = JSON.stringify(body);
            if (!pending || pending.hash !== hash) pending = {hash, id: crypto.randomUUID()};
            status('Trener analizuje historię i układa cykl 10-dniowy…');
            showPreview(await request('/preview', {method: 'POST', body: JSON.stringify({id: pending.id, ...body})}));
            pending = null; await history(); status(preview.coaching?.status === 'ready' ? 'Propozycja gotowa. Sprawdź uzasadnienie i plan przed akceptacją.' : 'Trener potrzebuje doprecyzowania przed ułożeniem planu.');
        });
    });
    for (const decision of ['accept', 'reject']) el(decision).addEventListener('click', () => run(async () => {
        if (decision === 'accept') { preview.status = 'writing'; controls(); }
        showPreview(await request(`/${preview.id}/decision`, {method: 'POST', body: JSON.stringify({decision})}));
        status(preview.status === 'applied' ? 'Plan zapisany i potwierdzony w Google Sheets.' : 'Wersja odrzucona.'); await history();
    }));
    document.addEventListener('coach-access-closed', () => {
        epoch++; context = preview = pending = null;
        ['calendar', 'history', 'entries', 'weeks', 'warnings', 'blockers', 'coaching'].forEach(name => el(name).replaceChildren());
        el('preview').hidden = true; ['start', 'end', 'note'].forEach(name => { el(name).value = ''; });
        el('summary').textContent = ''; status('');
    });
    controls();
})();

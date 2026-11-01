// A version is immutable after preview. Acceptance sends its UUID, never edited rows.
(() => {
    const el = name => document.getElementById(`race-${name}`);
    const days = ['Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota', 'Niedziela'];
    const labels = {preview: 'Do akceptacji', writing: 'Zapis do sprawdzenia', applied: 'Zapisany', rejected: 'Odrzucony', stale: 'Nieaktualny'};
    let context = null, preview = null, busy = false, epoch = 0, pending = null;
    const text = (tag, value) => { const node = document.createElement(tag); node.textContent = value; return node; };
    const status = value => { el('status').textContent = value; };
    async function request(path, options) {
        const current = epoch;
        const result = await chatRequest(`/race-plans${path}`, options);
        if (current !== epoch) throw new Error('Dostęp został zamknięty.');
        return result;
    }
    function controls() {
        document.querySelectorAll('#race-planning button, #race-planning input, #race-planning select').forEach(node => { node.disabled = busy; });
        el('accept').disabled = busy || !preview || !preview.can_accept || !['preview', 'writing'].includes(preview.status);
        el('reject').disabled = busy || !preview || preview.status !== 'preview';
        el('accept').textContent = preview?.status === 'writing' ? 'Sprawdź wynik poprzedniego zapisu planu' : 'Akceptuję cały podgląd i zapisuję plan do Google Sheets';
    }
    async function run(fn) {
        if (busy) return;
        const current = epoch;
        busy = true; controls();
        try { await fn(); } catch (error) { if (current === epoch) status(error.message); }
        finally { busy = false; controls(); }
    }
    days.forEach((day, i) => {
        const row = document.createElement('div');
        const label = document.createElement('label'), checkbox = document.createElement('input');
        checkbox.type = 'checkbox'; checkbox.id = `race-day-${i}`; checkbox.checked = [1, 3, 5, 6].includes(i);
        label.append(checkbox, document.createTextNode(day));
        const capLabel = document.createElement('label'), cap = document.createElement('input');
        cap.type = 'number'; cap.id = `race-cap-${i}`; cap.min = '15'; cap.max = '240'; cap.required = true; cap.value = i === 6 ? '90' : '60';
        capLabel.append(document.createTextNode('Limit minut'), cap);
        row.append(label, capLabel); el('days').append(row);
        el('long-day').append(new Option(day, i));
    });
    el('long-day').value = '6';
    function preferenceValue() {
        return {weekdays: days.flatMap((_, i) => el(`day-${i}`).checked ? [i] : []), long_run_day: Number(el('long-day').value),
            weekly_distance_km: Number(el('weekly-km').value), easy_pace_min_km: Number(el('easy-pace').value),
            max_minutes: Object.fromEntries(days.map((_, i) => [String(i), Number(el(`cap-${i}`).value)]))};
    }
    const fingerprint = p => p && JSON.stringify([p.weekdays, p.long_run_day, p.weekly_distance_km, p.easy_pace_min_km, days.map((_, i) => p.max_minutes[String(i)])]);
    function showPreferences(value) {
        days.forEach((_, i) => {
            el(`day-${i}`).checked = value.weekdays.includes(i);
            el(`cap-${i}`).value = value.max_minutes[String(i)];
        });
        el('long-day').value = String(value.long_run_day); el('weekly-km').value = value.weekly_distance_km;
        el('easy-pace').value = value.easy_pace_min_km;
    }
    const workout = row => row ? `${row.date} — ${row.title}\nDystans: ${row.planned_distance_km || 'nie określono'} km\nCzas: ${row.planned_duration_min || 'nie określono'} min\n\n${row.description}` : 'Brak treningu w tym dniu.';
    function showPreview(value) {
        preview = value; el('preview').hidden = false; el('generate').hidden = true;
        el('summary').textContent = `${value.start} – ${value.end}: dodane ${value.summary.added}, przebudowane ${value.summary.replaced}, zachowane ${value.summary.kept}. Stan: ${labels[value.status] || value.status}.`;
        for (const [name, list] of [['warnings', value.warnings], ['blockers', value.blockers]]) el(name).replaceChildren(...list.map(item => text('li', item)));
        const table = document.createElement('table'), header = document.createElement('tr');
        ['Tydzień od', 'Etap', 'Najbliższy start A', 'Budżet km', 'Plan km'].forEach(name => header.append(text('th', name)));
        table.append(header);
        value.weeks.forEach(week => {
            const row = document.createElement('tr');
            [week.week_start, week.phase, week.focus, week.budget_km, week.planned_km].forEach(item => row.append(text('td', item)));
            table.append(row);
        });
        el('weeks').replaceChildren(table); el('entries').replaceChildren();
        for (const entry of value.entries) {
            const details = document.createElement('details');
            const action = {add: 'Dodany', replace: 'Przebudowany', keep: 'Zachowany'}[entry.action];
            details.append(text('summary', `${entry.after.date} — ${entry.after.title} — ${action} — ${entry.phase}`));
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
            const row = document.createElement('div'), button = document.createElement('button'); button.type = 'button';
            button.textContent = `${item.start} – ${item.end} — ${labels[item.status] || item.status} (${new Date(item.created_at).toLocaleString('pl-PL')})`;
            button.addEventListener('click', () => run(async () => { showPreview(await request(`/${item.id}`)); status('Otwarta zapisana wersja planu.'); }));
            row.append(button); el('history').append(row);
        });
    }
    el('load').addEventListener('click', () => run(async () => {
        const value = await request('/context'); await history(); context = value; preview = pending = null;
        el('preview').hidden = true; el('calendar').replaceChildren();
        value.races.forEach(race => el('calendar').append(text('p', `${race.date} — ${race.name} — ${race.distance_km} km — ${race.priority}${race.target_time ? ` — cel: ${race.target_time}` : ''}${race.notes ? ` — ${race.notes}` : ''}`)));
        if (!value.races.length) el('calendar').append(text('p', 'Brak przyszłych startów. Uzupełnij race_calendar, w tym start główny A.'));
        el('preferences').hidden = false; el('generate').hidden = false;
        if (value.preferences.value) showPreferences(value.preferences.value);
        el('volume-hint').textContent = value.recent_weekly_km === null ? 'Brak zarejestrowanych biegów w ostatnich 28 dniach. Wpisz własną aktualną objętość.' : `Zarejestrowane biegi z ostatnich 28 dni: średnio ${value.recent_weekly_km} km/tydzień. Zweryfikuj kompletność danych przed wyborem objętości.`;
        el('start').value = value.default_start; el('start').min = value.default_start;
        el('end').value = value.default_end || ''; el('replace').checked = false;
        status('Wczytano aktualny kalendarz i plan. Zapisz preferencje przed generowaniem.');
    }));
    el('preferences').addEventListener('submit', event => {
        event.preventDefault(); run(async () => {
            const value = preferenceValue();
            if (value.weekdays.length < 2 || value.weekdays.length > 6) throw new Error('Wybierz od 2 do 6 dni treningowych.');
            if (!value.weekdays.includes(value.long_run_day)) throw new Error('Długi bieg musi przypadać w wybrany dzień treningowy.');
            context.preferences = await request('/preferences', {method: 'PUT', body: JSON.stringify({version: context.preferences.version, value})});
            preview = null; el('preview').hidden = true; el('generate').hidden = false;
            status('Preferencje zapisane. Możesz przygotować nową wersję planu.');
        });
    });
    el('generate').addEventListener('submit', event => {
        event.preventDefault(); run(async () => {
            if (fingerprint(preferenceValue()) !== fingerprint(context.preferences.value)) throw new Error('Najpierw zapisz aktualne preferencje.');
            const body = {plan_version: context.plan_version, calendar_version: context.calendar_version, preferences_version: context.preferences.version,
                start: el('start').value, end: el('end').value, replace_existing: el('replace').checked};
            const hash = JSON.stringify(body);
            if (!pending || pending.hash !== hash) pending = {hash, id: crypto.randomUUID()};
            showPreview(await request('/preview', {method: 'POST', body: JSON.stringify({id: pending.id, ...body})}));
            pending = null; await history(); status('Podgląd gotowy. Sprawdź tygodnie, wszystkie jednostki oraz ostrzeżenia przed akceptacją.');
        });
    });
    for (const decision of ['accept', 'reject']) el(decision).addEventListener('click', () => run(async () => {
        const id = preview.id;
        if (decision === 'accept') { preview.status = 'writing'; controls(); }
        showPreview(await request(`/${id}/decision`, {method: 'POST', body: JSON.stringify({decision})}));
        status(preview.status === 'applied' ? 'Plan zapisany i potwierdzony w Google Sheets.' : 'Wersja odrzucona; arkusz pozostał bez zmian.');
        await history();
    }));
    document.addEventListener('coach-access-closed', () => {
        epoch++; context = preview = pending = null;
        ['calendar', 'history', 'entries', 'weeks', 'warnings', 'blockers'].forEach(name => el(name).replaceChildren());
        ['preferences', 'generate', 'preview'].forEach(name => { el(name).hidden = true; });
        ['weekly-km', 'easy-pace', 'start', 'end'].forEach(name => { el(name).value = ''; });
        el('summary').textContent = el('volume-hint').textContent = ''; status('');
    });
    controls();
})();

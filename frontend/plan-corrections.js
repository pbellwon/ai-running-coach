// Preview is an immutable server record; acceptance only sends its UUID.
(() => {
    const el = id => document.getElementById(`corrections-${id}`);
    let plan = null, preview = null, busy = false;
    const status = text => { el('status').textContent = text; };
    const fields = ['title', 'distance', 'duration', 'description', 'reason'];
    const show = row => JSON.stringify(row, null, 2);
    function controls() {
        document.querySelectorAll('#plan-corrections button, #plan-corrections input, #plan-corrections select, #plan-corrections textarea')
            .forEach(node => { node.disabled = busy; });
        el('accept').disabled = busy || !preview || !['preview', 'writing'].includes(preview.status);
        el('reject').disabled = busy || !preview || preview.status !== 'preview';
    }
    async function run(fn) {
        if (busy) return;
        busy = true; controls();
        try { await fn(); } catch (error) { status(error.message); }
        finally { busy = false; controls(); }
    }
    function renderPreview(value) {
        preview = value;
        el('before').textContent = show(value.before);
        el('after').textContent = show(value.after);
        el('preview').hidden = false;
        // Keep the immutable preview separate from any later edits to the form.
        el('form').hidden = true;
        el('accept').textContent = value.status === 'writing' ? 'Sprawdź wynik poprzedniego zapisu' : 'Akceptuję tę zmianę i zapisuję do Google Sheets';
        controls();
    }
    function populate() {
        const row = plan.items.find(item => item.row === Number(el('workout').value));
        if (!row) return;
        let title = row.title, distance = row.planned_distance_km.replace(',', '.'), duration = row.planned_duration_min.replace(',', '.');
        let description = row.description;
        if (el('kind').value === 'rest') {
            title = 'Odpoczynek'; distance = '0'; duration = '0'; description = 'Dzień bez treningu biegowego. Odpoczynek i regeneracja.';
        } else if (el('kind').value === 'easy') {
            title = 'Spokojny bieg';
            distance = distance ? String(Math.round(Number(distance) * 7) / 10) : '';
            duration = duration ? String(Math.round(Number(duration) * 0.7)) : '';
            description = `Spokojny bieg w tempie konwersacyjnym, bez akcentów i szybkiego finiszu. ${distance ? `Dystans ${distance} km.` : ''} ${duration ? `Czas orientacyjny ${duration} min.` : ''}`;
        }
        el('title').value = title; el('distance').value = distance; el('duration').value = duration; el('description').value = description;
    }
    async function history() {
        const result = await chatRequest('/corrections');
        el('history').replaceChildren();
        for (const item of result.items) {
            const details = document.createElement('details'), label = document.createElement('summary'), body = document.createElement('pre');
            label.textContent = `${item.before.date} — ${item.before.title} — ${item.status}`;
            body.textContent = show({oryginał: item.before, korekta: item.after, uzasadnienie: item.reason, data: item.created_at});
            details.append(label, body);
            if (['preview', 'writing'].includes(item.status)) {
                const button = document.createElement('button'); button.type = 'button';
                button.textContent = item.status === 'writing' ? 'Sprawdź wynik zapisu' : 'Otwórz zapisany podgląd';
                button.addEventListener('click', () => { if (!busy) renderPreview(item); }); details.append(button);
            }
            el('history').append(details);
        }
    }
    el('load').addEventListener('click', () => run(async () => {
        plan = await chatRequest('/corrections/plan');
        await history(); preview = null; el('preview').hidden = true;
        el('workout').replaceChildren(...plan.items.map(item => new Option(`${item.date} — ${item.title} (wiersz ${item.row})`, item.row)));
        el('form').hidden = !plan.items.length; populate(); status(plan.items.length ? 'Aktualny plan wczytany.' : 'Brak nadchodzących treningów.');
    }));
    el('workout').addEventListener('change', populate); el('kind').addEventListener('change', populate);
    let pending = null;
    el('form').addEventListener('submit', event => {
        event.preventDefault();
        run(async () => {
            const body = {version: plan.version, row: Number(el('workout').value), reason: el('reason').value,
                change: {title: el('title').value, description: el('description').value,
                    planned_distance_km: el('distance').value === '' ? null : Number(el('distance').value),
                    planned_duration_min: el('duration').value === '' ? null : Number(el('duration').value)}};
            const fingerprint = JSON.stringify(body);
            if (!pending || pending.fingerprint !== fingerprint) pending = {fingerprint, id: crypto.randomUUID()};
            renderPreview(await chatRequest('/corrections/preview', {method: 'POST', body: JSON.stringify({id: pending.id, ...body})}));
            pending = null; status('Sprawdź pełną treść przed i po, w tym końcową notkę PaceMind.');
        });
    });
    for (const [id, decision] of [['accept', 'accept'], ['reject', 'reject']]) {
        el(id).addEventListener('click', () => run(async () => {
            const value = await chatRequest(`/corrections/${preview.id}/decision`, {method: 'POST', body: JSON.stringify({decision})});
            renderPreview(value); status(value.status === 'applied' ? 'Zaakceptowana zmiana zapisana i potwierdzona w Google Sheets.' : 'Zmiana odrzucona.');
            await history();
        }));
    }
    // Access closure also removes private plan data from the current document.
    document.addEventListener('coach-access-closed', () => {
        plan = preview = pending = null;
        fields.forEach(name => { el(name).value = ''; });
        el('before').textContent = el('after').textContent = ''; el('history').replaceChildren();
        el('form').hidden = el('preview').hidden = true; status('');
    });
})();

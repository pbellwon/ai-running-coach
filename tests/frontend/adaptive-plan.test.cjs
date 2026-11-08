const { test, before, after, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const path = require('node:path');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '../..');
const origin = 'http://127.0.0.1:18765';
const productionAPI = 'https://pacemind-backend-1034229547127.europe-central2.run.app';
let server, browser, temp, logs = '';

before(async () => {
    temp = mkdtempSync(path.join(tmpdir(), 'pacemind-browser-'));
    server = spawn(path.join(root, 'backend/.venv/bin/python'), [
        '-m', 'uvicorn', 'fixture_app:app', '--host', '127.0.0.1', '--port', '18765',
    ], {
        cwd: path.join(root, 'backend'),
        env: {
            ...process.env,
            PYTHONPATH: [path.join(root, 'backend'), __dirname].join(path.delimiter),
            DATABASE_URL: `sqlite:///${temp}/decisions.db`,
        },
        stdio: ['ignore', 'pipe', 'pipe'],
    });
    server.stdout.on('data', chunk => { logs += chunk; });
    server.stderr.on('data', chunk => { logs += chunk; });
    for (let attempt = 0; attempt < 100; attempt++) {
        if (server.exitCode !== null) throw new Error(logs);
        try {
            if ((await fetch(`${origin}/health`)).ok) break;
        } catch {}
        if (attempt === 99) throw new Error(`Fixture did not start: ${logs}`);
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    browser = await chromium.launch({
        executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
        headless: true,
    });
});

beforeEach(async () => {
    assert.equal((await fetch(`${origin}/__test__/reset`, { method: 'POST' })).status, 200);
});

after(async () => {
    if (browser) await browser.close();
    if (server && server.exitCode === null) {
        await new Promise(resolve => { server.once('exit', resolve); server.kill(); });
    }
    if (temp) rmSync(temp, { recursive: true, force: true });
});

async function openDashboard(t, interceptDecision) {
    const context = await browser.newContext();
    t.after(async () => { await context.unrouteAll({behavior: 'wait'}); await context.close(); });
    // Every request to the production hostname is intercepted; no production
    // request is sent. Adaptive routes run against the actual local API/SQLite.
    await context.route(`${productionAPI}/**`, async route => {
        if (route.request().method() === 'POST' && interceptDecision
            && await interceptDecision(route)) return;
        const response = await route.fetch({
            url: `${origin}${new URL(route.request().url()).pathname}${new URL(route.request().url()).search}`,
        });
        await route.fulfill({ response });
    });
    const page = await context.newPage();
    page.observedRequests = [];
    page.on("request", request => page.observedRequests.push(request.url()));
    await page.goto(`${origin}/index.html`);
    await page.locator('#dashboard').waitFor({ state: 'visible' });
    await page.locator('#adaptive-plan-accept').waitFor({ state: 'visible' });
    return page;
}

for (const [button, label] of [['accept', 'Zaakceptowano'], ['reject', 'Odrzucono']]) {
    test(`${button}: click, persist in SQLite, and reload in a new browser context`, async t => {
        const page = await openDashboard(t);
        await page.locator(`#adaptive-plan-${button}`).click();
        await page.locator('#adaptive-plan-status').filter({ hasText: label }).waitFor();
        assert.equal(await page.locator('#adaptive-plan-accept').isDisabled(), true);
        assert.equal(await page.locator('#adaptive-plan-reject').isDisabled(), true);
        // A fresh context rules out localStorage/sessionStorage as persistence.
        const reopened = await openDashboard(t);
        assert.match(await reopened.locator('#adaptive-plan-status').textContent(), new RegExp(label));
        assert.equal(await reopened.locator('#adaptive-plan-accept').isDisabled(), true);
        await fetch(`${origin}/__test__/change-proposal`, { method: 'POST' });
        await reopened.reload();
        await reopened.locator('#dashboard').waitFor({ state: 'visible' });
        assert.equal(await reopened.locator('#adaptive-plan-accept').isEnabled(), true);
        assert.doesNotMatch(await reopened.locator('#adaptive-plan-status').textContent(), /Decyzja została zapisana/);
    });
}

test('failed save permits retry and never shows false success', async t => {
    let failed = false;
    const page = await openDashboard(t, async route => {
        if (!failed) {
            failed = true;
            await route.fulfill({ status: 503, contentType: 'application/json', body: '{}' });
            return true;
        }
        return false;
    });
    await page.locator('#adaptive-plan-accept').click();
    await page.locator('#adaptive-plan-status').filter({ hasText: 'Nie udało się' }).waitFor();
    assert.equal(await page.locator('#adaptive-plan-accept').isEnabled(), true);
    assert.equal(await page.locator('#adaptive-plan-reject').isEnabled(), true);
    await page.locator('#adaptive-plan-accept').click();
    await page.locator('#adaptive-plan-status').filter({ hasText: 'Zaakceptowano' }).waitFor();
});

test('pending request disables both controls and sends one decision', async t => {
    let release, reached;
    const blocked = new Promise(resolve => { release = resolve; });
    const intercepted = new Promise(resolve => { reached = resolve; });
    let posts = 0;
    const page = await openDashboard(t, async () => {
        posts++;
        reached();
        await blocked;
        return false;
    });
    try {
        await page.locator('#adaptive-plan-accept').click();
        await intercepted;
        assert.equal(await page.locator('#adaptive-plan-accept').isDisabled(), true);
        assert.equal(await page.locator('#adaptive-plan-reject').isDisabled(), true);
        await page.locator('#adaptive-plan-accept').evaluate(button => button.click());
        assert.equal(posts, 1);
    } finally {
        release();
    }
    await page.locator('#adaptive-plan-status').filter({ hasText: 'Zaakceptowano' }).waitFor();
});

test('stale proposal prompts refresh instead of recording acceptance', async t => {
    const page = await openDashboard(t);
    await fetch(`${origin}/__test__/change-proposal`, { method: 'POST' });
    await page.locator('#adaptive-plan-accept').click();
    await page.locator('#adaptive-plan-status').filter({ hasText: 'Propozycja zmieniła się' }).waitFor();
    assert.equal(await page.locator('#adaptive-plan-accept').isDisabled(), true);
    await page.reload();
    await page.locator('#dashboard').waitFor({ state: 'visible' });
    assert.equal(await page.locator('#adaptive-plan-accept').isEnabled(), true);
});

async function waitForOverviews(page) {
    for (const days of [7, 28]) {
        await page.locator(`#training-overview-${days}[aria-busy="true"]`).waitFor({state: 'hidden'});
        await page.locator(`#overview-${days}-state`).filter({hasText: /Wykonane treningi|Brak zapisanych/}).waitFor();
    }
}

test('today ends with rolling 7-day and 28-day summaries instead of a week tab', async t => {
    const page = await openDashboard(t);
    await waitForOverviews(page);
    assert.deepEqual(await page.locator('.app-navigation a').allTextContents(), ['Dzisiaj', 'Trener']);
    assert.equal(await page.locator('#view-week, .weekly-shortcut').count(), 0);
    assert.equal(page.observedRequests.some(url => url.includes('/review/week')), false);
    assert.match(await page.locator('#overview-7-running').textContent(), /16 km/);
    assert.equal(await page.locator('#overview-7-running-sessions').textContent(), '2');
    assert.match(await page.locator('#overview-28-running').textContent(), /32 km/);
    assert.equal(await page.locator('#overview-28-running-sessions').textContent(), '4');
    assert.match(await page.locator('#overview-7-period').textContent(), /23.*29.*2026/);
    assert.match(await page.locator('#overview-28-period').textContent(), /2.*29.*2026/);
    assert.deepEqual(await page.locator('#dashboard > section').evaluateAll(nodes => nodes.slice(-3).map(node => node.id || node.className)),
        ['card recent-workouts-card', 'training-overview-7', 'training-overview-28']);
});

test('empty rolling summaries show zero with an explicit no-data message', async t => {
    const page = await openDashboard(t);
    await waitForOverviews(page);
    await fetch(`${origin}/__test__/weekly-mode/empty`, {method: 'POST'});
    await page.evaluate(() => Promise.all([loadTrainingOverview(7), loadTrainingOverview(28)]));
    for (const days of [7, 28]) {
        assert.match(await page.locator(`#overview-${days}-state`).textContent(), /Brak zapisanych treningów/);
        assert.equal(await page.locator(`#overview-${days}-running`).textContent(), '0 km');
    }
});

test('failed 7-day summary stays unavailable while 28 days and today work, then retries', async t => {
    const page = await openDashboard(t);
    await waitForOverviews(page);
    let failed = false;
    await page.route(`${productionAPI}/training/overview?window_days=7`, async route => {
        if (!failed) {failed = true; await route.fulfill({status: 502, body: '{}'});}
        else await route.fulfill({response: await route.fetch({url: `${origin}/training/overview?window_days=7`})});
    });
    await page.evaluate(() => loadTrainingOverview(7));
    await page.locator('[data-overview-retry="7"]').waitFor({state: 'visible'});
    assert.equal(await page.locator('#overview-7-running').textContent(), '—');
    assert.equal(await page.locator('#overview-28-running').textContent(), '32 km');
    assert.equal(await page.locator('#adaptive-plan-accept').isEnabled(), true);
    await page.locator('[data-overview-retry="7"]').click();
    await waitForOverviews(page);
    assert.equal(await page.locator('#overview-7-running').textContent(), '16 km');
});

test('late rolling summary response cannot overwrite a newer refresh', async t => {
    const page = await openDashboard(t);
    await waitForOverviews(page);
    let release, reached, first = true;
    const blocked = new Promise(resolve => {release = resolve;});
    const intercepted = new Promise(resolve => {reached = resolve;});
    await page.route(`${productionAPI}/training/overview?window_days=7`, async route => {
        if (first) {
            first = false; reached(); await blocked;
            const data = await (await page.request.get(`${origin}/training/overview?window_days=7`)).json();
            data.running_distance_km = 999;
            await route.fulfill({json: data});
        } else await route.fulfill({response: await route.fetch({url: `${origin}/training/overview?window_days=7`})});
    });
    await page.evaluate(() => {window.olderOverview = loadTrainingOverview(7);});
    await intercepted;
    try {await page.evaluate(() => loadTrainingOverview(7));}
    finally {release();}
    await page.evaluate(() => window.olderOverview);
    assert.equal(await page.locator('#overview-7-running').textContent(), '16 km');
});

test('rolling summaries fit a mobile viewport and old week links fall back to today', async t => {
    const page = await openDashboard(t);
    await page.setViewportSize({width: 390, height: 844});
    await page.goto(`${origin}/index.html#week`);
    await page.locator('#dashboard').waitFor({state: 'visible'});
    await waitForOverviews(page);
    await page.locator('#training-overview-28').scrollIntoViewIfNeeded();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.equal(await page.locator('#view-today').isVisible(), true);
    assert.equal(await page.locator('#page-title').textContent(), 'Dzisiaj');
});

test('a server returning 28 days for a 7-day request is not displayed as 7 days', async t => {
    const page = await openDashboard(t);
    await waitForOverviews(page);
    await page.route(`${productionAPI}/training/overview?window_days=7`, async route => {
        await route.fulfill({response: await route.fetch({url: `${origin}/training/overview?window_days=28`})});
    });
    await page.evaluate(() => loadTrainingOverview(7));
    assert.match(await page.locator('#overview-7-state').textContent(), /Nie udało się/);
    assert.equal(await page.locator('#overview-7-running').textContent(), '—');
});

async function unlockChat(page) {
    await page.locator('[data-view=coach]').click();
    await page.locator('#coach-access-code').fill('fixture-private-chat-code');
    await page.getByRole('button', {name: 'Otwórz rozmowę', exact: true}).click();
    await page.locator('#coach-chat-body').waitFor({state: 'visible'});
}

test('navigation loads coach on demand and supports browser back to today', async t => {
    const page = await openDashboard(t);
    await waitForOverviews(page);
    assert.equal(page.observedRequests.some(url => url.includes('/coach/')), false);
    await page.locator('[data-view=coach]').click();
    await page.locator('#view-coach').waitFor({state: 'visible'});
    assert.equal(await page.locator('#view-today').isHidden(), true);
    await page.goBack();
    await page.locator('#dashboard').waitFor({state: 'visible'});
    assert.equal(await page.locator('#view-coach').isHidden(), true);
    await waitForOverviews(page);
});

test('chat rejects wrong code, persists history on reload, and escapes all text', async t => {
    const page = await openDashboard(t);
    await page.locator('[data-view=coach]').click();
    await page.locator('#coach-access-code').fill('wrong-code');
    await page.getByRole('button', {name: 'Otwórz rozmowę', exact: true}).click();
    await page.locator('#coach-chat-status').filter({hasText: 'Nieprawidłowy kod'}).waitFor();
    assert.equal(await page.locator('#coach-chat-body').isHidden(), true);
    await unlockChat(page);
    await page.locator('#coach-message').fill('Czy trening pomógł? <script>alert(1)</script>');
    await page.locator('#coach-send').click();
    await page.locator('#coach-chat-status').filter({hasText: 'Odpowiedź zapisana'}).waitFor();
    assert.equal(await page.locator('.coach-chat-message').count(), 2);
    assert.equal(await page.locator('#coach-chat-messages img, #coach-chat-messages script').count(), 0);
    await page.reload();
    await page.locator('.coach-chat-message[data-role=coach]').waitFor();
    assert.equal(await page.locator('.coach-chat-message').count(), 2);
    await page.getByText('Na czym opieram odpowiedź?', {exact: true}).click();
    assert.match(await page.locator('#coach-chat-messages').textContent(), /Aktualny cel: 10 km w 38:30/);
    await page.locator('#coach-lock').click();
    assert.equal(await page.locator('#coach-chat-body').isHidden(), true);
    assert.equal(await page.evaluate(() => sessionStorage.getItem('coach-code')), null);
});

test('previous weekly discussion context remains readable without the removed week screen', async t => {
    const page = await openDashboard(t);
    await page.evaluate(() => startCoachDiscussion({kind: 'week', week_start: '2026-10-19'}, 'Co dał mi ten tydzień?'));
    await page.locator('#view-coach').waitFor({state: 'visible'});
    await unlockChat(page);
    assert.match(await page.locator('#coach-chat-context').textContent(), /19 października/);
    assert.equal(page.observedRequests.some(url => url.endsWith('/coach/chat')), false);
    await page.locator('#coach-send').click();
    await page.locator('#coach-chat-status').filter({hasText: 'Odpowiedź zapisana'}).waitFor();
    const context = await page.evaluate(() => coachChat.turns[0].context);
    assert.deepEqual(context, {kind: 'week', week_start: '2026-10-19'});
});

test('chat retry preserves request identity and does not duplicate a response lost on the network', async t => {
    const page = await openDashboard(t);
    await unlockChat(page);
    let first = true;
    const ids = [];
    await page.route(`${productionAPI}/coach/chat`, async route => {
        ids.push(route.request().postDataJSON().request_id);
        const response = await route.fetch({url: `${origin}/coach/chat`});
        if (first) {
            first = false;
            await route.fulfill({status: 502, contentType: 'application/json', body: '{}'});
        } else await route.fulfill({response});
    });
    await page.locator('#coach-message').fill('Co dał trening?');
    await page.locator('#coach-send').click();
    await page.locator('#coach-retry').waitFor({state: 'visible'});
    await page.locator('#coach-retry').click();
    await page.locator('#coach-chat-status').filter({hasText: 'Odpowiedź zapisana'}).waitFor();
    assert.equal(ids.length, 2);
    assert.equal(ids[0], ids[1]);
    assert.equal(await page.locator('.coach-chat-message').count(), 2);
});

test('chat blocks duplicate sends while waiting and starts a separate conversation', async t => {
    const page = await openDashboard(t);
    await unlockChat(page);
    let release, reached;
    const blocked = new Promise(resolve => {release = resolve;});
    const intercepted = new Promise(resolve => {reached = resolve;});
    let posts = 0;
    await page.route(`${productionAPI}/coach/chat`, async route => {
        posts++; reached(); await blocked;
        const response = await route.fetch({url: `${origin}/coach/chat`});
        await route.fulfill({response});
    });
    await page.locator('#coach-message').fill('Jak trenować dalej?');
    await page.locator('#coach-send').click();
    await intercepted;
    try {
        assert.equal(await page.locator('#coach-send').isDisabled(), true);
        assert.equal(await page.locator('#coach-new-conversation').isDisabled(), true);
        await page.locator('#coach-message-form').evaluate(form => form.dispatchEvent(new Event('submit', {cancelable: true})));
        assert.equal(posts, 1);
    } finally {release();}
    await page.locator('#coach-chat-status').filter({hasText: 'Odpowiedź zapisana'}).waitFor();
    const previousId = await page.evaluate(() => coachChat.id);
    await page.locator('#coach-conversation-history > summary').click();
    await page.locator('#coach-new-conversation').click();
    assert.equal(await page.locator('.coach-chat-message').count(), 0);
    await page.locator('#coach-conversation-select').selectOption(previousId);
    await page.locator('.coach-chat-message[data-role=coach]').waitFor();
});

test('coach direct link and navigation fit a mobile viewport', async t => {
    const page = await openDashboard(t);
    await page.setViewportSize({width: 390, height: 844});
    await unlockChat(page);
    await page.reload();
    await page.locator('#coach-chat-body').waitFor({state: 'visible'});
    assert.equal(await page.locator('#view-today').isHidden(), true);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.locator('#coach-conversation-history > summary').click();
    assert.ok((await page.locator('#coach-conversation-select').boundingBox()).width >= 200);
    const bounds = await page.locator('.app-navigation').boundingBox();
    assert.ok(bounds.y + bounds.height <= 845);
});

test('workout discussion carries the selected logical session and date', async t => {
    const page = await openDashboard(t);
    const first = page.locator('.recent-workout').first();
    await first.getByRole('button', {name: 'Zapytaj trenera o ten trening'}).click();
    await page.locator('#view-coach').waitFor({state: 'visible'});
    await unlockChat(page);
    assert.match(await page.locator('#coach-chat-context').textContent(), /26 października/);
    await page.locator('#coach-send').click();
    await page.locator('#coach-chat-status').filter({hasText: 'Odpowiedź zapisana'}).waitFor();
    const context = await page.evaluate(() => coachChat.turns[0].context);
    assert.equal(context.kind, 'workout');
    assert.equal(context.date, '2026-10-26');
    assert.ok(context.session_id);
});

test('correction preview preserves notes, requires acceptance and survives reload', async t => {
    const page = await openDashboard(t);
    await unlockChat(page);
    await page.locator('#plan-corrections > summary').click();
    await page.locator('#corrections-load').click();
    await page.locator('#corrections-form').waitFor({state: 'visible'});
    await page.locator('#corrections-kind').selectOption('easy');
    await page.locator('#corrections-reason').fill('Zmęczenie po ostatnich treningach.');
    await page.locator('#corrections-form button[type=submit]').click();
    await page.locator('#corrections-preview').waitFor({state: 'visible'});
    assert.match(await page.locator('#corrections-before').textContent(), /Threshold/);
    assert.match(await page.locator('#corrections-after').textContent(), /Spokojny bieg/);
    assert.match(await page.locator('#corrections-after').textContent(), /Uwagi: zachowaj/);
    assert.match(await page.locator('#corrections-after').textContent(), /Uzasadnienie: Zmęczenie/);
    assert.equal(await page.locator('#corrections-preview img').count(), 0);
    await page.locator('#corrections-accept').click();
    await page.locator('#corrections-status').filter({hasText: 'zapisana i potwierdzona'}).waitFor();
    assert.equal(await page.locator('#corrections-accept').isDisabled(), true);
    await page.reload();
    await page.locator('#coach-chat-body').waitFor({state: 'visible'});
    await page.locator('#plan-corrections > summary').click();
    await page.locator('#corrections-load').click();
    await page.locator('#corrections-status').filter({hasText: 'Aktualny plan'}).waitFor();
    assert.match(await page.locator('#corrections-history').textContent(), /applied/);
    assert.match(await page.locator('#corrections-history').textContent(), /Threshold/);
    assert.equal(await page.locator('#corrections-title').inputValue(), 'Spokojny bieg');
    await page.setViewportSize({width: 390, height: 844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
});

async function prepareRacePlan(page) {
    await unlockChat(page);
    await page.locator('#race-generate button[type=submit]').click();
    await page.locator('#race-preview').waitFor({state: 'visible'});
}

test('one click proposes a ten-day plan from history without a preferences form', async t => {
    const page = await openDashboard(t);
    await prepareRacePlan(page);
    assert.equal(await page.locator('#race-preferences').count(), 0);
    assert.equal((await (await fetch(`${origin}/__test__/race-write-count`)).json()).count, 0);
    assert.match(await page.locator('#race-coaching').textContent(), /Historia i dawna kontuzja/);
    assert.match(await page.locator('#race-coaching').textContent(), /Droga do/);
    assert.match(await page.locator('#race-coaching').textContent(), /Baza i tolerancja/);
    assert.match(await page.locator('#race-coaching').textContent(), /Przygotowanie specyficzne/);
    assert.match(await page.locator('#race-weeks').textContent(), /2026-11-11/);
    assert.match(await page.locator('#race-entries').textContent(), /dzień 10\/10/);
    assert.match(await page.locator('#race-entries').textContent(), /Uwagi trenera: zachowaj/);
    assert.equal(await page.locator('#race-calendar img').count(), 0);
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.locator('#race-accept').click();
    await page.locator('#race-status').filter({hasText:'Plan zapisany i potwierdzony'}).waitFor();
    assert.equal(await page.locator('#race-accept').isDisabled(), true);
    assert.equal((await (await fetch(`${origin}/__test__/race-write-count`)).json()).count, 1);
    await page.reload();
    await page.locator('#coach-chat-body').waitFor({state:'visible'});
    await page.getByText('Kalendarz i starty po drodze', {exact:true}).click();
    await page.locator('#race-load').click();
    await page.getByText('Historia wersji planu', {exact:true}).click();
    await page.locator('#race-history button').first().click();
    await page.locator('#race-preview').waitFor({state:'visible'});
    assert.match(await page.locator('#race-summary').textContent(), /Stan: Zapisany/);
    assert.equal(await page.locator('#race-accept').isDisabled(), true);
});

test('calendar edit after preview blocks the whole plan write', async t => {
    const page = await openDashboard(t);
    await prepareRacePlan(page);
    await fetch(`${origin}/__test__/race-calendar-change`, {method: 'POST'});
    await page.locator('#race-accept').click();
    await page.locator('#race-status').filter({hasText: 'nieaktualne'}).waitFor();
    assert.equal((await (await fetch(`${origin}/__test__/race-write-count`)).json()).count, 0);
});

test('lost full plan save response retries the same immutable version without duplicate rows', async t => {
    const page = await openDashboard(t);
    await prepareRacePlan(page);
    let first = true;
    const ids = [];
    await page.route(`${productionAPI}/coach/race-plans/*/decision`, async route => {
        ids.push(new URL(route.request().url()).pathname);
        const response = await route.fetch({url: `${origin}${new URL(route.request().url()).pathname}`});
        if (first) {
            first = false;
            await route.fulfill({status: 502, contentType: 'application/json', body: '{}'});
        } else await route.fulfill({response});
    });
    await page.locator('#race-accept').click();
    await page.locator('#race-status').filter({hasText: 'Nie udało'}).waitFor();
    assert.match(await page.locator('#race-accept').textContent(), /Sprawdź wynik/);
    await page.locator('#race-accept').click();
    await page.locator('#race-status').filter({hasText: 'Plan zapisany i potwierdzony'}).waitFor();
    assert.equal(ids.length, 2);
    assert.equal(ids[0], ids[1]);
    assert.equal((await (await fetch(`${origin}/__test__/race-write-count`)).json()).count, 1);
});

test('new injury information produces a focused question and blocks plan acceptance', async t => {
    const page = await openDashboard(t);
    await unlockChat(page);
    await page.locator('#race-extra').evaluate(node => {node.open=true;});
    await page.locator('#race-note').fill('Aktualny ból Achillesa po biegu.');
    await page.locator('#race-generate button[type=submit]').click();
    await page.locator('#race-preview').waitFor({state:'visible'});
    assert.match(await page.locator('#race-blockers').textContent(), /ból występuje także podczas chodzenia/);
    assert.equal(await page.locator('#race-accept').isDisabled(), true);
    assert.equal(await page.locator('#race-entries details').count(), 0);
    assert.equal((await (await fetch(`${origin}/__test__/race-write-count`)).json()).count, 0);
});

test('zero changes explains protection and does not offer plan acceptance', async t => {
    await fetch(`${origin}/__test__/protect-race-plan`, {method:'POST'});
    const page = await openDashboard(t);
    await prepareRacePlan(page);
    assert.match(await page.locator('#race-outcome-title').textContent(), /Brak zmian do zapisania/);
    assert.match(await page.locator('#race-outcome').textContent(), /nie potwierdza/);
    assert.match(await page.locator('#race-summary').textContent(), /dodane 0, przebudowane 0, zachowane 49/);
    assert.equal(await page.locator('#race-accept').isHidden(), true);
    await page.locator('#race-entries details').first().locator('summary').click();
    assert.match(await page.locator('#race-entries details').first().textContent(), /korekta jest chroniona/);
    assert.equal((await (await fetch(`${origin}/__test__/race-write-count`)).json()).count, 0);
});

test('real proposed changes are open and visible before accepting', async t => {
    const page = await openDashboard(t);
    await prepareRacePlan(page);
    assert.match(await page.locator('#race-outcome-title').textContent(), /Propozycja planu gotowa/);
    assert.match(await page.locator('#race-outcome').textContent(), /Nic nie zostało jeszcze zapisane/);
    assert.equal(await page.locator('#race-entries details[open]').count(), 3);
    assert.equal(await page.locator('#race-entries details[open]').first().getByText('Po', {exact:true}).isVisible(), true);
    assert.equal(await page.locator('#race-accept').isVisible(), true);
});

test('failed new generation cannot leave an earlier acceptance button on screen', async t => {
    const page = await openDashboard(t);
    await prepareRacePlan(page);
    assert.equal(await page.locator('#race-accept').isVisible(), true);
    await page.route(`${productionAPI}/coach/race-plans/context`, route => route.fulfill({status:503, contentType:'application/json', body:JSON.stringify({detail:'Dane niedostępne.'})}));
    await page.locator('#race-generate button[type=submit]').click();
    await page.locator('#race-status').filter({hasText:'Dane niedostępne'}).waitFor();
    assert.equal(await page.locator('#race-preview').isHidden(), true);
    assert.equal(await page.locator('#race-accept').isHidden(), true);
});

test('primary goal and cycle require a review, persist and restore on reload', async t => {
    await fetch(`${origin}/__test__/legacy-goal`, {method:'POST'});
    const page = await openDashboard(t);
    await unlockChat(page);
    await page.getByText('Co PaceMind o mnie wie', {exact:true}).click();
    await page.locator('#profile-goal').filter({hasText:'2026-11-11'}).waitFor();
    await page.locator('#profile-calendar-load').click();
    await page.locator('#profile-goal-form').waitFor({state:'visible'});
    assert.equal(await page.locator('#profile-race option').count(),1);
    await page.locator('#profile-goal-form button').click();
    await page.locator('#profile-preview').waitFor({state:'visible'});
    assert.match(await page.locator('#profile-after').textContent(),/2026-12-13/);
    assert.match(await page.locator('#profile-goal').textContent(),/2026-11-11/);
    assert.equal(await page.locator('#profile-preview img').count(),0);
    await page.locator('#profile-accept').click();
    await page.locator('#profile-status').filter({hasText:'potwierdzone i zapisane'}).waitFor();
    assert.match(await page.locator('#profile-goal').textContent(),/2026-12-13/);
    await page.getByText('Ustal lub popraw początek cyklu', {exact:true}).click();
    await page.locator('#profile-anchor').fill('2026-11-01');
    await page.locator('#profile-cycle-form button').click();
    await page.locator('#profile-after').filter({hasText:'2026-11-01'}).waitFor();
    await page.locator('#profile-accept').click();
    await page.locator('#profile-status').filter({hasText:'potwierdzone i zapisane'}).waitFor();
    await page.reload();
    await page.locator('#coach-chat-body').waitFor({state:'visible'});
    await page.getByText('Co PaceMind o mnie wie', {exact:true}).click();
    await page.locator('#profile-goal').filter({hasText:'2026-12-13'}).waitFor();
    assert.match(await page.locator('#profile-cycle').textContent(),/Dziś dzień 1\/10/);
});

test('chat proposes memory but only athlete confirmation saves it; correction keeps original history', async t => {
    const page = await openDashboard(t);
    await unlockChat(page);
    await page.locator('#coach-message').fill('Boli mnie Achilles po akcentach.');
    await page.locator('#coach-send').click();
    await page.getByRole('button',{name:'Sprawdź i potwierdź',exact:true}).waitFor();
    await page.getByRole('button',{name:'Sprawdź i potwierdź',exact:true}).click();
    await page.locator('#profile-preview').waitFor({state:'visible'});
    assert.match(await page.locator('#profile-memory').textContent(),/Brak zapisanych ustaleń/);
    assert.match(await page.locator('#profile-source').textContent(),/Boli mnie Achilles/);
    await page.locator('#profile-accept').click();
    await page.locator('#profile-status').filter({hasText:'potwierdzone i zapisane'}).waitFor();
    assert.match(await page.locator('#profile-memory').textContent(),/Ból Achillesa/);
    await page.locator('#profile-memory').getByRole('button',{name:'Popraw lub oznacz ustąpienie'}).click();
    await page.locator('#profile-text').fill('Ból ustąpił, historyczna kontuzja.');
    await page.locator('#profile-fact-status').selectOption('resolved');
    await page.locator('#profile-memory-form button[type=submit]').click();
    await page.locator('#profile-after').filter({hasText:'Ból ustąpił'}).waitFor();
    await page.locator('#profile-accept').click();
    await page.locator('#profile-status').filter({hasText:'potwierdzone i zapisane'}).waitFor();
    assert.match(await page.locator('#profile-memory').textContent(),/Ustąpiło \/ nieaktualne/);
    assert.match(await page.locator('#profile-history').textContent(),/Ból Achillesa po akcentach/);
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),true);
    await page.locator('#coach-lock').click();
    assert.equal(await page.locator('#profile-memory').textContent(),'');
    assert.equal(await page.locator('#profile-history').textContent(),'');
});

test('answer to a planning question carries the previous question and reveals the generated plan', async t => {
    const page=await openDashboard(t);
    await unlockChat(page);
    await page.locator('#race-extra').evaluate(node => {node.open=true;});
    await page.locator('#race-note').fill('Potrzebne pytanie testowe');
    await page.locator('#race-generate button[type=submit]').click();
    await page.locator('#race-preview').waitFor({state:'visible'});
    assert.match(await page.locator('#race-summary').textContent(),/Wymaga odpowiedzi/);
    assert.match(await page.locator('#race-history').textContent(),/Wymaga odpowiedzi/);
    await fetch(`${origin}/__test__/allow-next-planning-attempt`,{method:'POST'});
    await page.locator('#race-extra').evaluate(node => {node.open=true;});
    await page.locator('#race-note').fill('Tak, od 1 grudnia. Ból ustąpił.');
    await page.locator('#race-start').fill('2026-12-01');
    await page.locator('#race-generate button[type=submit]').click();
    await page.locator('#race-outcome-title').filter({hasText:'Propozycja planu gotowa'}).waitFor();
    assert.equal((await (await fetch(`${origin}/__test__/clarification-answer-seen`)).json()).seen,true);
    assert.match(await page.locator('#race-summary').textContent(),/2026-12-01/);
    assert.ok(await page.locator('#race-entries details').count()>0);
    assert.equal(await page.locator('#race-accept').isVisible(),true);
    assert.equal(await page.locator('#race-outcome-title').evaluate(node=>document.activeElement===node),true);
});

test('review adapts the accepted campaign with visible evidence, preview and explicit save', async t=>{
    const seeded=await (await fetch(`${origin}/__test__/seed-accepted-review-plan`,{method:'POST'})).json();
    const page=await openDashboard(t);await unlockChat(page);
    await page.locator('#plan-review > summary').click();
    await page.locator('#review-run').click();
    await page.locator('#review-result').waitFor({state:'visible'});
    assert.match(await page.locator('#review-title').textContent(),/zmniejszenia/);
    assert.match(await page.locator('#review-evidence').textContent(),/too_hard: 2/);
    assert.equal((await (await fetch(`${origin}/__test__/race-write-count`)).json()).count,0);
    await page.locator('#review-propose button').click();
    await page.locator('#review-patch').waitFor({state:'visible'});
    assert.match(await page.locator('#review-changes').textContent(),/Przed/);
    assert.match(await page.locator('#review-changes').textContent(),/Uwagi: zachowaj/);
    await page.locator('#review-accept').click();
    await page.locator('#review-status').filter({hasText:'zapisana i potwierdzona'}).waitFor();
    assert.equal((await (await fetch(`${origin}/__test__/race-write-count`)).json()).count,1);
    const current=await (await page.request.get(`${origin}/coach/plan-reviews/current`,{headers:{Authorization:'Bearer fixture-private-chat-code'}})).json();
    assert.equal(current.campaign_id,seeded.id);
    assert.notEqual(current.head_id,seeded.id);
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
});

test('review with missing accepted plan explains the prerequisite',async t=>{
    const page=await openDashboard(t);await unlockChat(page);
    await page.locator('#plan-review > summary').click();
    await page.locator('#review-run').click();
    await page.locator('#review-status').filter({hasText:'Brak zaakceptowanego planu'}).waitFor();
    assert.equal(await page.locator('#review-result').isHidden(),true);
});

test('on-target execution supports keeping the plan without inventing a correction',async t=>{
    await fetch(`${origin}/__test__/seed-accepted-review-plan`,{method:'POST'});
    await fetch(`${origin}/__test__/review-mode/keep`,{method:'POST'});
    const page=await openDashboard(t);await unlockChat(page);
    await page.locator('#plan-review > summary').click();
    await page.locator('#review-run').click();
    await page.locator('#review-result').waitFor({state:'visible'});
    assert.match(await page.locator('#review-title').textContent(),/Utrzymaj/);
    assert.equal(await page.locator('#review-propose').isHidden(),true);
    assert.equal((await (await fetch(`${origin}/__test__/race-write-count`)).json()).count,0);
});

test('coach starts with chat and a simple planner while optional tools stay collapsed', async t=>{
    const page=await openDashboard(t); await unlockChat(page);
    await page.locator('#race-generate button[type=submit]').waitFor({state:'visible'});
    assert.deepEqual(await page.locator('#coach-chat-body > section').evaluateAll(nodes=>nodes.map(n=>n.id)),['coach-conversation','race-planning']);
    for (const id of ['athlete-knowledge','plan-review','plan-corrections']) assert.equal(await page.locator(`#${id}`).getAttribute('open'),null);
    assert.equal(await page.locator('#race-end, #race-replace').count(),0);
    assert.equal(await page.locator('#race-start').isVisible(),true);
    assert.equal(await page.locator('#race-goal').isVisible(),true);
    await page.getByRole('button',{name:'Czy mój czas jest realny?',exact:true}).click();
    assert.match(await page.locator('#coach-message').inputValue(),/całą dostępną historię/);
    assert.equal(page.observedRequests.some(url=>url.endsWith('/coach/chat')),false);
    await page.locator('#coach-send').click();
    await page.locator('#coach-chat-status').filter({hasText:'Odpowiedź zapisana'}).waitFor();
});

test('planner confirms selected Sheets goal explicitly, then generates from chosen preparation start',async t=>{
    await fetch(`${origin}/__test__/add-a-goal`,{method:'POST'});
    const page=await openDashboard(t); await unlockChat(page);
    await page.locator('#race-goal option').nth(1).waitFor({state:'attached'});
    await page.locator('#race-goal').selectOption({index:1});
    const readGoal=async()=> (await page.request.get(`${origin}/coach/profile`,{headers:{Authorization:'Bearer fixture-private-chat-code'}})).json();
    assert.equal((await readGoal()).goal.date,'2026-12-13');
    await page.locator('#race-goal-confirm').click();
    await page.locator('#race-status').filter({hasText:'Cel potwierdzony'}).waitFor();
    assert.equal((await readGoal()).goal.date,'2027-03-21');
    assert.equal((await (await fetch(`${origin}/__test__/race-write-count`)).json()).count,0);
    await page.locator('#race-start').fill('2026-12-01');
    await page.locator('#race-generate button[type=submit]').click();
    await page.locator('#race-outcome-title').filter({hasText:'Propozycja planu gotowa'}).waitFor();
    assert.match(await page.locator('#race-coaching').textContent(),/Półmaraton A/);
    assert.match(await page.locator('#race-summary').textContent(),/2026-12-01/);
    assert.equal((await (await fetch(`${origin}/__test__/race-write-count`)).json()).count,0);
});

test('later B race is previewed as a version of the same preparation and saves only on acceptance', async t=>{
    const page=await openDashboard(t); await prepareRacePlan(page);
    await page.locator('#race-accept').click();
    await page.locator('#race-status').filter({hasText:'Plan zapisany i potwierdzony'}).waitFor();
    const readCurrent=async()=> (await page.request.get(`${origin}/coach/plan-reviews/current`,{headers:{Authorization:'Bearer fixture-private-chat-code'}})).json();
    const original=await readCurrent();
    await fetch(`${origin}/__test__/add-b-race`,{method:'POST'});
    await fetch(`${origin}/__test__/allow-next-planning-attempt`,{method:'POST'});
    await page.getByText('Kalendarz i starty po drodze',{exact:true}).click();
    await page.locator('#race-load').click();
    await page.locator('#race-status').filter({hasText:'Kalendarz zmienił się'}).waitFor();
    await page.locator('#race-generate button[type=submit]').click();
    await page.locator('#race-outcome-title').filter({hasText:'Propozycja planu gotowa'}).waitFor();
    assert.match(await page.locator('#race-entries').textContent(),/Sprawdzian B/);
    assert.equal((await (await fetch(`${origin}/__test__/race-write-count`)).json()).count,1);
    await page.locator('#race-accept').click();
    await page.locator('#race-status').filter({hasText:'Plan zapisany i potwierdzony'}).waitFor();
    const updated=await readCurrent();
    assert.equal(updated.campaign_id,original.campaign_id);
    assert.notEqual(updated.head_id,original.head_id);
    assert.equal(updated.start,original.start);
});

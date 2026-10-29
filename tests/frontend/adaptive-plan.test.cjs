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
    t.after(() => context.close());
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

async function waitForWeekly(page) {
    await page.locator('#weekly-coach-review-card[aria-busy="true"]').waitFor({ state: 'hidden' });
    await page.locator('#weekly-review-content h3').waitFor({ state: 'visible' });
}

test('weekly review shows coaching, recovery, evidence and a full seven-day comparison', async t => {
    const page = await openDashboard(t);
    await waitForWeekly(page);
    const content = page.locator('#weekly-review-content');
    assert.match(await content.textContent(), /regeneracji pierwszeństwo/);
    assert.match(await content.textContent(), /Narastające|Silne sygnały zmęczenia/);
    assert.match(await content.textContent(), /Wnioski na kolejny tydzień/);
    assert.match(await page.locator('#weekly-review-period').textContent(), /19 października 2026.*25 października 2026/);
    await content.getByText('Plan i wykonanie dzień po dniu', { exact: true }).click();
    assert.equal(await content.locator('tbody tr').count(), 7);
    assert.match(await content.locator('tbody').textContent(), /Easy <img src=x onerror=alert\(1\)>/);
    assert.equal(await content.locator('img').count(), 0);
    await content.getByText('Na czym opiera się wniosek?', { exact: true }).first().click();
    assert.equal(await content.locator('.weekly-review-findings details[open]').count(), 1);
    assert.match(await content.locator('tbody').textContent(), /Za duży bodziec/);
});

test('weekly navigation handles current week, pending workouts and return to last full week', async t => {
    const page = await openDashboard(t);
    await waitForWeekly(page);
    await page.locator('#weekly-review-current').click();
    await waitForWeekly(page);
    assert.match(await page.locator('#weekly-review-state').textContent(), /Tydzień w toku/);
    assert.equal(await page.locator('#weekly-review-next').isDisabled(), true);
    const result = await (await fetch(`${origin}/review/week?week_start=2026-10-26`)).json();
    assert.equal(result.summary.pending_workouts_count, 1);
    assert.equal(result.summary.missed_workouts_count, 1);
    await page.locator('#weekly-review-content .weekly-review-days > summary').click();
    const friday = page.locator('#weekly-review-content tbody tr').filter({ hasText: '30 października' });
    assert.match(await friday.textContent(), /W planie/);
    await page.locator('#weekly-review-previous').click();
    await waitForWeekly(page);
    assert.match(await page.locator('#weekly-review-state').textContent(), /Zakończony tydzień/);
    await page.locator('#weekly-review-previous').click();
    await waitForWeekly(page);
    assert.match(await page.locator('#weekly-review-content').textContent(), /Brak zapisanych wykonań/);
    await page.locator('#weekly-review-latest').click();
    await waitForWeekly(page);
    assert.match(await page.locator('#weekly-review-period').textContent(), /19 października/);
});

test('empty weekly data has an explicit state instead of a reassuring verdict', async t => {
    await fetch(`${origin}/__test__/weekly-mode/empty`, { method: 'POST' });
    const page = await openDashboard(t);
    await waitForWeekly(page);
    assert.match(await page.locator('#weekly-review-content').textContent(), /Brak zapisanych wykonań/);
    assert.match(await page.locator('#weekly-review-content h3').textContent(), /więcej danych/);
    assert.match(await page.locator('#weekly-review-content').textContent(), /Za mało danych do oceny trendu/);
});

test('weekly failure leaves dashboard usable and retry recovers', async t => {
    await fetch(`${origin}/__test__/weekly-mode/failure`, { method: 'POST' });
    const page = await openDashboard(t);
    await page.locator('#weekly-review-retry').waitFor({ state: 'visible' });
    assert.equal(await page.locator('#dashboard').isVisible(), true);
    assert.equal(await page.locator('#adaptive-plan-accept').isEnabled(), true);
    assert.match(await page.locator('#weekly-review-state').textContent(), /Nie udało się/);
    await fetch(`${origin}/__test__/weekly-mode/normal`, { method: 'POST' });
    await page.locator('#weekly-review-retry').click();
    await waitForWeekly(page);
    assert.equal(await page.locator('#weekly-review-retry').isHidden(), true);
});

test('weekly review fits a mobile viewport', async t => {
    const page = await openDashboard(t);
    await page.setViewportSize({ width: 390, height: 844 });
    await waitForWeekly(page);
    await page.locator('#weekly-review-content .weekly-review-days > summary').click();
    const overflow = await page.evaluate(() => [...document.querySelectorAll('body *')]
        .filter(element => element.getBoundingClientRect().right > window.innerWidth + 1)
        .slice(0, 15).map(element => ({ tag: element.tagName, id: element.id, className: element.className, right: element.getBoundingClientRect().right })));
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, JSON.stringify(overflow));
});

test('late weekly response cannot overwrite a newer selection', async t => {
    const page = await openDashboard(t);
    await waitForWeekly(page);
    let release, reached;
    const blocked = new Promise(resolve => { release = resolve; });
    const intercepted = new Promise(resolve => { reached = resolve; });
    await page.route(`${productionAPI}/review/week?week_start=2026-10-12`, async route => {
        reached();
        await blocked;
        const response = await route.fetch({ url: `${origin}/review/week?week_start=2026-10-12` });
        await route.fulfill({ response });
    });
    await page.evaluate(() => {
        window.olderWeeklyRequest = loadWeeklyCoachReview('2026-10-12');
    });
    await intercepted;
    try {
        await page.evaluate(() => loadWeeklyCoachReview('2026-10-26'));
        await waitForWeekly(page);
    } finally {
        release();
    }
    await page.evaluate(() => window.olderWeeklyRequest);
    assert.match(await page.locator('#weekly-review-period').textContent(), /26 października/);
    assert.match(await page.locator('#weekly-review-state').textContent(), /Tydzień w toku/);
});

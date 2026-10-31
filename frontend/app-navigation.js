function currentAppView() {
    const hash = location.hash.slice(1);
    if (hash === 'weekly-coach-review-card') return 'week';
    return ['today', 'week', 'coach'].includes(hash) ? hash : 'today';
}

function showAppView() {
    const view = currentAppView();
    document.querySelectorAll('[data-app-view]').forEach(panel => {
        panel.hidden = panel.dataset.appView !== view;
    });
    document.querySelectorAll('.app-navigation [data-view]').forEach(link => {
        if (link.dataset.view === view) link.setAttribute('aria-current', 'page');
        else link.removeAttribute('aria-current');
    });
    document.getElementById('page-title').textContent = {today: 'Dzisiaj', week: 'Tydzień', coach: 'Trener'}[view];
    document.querySelector('.topbar-actions').hidden = view !== 'today';
    document.getElementById('today-date').hidden = view !== 'today';
}

document.addEventListener('DOMContentLoaded', () => {
    showAppView();
    initializeCoachChat();
    try {
        const shortcut = sessionStorage.getItem('weekly-shortcut');
        if (shortcut) document.getElementById('weekly-shortcut-summary').textContent = shortcut;
    } catch {}
    const ask = document.createElement('button');
    ask.type = 'button';
    ask.className = 'coach-request-button';
    ask.textContent = 'Zapytaj trenera o rekomendację';
    ask.addEventListener('click', () => startCoachDiscussion({kind: 'today'}, 'Dlaczego taka rekomendacja na dziś?'));
    document.getElementById('recommendation-card').appendChild(ask);
});
window.addEventListener('hashchange', () => {
    showAppView();
    loadDashboard();
    document.getElementById('page-title').focus({preventScroll: true});
    window.scrollTo({top: 0});
});

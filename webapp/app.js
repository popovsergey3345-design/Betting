// app.js

let tg = window.Telegram?.WebApp;
let userId = null;
let currentBalance = 0;
let currentBet = {};
let picks = { coinflip: null, dice: null, roulette: null };

// --- Запуск ---
document.addEventListener('DOMContentLoaded', async () => {
    if (tg) {
        tg.ready();
        tg.expand();
        if (tg.initDataUnsafe?.user) {
            userId = tg.initDataUnsafe.user.id;
        }
    }
    // Для тестов в браузере
    if (!userId) userId = 12345678;

    await loadUser();
    await loadEvents();
});

// --- API ---
async function api(url, method = 'GET', data = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (data) opts.body = JSON.stringify(data);
    const res = await fetch(url, opts);
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Ошибка');
    return json;
}

// --- Загрузка ---
async function loadUser() {
    const user = await api(`/api/user/${userId}`);
    currentBalance = user.balance;
    document.getElementById('balance').textContent = Math.floor(currentBalance);
}

async function loadEvents() {
    const data = await api('/api/events');
    const el = document.getElementById('events-list');
    if (!data.events.length) { el.innerHTML = '<div class="empty">Нет событий</div>'; return; }

    el.innerHTML = data.events.map(e => {
        const drawBtn = e.odds_draw > 0 ? `
            <button class="odds-btn" onclick="openModal('${e.id}','${e.title}','draw','Ничья',${e.odds_draw})">
                <span class="odds-label">X</span><span class="odds-value">${e.odds_draw.toFixed(2)}</span>
            </button>` : '';
        return `
        <div class="event-card">
            <div class="event-category">${e.category}</div>
            <div class="event-teams"><span>${e.team_a}</span><span class="vs">VS</span><span>${e.team_b}</span></div>
            <div class="odds-row">
                <button class="odds-btn" onclick="openModal('${e.id}','${e.title}','team_a','${e.team_a}',${e.odds_a})">
                    <span class="odds-label">1</span><span class="odds-value">${e.odds_a.toFixed(2)}</span>
                </button>
                ${drawBtn}
                <button class="odds-btn" onclick="openModal('${e.id}','${e.title}','team_b','${e.team_b}',${e.odds_b})">
                    <span class="odds-label">2</span><span class="odds-value">${e.odds_b.toFixed(2)}</span>
                </button>
            </div>
        </div>`;
    }).join('');
}

async function loadBets() {
    const data = await api(`/api/bets/${userId}`);
    const el = document.getElementById('bets-list');
    if (!data.bets.length) { el.innerHTML = '<div class="empty">Ставок пока нет 🎰</div>'; return; }

    const labels = { pending: '⏳', win: '✅', lose: '❌' };
    el.innerHTML = data.bets.map(b => `
        <div class="bet-card ${b.result}">
            <div class="bet-header">
                <span class="bet-name">${b.event_title}</span>
                <span class="bet-status">${labels[b.result] || '?'}</span>
            </div>
            <div class="bet-details">Ставка: ${b.amount}🪙 | Коэф: ${b.odds} | Выигрыш: ${b.potential_win}🪙</div>
        </div>`).join('');
}

// --- Табы ---
function switchTab(name, btn) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + name).classList.add('active');
    if (name === 'mybets') loadBets();
}

// --- Модалка ставки ---
function openModal(eventId, title, pick, pickLabel, odds) {
    currentBet = { eventId, title, pick, pickLabel, odds };
    document.getElementById('slip-event').textContent = title;
    document.getElementById('slip-pick').textContent = 'Исход: ' + pickLabel;
    document.getElementById('slip-odds').textContent = 'Коэффициент: ' + odds.toFixed(2);
    document.getElementById('bet-amount').value = '';
    document.getElementById('potential-win').textContent = '0';
    document.getElementById('bet-modal').classList.remove('hidden');
}

function closeModal() { document.getElementById('bet-modal').classList.add('hidden'); }

function calcWin() {
    const a = parseFloat(document.getElementById('bet-amount').value) || 0;
    document.getElementById('potential-win').textContent = (a * currentBet.odds).toFixed(2);
}

async function confirmBet() {
    const amount = parseFloat(document.getElementById('bet-amount').value);
    if (!amount || amount < 10) { toast('Минимум 10 монет', 'error'); return; }
    if (amount > currentBalance) { toast('Не хватает монет!', 'error'); return; }
    try {
        const res = await api('/api/bet', 'POST', {
            user_id: userId, event_id: currentBet.eventId,
            event_title: currentBet.title, pick: currentBet.pick,
            pick_label: currentBet.pickLabel, odds: currentBet.odds, amount
        });
        currentBalance = res.new_balance;
        document.getElementById('balance').textContent = Math.floor(currentBalance);
        closeModal();
        toast('Ставка принята! ✅', 'success');
    } catch (e) { toast(e.message, 'error'); }
}

// --- Быстрые игры ---
function selectPick(game, pick, btn) {
    picks[game] = pick;
    btn.closest('.quick-game').querySelectorAll('.pick-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
}

function setAmount(game, val) { document.getElementById(game + '-amount').value = val; }

async function playGame(game) {
    if (!picks[game]) { toast('Выбери исход!', 'error'); return; }
    const amount = parseFloat(document.getElementById(game + '-amount').value);
    if (!amount || amount < 10) { toast('Минимум 10 монет', 'error'); return; }
    if (amount > currentBalance) { toast('Не хватает монет!', 'error'); return; }

    try {
        const res = await api('/api/quick-bet', 'POST', {
            user_id: userId, game, pick: picks[game], amount
        });
        currentBalance = res.new_balance;
        document.getElementById('balance').textContent = Math.floor(currentBalance);

        const el = document.getElementById(game + '-result');
        el.className = 'game-result show ' + (res.win ? 'win' : 'lose');

        let text = '';
        if (game === 'coinflip') text = res.result === 'heads' ? '👑 Орёл' : '🔢 Решка';
        else if (game === 'dice') text = '🎲 Выпало: ' + res.result;
        else text = '🎡 Число: ' + res.result;

        el.textContent = res.win ? text + ' — Выигрыш! +' + res.winnings + '🪙' : text + ' — Мимо 😔';
        setTimeout(() => el.classList.remove('show'), 3500);
    } catch (e) { toast(e.message, 'error'); }
}

// --- Тост ---
function toast(msg, type) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = 'toast ' + type;
    setTimeout(() => el.classList.add('hidden'), 3000);
}
let tg=window.Telegram?.WebApp,userId=null,currentBalance=0,currentBet={},picks={coinflip:null,dice:null,roulette:null},allEvents=[];

document.addEventListener('DOMContentLoaded',async()=>{
    if(tg){tg.ready();tg.expand();if(tg.initDataUnsafe?.user)userId=tg.initDataUnsafe.user.id}
    if(!userId)userId=12345678;
    await loadUser();
    await loadEvents();
});

async function api(url,method='GET',data=null){
    const o={method,headers:{'Content-Type':'application/json'}};
    if(data)o.body=JSON.stringify(data);
    const r=await fetch(url,o);
    const j=await r.json();
    if(!r.ok)throw new Error(j.detail||'Ошибка');
    return j;
}

async function loadUser(){
    try{
        const u=await api(`/api/user/${userId}`);
        currentBalance=u.balance;
        upBal();
        const pn=document.getElementById('pname');if(pn)pn.textContent=u.username||'Игрок';
        const sb=document.getElementById('st-bal');if(sb)sb.textContent=Math.floor(u.balance);
        const sbe=document.getElementById('st-bets');if(sbe)sbe.textContent=u.total_bets;
        const sw=document.getElementById('st-wins');if(sw)sw.textContent=u.total_wins;
    }catch(e){console.error(e)}
}

async function loadEvents(){
    try{
        const d=await api('/api/events');
        allEvents=d.events;
        renderEvents(allEvents);
    }catch(e){
        document.getElementById('events-list').innerHTML='<div class="empty">❌ Ошибка загрузки</div>';
    }
}

function renderEvents(events){
    const el=document.getElementById('events-list');
    if(!events.length){el.innerHTML='<div class="empty">Нет предстоящих матчей</div>';return}

    // Группируем по лигам
    const groups={};
    events.forEach(e=>{
        const lg=e.league||e.category;
        if(!groups[lg])groups[lg]=[];
        groups[lg].push(e);
    });

    let html='';
    for(const[league,evts]of Object.entries(groups)){
        html+=`<div class="league-group"><div class="league-name">${league}</div>`;
        evts.forEach(e=>{
            const dt=new Date(e.commence_time);
            const now=new Date();
            const isLive=dt<=now;
            const timeStr=isLive?'<span class="live-dot">🔴 LIVE</span>':formatDate(dt);
            const drawBtn=e.odds_draw>0?`<button class="odds-btn" onclick="openModal('${e.id}',\`${esc(e.title)}\`,'draw','Ничья',${e.odds_draw})"><span class="ol">X</span><span class="ov">${e.odds_draw.toFixed(2)}</span></button>`:'';

            html+=`<div class="event-card" data-cat="${e.category}">
                <div class="event-time">${timeStr}</div>
                <div class="event-teams"><span>${e.team_a}</span><span class="vs">VS</span><span>${e.team_b}</span></div>
                <div class="odds-row">
                    <button class="odds-btn" onclick="openModal('${e.id}',\`${esc(e.title)}\`,'team_a','${esc(e.team_a)}',${e.odds_a})"><span class="ol">1</span><span class="ov">${e.odds_a.toFixed(2)}</span></button>
                    ${drawBtn}
                    <button class="odds-btn" onclick="openModal('${e.id}',\`${esc(e.title)}\`,'team_b','${esc(e.team_b)}',${e.odds_b})"><span class="ol">2</span><span class="ov">${e.odds_b.toFixed(2)}</span></button>
                </div>
            </div>`;
        });
        html+='</div>';
    }
    el.innerHTML=html;
}

function formatDate(d){
    const now=new Date();
    const today=new Date(now.getFullYear(),now.getMonth(),now.getDate());
    const tom=new Date(today);tom.setDate(tom.getDate()+1);
    const day=new Date(d.getFullYear(),d.getMonth(),d.getDate());
    let prefix='';
    if(day.getTime()===today.getTime())prefix='Сегодня';
    else if(day.getTime()===tom.getTime())prefix='Завтра';
    else prefix=d.toLocaleDateString('ru',{day:'numeric',month:'short'});
    return`📅 ${prefix} ${d.toLocaleTimeString('ru',{hour:'2-digit',minute:'2-digit'})}`;
}

function esc(s){return s.replace(/'/g,"\\'").replace(/`/g,"\\`")}

function filterSport(cat,btn){
    document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    if(cat==='all')renderEvents(allEvents);
    else renderEvents(allEvents.filter(e=>e.category===cat));
}

function switchTab(n,btn){
    document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-'+n).classList.add('active');
    if(n==='mybets')loadBets();
    if(n==='profile'){loadUser();loadLB()}
}

// --- Модалка ---
function openModal(eid,title,pick,label,odds){
    currentBet={eid,title,pick,label,odds};
    document.getElementById('s-event').textContent=title;
    document.getElementById('s-pick').textContent='Исход: '+label;
    document.getElementById('s-odds').textContent='Коэффициент: '+odds.toFixed(2);
    document.getElementById('bet-amount').value='';
    document.getElementById('pot-win').textContent='0';
    document.getElementById('bet-modal').classList.remove('hidden');
}
function closeModal(){document.getElementById('bet-modal').classList.add('hidden')}
function calcWin(){
    const a=parseFloat(document.getElementById('bet-amount').value)||0;
    document.getElementById('pot-win').textContent=(a*currentBet.odds).toFixed(2);
}
function sa(v){
    const inp=document.getElementById('bet-amount');
    inp.value=v==='max'?Math.floor(currentBalance):v;
    calcWin();
}

async function confirmBet(){
    const amt=parseFloat(document.getElementById('bet-amount').value);
    if(!amt||amt<10){toast('Минимум 10 монет','error');return}
    if(amt>currentBalance){toast('Не хватает монет!','error');return}
    try{
        const r=await api('/api/bet','POST',{
            user_id:userId,event_id:currentBet.eid,event_title:currentBet.title,
            pick:currentBet.pick,pick_label:currentBet.label,odds:currentBet.odds,amount:amt
        });
        currentBalance=r.new_balance;upBal();
        closeModal();
        toast('Ставка принята! ✅','success');
    }catch(e){toast(e.message,'error')}
}

// --- Ставки ---
async function loadBets(){
    try{
        const d=await api(`/api/bets/${userId}`);
        const el=document.getElementById('bets-list');
        if(!d.bets.length){el.innerHTML='<div class="empty">Ставок пока нет 🎰</div>';return}
        const lab={pending:'⏳ Ожидание',win:'✅ Выигрыш',lose:'❌ Проигрыш',cashout:'💰 Кэшаут'};
        el.innerHTML=d.bets.map(b=>{
            const coBtn=b.result==='pending'?`<button class="cashout-btn" onclick="doCashout(${b.id})">💰 Кэшаут</button>`:'';
            return`<div class="bet-card ${b.result}">
                <div class="bet-hdr"><span class="bet-ev">${b.event_title}</span><span class="bet-st ${b.result}">${lab[b.result]||b.result}</span></div>
                <div class="bet-pick">Исход: ${b.pick_label||b.pick}</div>
                <div class="bet-det">Ставка: ${b.amount}🪙 · Коэф: ${b.odds} · Выигрыш: ${b.potential_win}🪙</div>
                ${coBtn}
            </div>`}).join('');
    }catch(e){console.error(e)}
}

async function doCashout(betId){
    try{
        const r=await api('/api/cashout','POST',{user_id:userId,bet_id:betId});
        currentBalance=r.new_balance;upBal();
        toast(`Кэшаут: +${r.cashout.cashout_amount}🪙`,'success');
        loadBets();
    }catch(e){toast(e.message,'error')}
}

// --- Лидерборд ---
async function loadLB(){
    try{
        const d=await api('/api/leaderboard');
        document.getElementById('leaderboard').innerHTML=d.leaderboard.map((u,i)=>{
            const rc=i===0?'g':i===1?'s':i===2?'b':'';
            const re=i===0?'🥇':i===1?'🥈':i===2?'🥉':i+1;
            return`<div class="lb-row"><div class="lb-r ${rc}">${re}</div><div class="lb-n">${u.username||'Аноним'}</div><div class="lb-b">${Math.floor(u.balance)}🪙</div></div>`
        }).join('');
    }catch(e){}
}

// --- Быстрые игры ---
function selectPick(g,p,btn){picks[g]=p;btn.closest('.quick-game').querySelectorAll('.pick-btn').forEach(b=>b.classList.remove('selected'));btn.classList.add('selected')}
function setAmt(g,v){document.getElementById(g+'-amount').value=v}

async function playGame(g){
    if(!picks[g]){toast('Выбери исход!','error');return}
    const amt=parseFloat(document.getElementById(g+'-amount').value);
    if(!amt||amt<10){toast('Минимум 10','error');return}
    if(amt>currentBalance){toast('Не хватает!','error');return}
    try{
        const r=await api('/api/quick-bet','POST',{user_id:userId,game:g,pick:picks[g],amount:amt});
        currentBalance=r.new_balance;upBal();
        const el=document.getElementById(g+'-result');
        el.className='game-result show '+(r.win?'win':'lose');
        let t=g==='coinflip'?(r.result==='heads'?'👑 Орёл':'🔢 Решка'):g==='dice'?'🎲 '+r.result:'🎡 '+r.result;
        el.textContent=r.win?t+' +'+r.winnings+'🪙':t+' — Мимо 😔';
        setTimeout(()=>el.classList.remove('show'),3500);
    }catch(e){toast(e.message,'error')}
}

function upBal(){document.getElementById('balance').textContent=Math.floor(currentBalance);const s=document.getElementById('st-bal');if(s)s.textContent=Math.floor(currentBalance)}
function toast(m,t){const el=document.getElementById('toast');el.textContent=m;el.className='toast '+t;setTimeout(()=>el.classList.add('hidden'),3000)}

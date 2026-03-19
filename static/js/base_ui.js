
// ── CLOCK ────────────────────────────────────────────────────────────────────
function updateClock() {
  const el = document.getElementById('topClock');
  if (!el) return;
  const now = new Date();
  const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const d = days[now.getDay()]+' '+String(now.getDate()).padStart(2,'0')+' '+months[now.getMonth()];
  const t = String(now.getHours()).padStart(2,'0')+':'+String(now.getMinutes()).padStart(2,'0')+':'+String(now.getSeconds()).padStart(2,'0');
  el.textContent = d + ' — ' + t;
}
setInterval(updateClock, 1000); updateClock();

// ── THEME ─────────────────────────────────────────────────────────────────────
function toggleTheme() {
  document.body.classList.toggle('light');
  const isLight = document.body.classList.contains('light');
  localStorage.setItem('pmTheme', isLight ? 'light' : 'dark');
  document.getElementById('btnTheme').innerHTML =
    isLight ? '<i class="bi bi-sun-fill" style="color:#ffaa00"></i>'
            : '<i class="bi bi-moon-fill"></i>';
}
(function(){
  if (localStorage.getItem('pmTheme') === 'light') {
    document.body.classList.add('light');
    document.getElementById('btnTheme').innerHTML =
      '<i class="bi bi-sun-fill" style="color:#ffaa00"></i>';
  }
})();

// ── VOICE ─────────────────────────────────────────────────────────────────────
let voiceOn = localStorage.getItem('pmVoice') === 'on';
function toggleVoice() {
  voiceOn = !voiceOn;
  localStorage.setItem('pmVoice', voiceOn ? 'on' : 'off');
  document.getElementById('btnVoice').style.color = voiceOn ? 'var(--accent2)' : '';
  speakMessage(voiceOn ? 'Voice alerts enabled' : 'Voice alerts disabled');
}
function speakMessage(text) {
  if (voiceOn && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.9; u.pitch = 1;
    window.speechSynthesis.speak(u);
  }
}
if (voiceOn) document.getElementById('btnVoice').style.color = 'var(--accent2)';

// ── SIDEBAR MOBILE ────────────────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ── NOTIFICATION BADGE ────────────────────────────────────────────────────────
function updateNotifBadge() {
  fetch('/api/notifications/count')
    .then(r => r.json())
    .then(d => {
      const n = d.count || 0;
      ['topNotifBadge','sideNotifBadge'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent  = n;
        el.style.display = n > 0 ? 'block' : 'none';
      });
    }).catch(()=>{});
}
setInterval(updateNotifBadge, 10000); updateNotifBadge();

// ── WHATSAPP ALERT ────────────────────────────────────────────────────────────
async function sendWhatsAppAlert(machineId) {
  try {
    const r = await fetch(`/api/whatsapp-alert/${machineId}`,{method:'POST'});
    const d = await r.json();
    const modal = new bootstrap.Modal(document.getElementById('waModal') ||
      createWaModal(d.message));
    document.getElementById('waMessageText').textContent = d.message;
    modal.show();
    if (d.wa_url) setTimeout(()=>window.open(d.wa_url,'_blank'),1500);
  } catch(e) { alert('Alert simulation sent!'); }
}
function createWaModal(msg) {
  const div = document.createElement('div');
  div.innerHTML = `
    <div class="modal fade" id="waModal" tabindex="-1">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content" style="background:#0d1828;border:1px solid rgba(37,211,102,.3)">
          <div class="modal-header" style="border-color:rgba(37,211,102,.2)">
            <h6 class="modal-title" style="color:#25D366"><i class="bi bi-whatsapp me-2"></i>WhatsApp Alert Preview</h6>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div style="background:rgba(37,211,102,.05);border:1px solid rgba(37,211,102,.15);border-radius:10px;padding:1rem">
              <pre id="waMessageText" style="color:#d0dde8;font-size:.8rem;white-space:pre-wrap;font-family:'Exo 2',sans-serif;margin:0">${msg}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>`;
  document.body.appendChild(div);
  return document.getElementById('waModal');
}

// ── TELEGRAM MACHINE ALERT ────────────────────────────────────────────────────
async function sendTelegramMachineAlert(machineId) {
  const btn = event.target.closest('button');
  if (btn) { btn.disabled=true; btn.innerHTML='<i class="bi bi-hourglass-split"></i>'; }
  try {
    const r = await fetch(`/api/telegram-alert/${machineId}`,{method:'POST'});
    const d = await r.json();
    if (btn) {
      btn.innerHTML = d.success
        ? '<i class="bi bi-check-circle-fill" style="color:#00ff88"></i>'
        : '<i class="bi bi-x-circle-fill" style="color:#ff3355"></i>';
      setTimeout(()=>{
        btn.disabled=false;
        btn.innerHTML='<i class="bi bi-telegram"></i>';
      }, 2500);
    }
    if (!d.success) alert('Telegram not configured. Check config.py');
  } catch(e) {
    if (btn) { btn.disabled=false; btn.innerHTML='<i class="bi bi-telegram"></i>'; }
  }
}

// ── TELEGRAM TEST ─────────────────────────────────────────────────────────────
async function testTelegram() {
  const btn = event.target.closest('button');
  if (btn) btn.innerHTML = '<i class="bi bi-hourglass-split" style="color:#26A8E0"></i>';
  try {
    const r = await fetch('/api/telegram-test',{method:'POST'});
    const d = await r.json();
    if (btn) btn.innerHTML = d.success
      ? '<i class="bi bi-telegram" style="color:#00ff88"></i>'
      : '<i class="bi bi-telegram" style="color:#ff3355"></i>';
    alert(d.success
      ? '✅ Telegram working! Check your phone.'
      : '❌ Telegram failed: ' + d.message + '\nCheck BOT_TOKEN and CHAT_ID in config.py');
    setTimeout(()=>{ if(btn) btn.innerHTML='<i class="bi bi-telegram" style="color:#26A8E0"></i>'; }, 3000);
  } catch(e) {
    if (btn) btn.innerHTML = '<i class="bi bi-telegram" style="color:#26A8E0"></i>';
  }
}
import re

API = 'https://satta-matka-app-production.up.railway.app'

NEWJS = r'''
const API='__API__';
const store={get(k){try{return localStorage.getItem(k)}catch(e){return null}},set(k,v){try{localStorage.setItem(k,v)}catch(e){}},del(k){try{localStorage.removeItem(k)}catch(e){}}};
let TOKEN=store.get('kg_admin_token')||'';
let creds={};
const R='₹';
const inr=n=>R+Number(n||0).toLocaleString('en-IN');
const cap=s=>String(s||'').charAt(0).toUpperCase()+String(s||'').slice(1);
const v=id=>document.getElementById(id).value.trim();
let tT; function toast(m){const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');clearTimeout(tT);tT=setTimeout(()=>t.classList.remove('show'),2600);}
async function api(path,opts){
  opts=opts||{}; const headers={'Content-Type':'application/json'};
  if(TOKEN) headers.Authorization='Bearer '+TOKEN;
  const res=await fetch(API+path,{method:opts.method||'GET',headers,body:opts.body});
  let data={}; try{data=await res.json();}catch(e){}
  if(!res.ok) throw new Error(data.error||('Error '+res.status));
  return data;
}

/* ---- login ---- */
function toStep(s){ document.getElementById('step-pw').hidden=s!=='pw'; document.getElementById('step-otp').hidden=s!=='otp'; if(s==='otp')setTimeout(()=>{const f=document.querySelector('#otp input'); if(f)f.focus();},50); }
async function submitPw(){
  creds={username:v('a-user'),password:document.getElementById('a-pass').value};
  const err=document.getElementById('pw-err'); err.textContent='';
  if(!creds.username||!creds.password){ err.textContent='Enter username and password.'; return; }
  try{ const d=await api('/admin/login',{method:'POST',body:JSON.stringify(creds)});
    if(d.totpRequired){ toStep('otp'); return; } finishLogin(d);
  }catch(e){ err.textContent=e.message; }
}
async function submitOtp(){
  const code=[...document.querySelectorAll('#otp input')].map(i=>i.value).join('');
  const err=document.getElementById('otp-err'); err.textContent='';
  if(code.length!==6){ err.textContent='Enter the full 6-digit code.'; return; }
  try{ finishLogin(await api('/admin/login',{method:'POST',body:JSON.stringify(Object.assign({},creds,{token:code}))})); }
  catch(e){ err.textContent=e.message; }
}
function finishLogin(d){ TOKEN=d.token; store.set('kg_admin_token',TOKEN); enterApp(); }
function enterApp(){ document.getElementById('login').style.display='none'; document.getElementById('app').style.display='grid'; buildNav(); go('dashboard'); }
function logout(){ TOKEN=''; store.del('kg_admin_token'); location.reload(); }
document.querySelectorAll('#otp input').forEach((el,i,arr)=>{
  el.addEventListener('input',()=>{ el.value=el.value.replace(/\D/g,''); if(el.value&&arr[i+1])arr[i+1].focus(); });
  el.addEventListener('keydown',e=>{ if(e.key==='Backspace'&&!el.value&&arr[i-1])arr[i-1].focus(); if(e.key==='Enter')submitOtp(); });
});

/* ---- nav ---- */
const pages=[
  ['dashboard','Dashboard','Overview of your platform','M3 13h8V3H3zM13 21h8V11h-8zM13 3v6h8V3zM3 21h8v-6H3z'],
  ['users','Users','All registered players','M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8'],
  ['markets','Markets','Open, close and add markets','M3 3v18h18M7 14l4-4 3 3 5-6'],
  ['results','Results','Declare and view results','M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11'],
  ['deposits','Deposits','Verify and approve deposits','M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM3 10h18M7 15h4'],
  ['withdrawals','Withdrawals','Approve or reject payouts','M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6'],
  ['settings','Settings','Deposit / payment details','M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z'],
  ['security','Security','Google Authenticator (2FA)','M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'],
];
function buildNav(){
  document.getElementById('nav').innerHTML=pages.map(p=>{
    let badge=''; if(p[0]==='withdrawals')badge='<span class="badge" id="wd-badge">0</span>'; if(p[0]==='deposits')badge='<span class="badge" id="dp-badge">0</span>';
    return '<a id="nav-'+p[0]+'" onclick="go(\''+p[0]+'\')"><svg class="i" viewBox="0 0 24 24"><path d="'+p[3]+'"/></svg>'+p[1]+badge+'</a>';
  }).join('');
}
function setBadge(n){ const b=document.getElementById('wd-badge'); if(b)b.textContent=n; }
function setDepBadge(n){ const b=document.getElementById('dp-badge'); if(b)b.textContent=n; }
async function go(id){
  const p=pages.find(x=>x[0]===id);
  document.querySelectorAll('.nav a').forEach(a=>a.classList.remove('active'));
  const na=document.getElementById('nav-'+id); if(na)na.classList.add('active');
  document.getElementById('pg-title').textContent=p[1];
  document.getElementById('pg-sub').textContent=p[2];
  const view=document.getElementById('view');
  view.innerHTML='<div style="padding:48px 4px;color:var(--muted);font-size:14px">Loading…</div>';
  try{ await loaders[id](view); }catch(e){ view.innerHTML='<div class="panel" style="color:var(--red)">'+e.message+'</div>'; }
}

const loaders={
  async dashboard(view){
    const [u,m,w,r]=await Promise.all([api('/admin/users'),api('/markets'),api('/admin/withdrawals'),api('/results')]);
    const pend=(w.withdrawals||[]).filter(x=>x.status==='pending'); setBadge(pend.length);
    const openM=(m.markets||[]).filter(x=>x.status==='open').length;
    const tiles=[
      ['Total Users',(u.users||[]).length,'registered players','M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8',false],
      ['Open Markets',openM+' / '+(m.markets||[]).length,'currently running','M3 3v18h18M7 14l4-4 3 3 5-6',false],
      ['Pending Payouts',pend.length,pend.length?'awaiting review':'all clear','M12 8v4l3 3M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20',pend.length>0],
    ];
    view.innerHTML='<div class="tiles">'+tiles.map(t=>`<div class="tile"><div class="tl"><span class="ic"><svg class="i" viewBox="0 0 24 24"><path d="${t[3]}"/></svg></span>${t[0]}</div><div class="tv">${t[1]}</div><div class="td ${t[4]?'down':''}">${t[2]}</div></div>`).join('')+'</div>'+
    `<div class="grid2"><div class="panel"><h3>Pending withdrawals</h3><p class="sub">Approve or reject payouts</p>`+
    (pend.length? '<div class="table-wrap"><table><thead><tr><th>Player</th><th>Amount</th><th style="text-align:right">Action</th></tr></thead><tbody>'+
      pend.map(x=>`<tr><td class="u-name">${x.user?x.user.name:''}<div class="u-sub">+91 ${x.user?x.user.phone:''}</div></td><td class="amt">${inr(x.amount)}</td><td><div class="row-actions"><button class="btn sm ok" onclick="decide('${x.id}','approved')">Approve</button><button class="btn sm no" onclick="decide('${x.id}','rejected')">Reject</button></div></td></tr>`).join('')+
      '</tbody></table></div>' : '<p style="color:var(--muted);font-size:13px">No pending withdrawals.</p>')+
    `</div><div class="panel"><h3>Latest results</h3><p class="sub">Most recent declared</p>`+
    ((r.results||[]).length? (r.results||[]).slice(0,6).map(x=>`<div style="display:flex;justify-content:space-between;align-items:center;padding:11px 0;border-top:1px solid var(--line-soft)"><div><div style="font-weight:600;font-size:13.5px">${x.market}</div><div class="u-sub">${x.time||''}</div></div><div style="font-weight:700;letter-spacing:.05em;color:var(--violet)">${x.value}</div></div>`).join('') : '<p style="color:var(--muted);font-size:13px">No results declared yet.</p>')+
    `</div></div>`;
  },
  async users(view){
    const d=await api('/admin/users'); const us=d.users||[];
    view.innerHTML=`<div class="panel"><div class="head"><h3>Registered players</h3><span class="pill on">${us.length} total</span></div><p class="sub">Players reset their own password by OTP. Use Reset only if a player is locked out.</p><div class="table-wrap"><table><thead><tr><th>Player</th><th>Mobile</th><th>Wallet</th><th>Joined</th><th style="text-align:right">Action</th></tr></thead><tbody>`+
    (us.length? us.map(u=>`<tr><td class="u-name">${u.name}</td><td>+91 ${u.phone}</td><td class="amt">${inr(u.balance)}</td><td class="u-sub">${new Date(u.createdAt).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'})}</td><td style="text-align:right"><button class="btn sm ghost" onclick="resetPw('${u.id}','${(u.name||'').replace(/'/g,'')}')">Reset password</button></td></tr>`).join('') : '<tr><td colspan="5" style="color:var(--muted)">No users yet.</td></tr>')+
    `</tbody></table></div></div>`;
  },
  async markets(view){
    const d=await api('/markets'); const ms=d.markets||[];
    view.innerHTML=`<div class="panel"><h3>Add a market</h3><p class="sub">Create a new game market</p><div class="toolbar"><input class="in" id="m-name" placeholder="Market name (e.g. Sridevi Night)"><input class="in" id="m-open" placeholder="Open time (07:00 PM)"><input class="in" id="m-close" placeholder="Close time (08:00 PM)"><button class="btn" onclick="addMarket()">Add market</button></div></div>`+
    `<div class="panel"><div class="head"><h3>All markets</h3><span class="pill on">${ms.filter(m=>m.status==='open').length} open</span></div><div class="table-wrap"><table><thead><tr><th>Market</th><th>Open</th><th>Close</th><th>Status</th><th style="text-align:right">Toggle</th></tr></thead><tbody>`+
    ms.map(m=>`<tr><td class="u-name">${m.name}</td><td>${m.openTime}</td><td>${m.closeTime}</td><td><span class="pill ${m.status==='open'?'on':'off'}">${m.status==='open'?'Open':'Closed'}</span></td><td style="text-align:right"><button class="switch ${m.status==='open'?'on':''}" onclick="toggleMarket('${m.id}','${m.status}')"></button></td></tr>`).join('')+
    `</tbody></table></div></div>`;
  },
  async results(view){
    const [m,r]=await Promise.all([api('/markets'),api('/results')]);
    const ms=m.markets||[], rs=r.results||[];
    view.innerHTML=`<div class="panel"><h3>Declare a result</h3><p class="sub">Publish the winning number for a market</p><div class="toolbar"><select class="in" id="r-market">`+ms.map(x=>`<option value="${x.id}">${x.name}</option>`).join('')+`</select><input class="in" id="r-value" placeholder="Result (e.g. 128-14-590)"><button class="btn" onclick="declareResult()">Declare</button></div></div>`+
    `<div class="panel"><h3>Declared results</h3><p class="sub">Latest first</p><div class="table-wrap"><table><thead><tr><th>Market</th><th>Result</th><th>When</th></tr></thead><tbody>`+
    (rs.length? rs.map(x=>`<tr><td class="u-name">${x.market}</td><td style="font-weight:700;letter-spacing:.05em;color:var(--violet)">${x.value}</td><td class="u-sub">${x.time||new Date(x.declaredAt).toLocaleString('en-IN')}</td></tr>`).join('') : '<tr><td colspan="3" style="color:var(--muted)">No results yet.</td></tr>')+
    `</tbody></table></div></div>`;
  },
  async withdrawals(view){
    const d=await api('/admin/withdrawals'); const ws=d.withdrawals||[];
    const pc=ws.filter(w=>w.status==='pending').length; setBadge(pc);
    view.innerHTML=`<div class="panel"><div class="head"><h3>Withdrawal requests</h3><span class="pill pend">${pc} pending</span></div><p class="sub">Pay the player at the bank details shown, then approve.</p><div class="table-wrap"><table><thead><tr><th>Player</th><th>Mobile</th><th>Bank details</th><th>Amount</th><th>Status</th><th style="text-align:right">Action</th></tr></thead><tbody>`+
    (ws.length? ws.map(w=>`<tr><td class="u-name">${w.user?w.user.name:''}</td><td>+91 ${w.user?w.user.phone:''}</td><td class="u-sub" style="max-width:260px;white-space:normal">${w.bankInfo||'—'}</td><td class="amt">${inr(w.amount)}</td><td><span class="pill ${w.status==='approved'?'on':w.status==='rejected'?'off':'pend'}">${cap(w.status)}</span></td><td><div class="row-actions">${w.status==='pending'?`<button class="btn sm ok" onclick="decide('${w.id}','approved')">Approve</button><button class="btn sm no" onclick="decide('${w.id}','rejected')">Reject</button>`:'<span class="u-sub">Done</span>'}</div></td></tr>`).join('') : '<tr><td colspan="6" style="color:var(--muted)">No withdrawal requests.</td></tr>')+
    `</tbody></table></div></div>`;
  },
  async deposits(view){
    const d=await api('/admin/deposits'); const ds=d.deposits||[];
    const pc=ds.filter(x=>x.status==='pending').length; setDepBadge(pc);
    view.innerHTML=`<div class="panel"><div class="head"><h3>Deposit requests</h3><span class="pill pend">${pc} pending</span></div><p class="sub">Confirm the real payment (check the UTR / screenshot) before approving. Approving credits the player's wallet.</p><div class="table-wrap"><table><thead><tr><th>Player</th><th>Method</th><th>Reference / UTR</th><th>Proof</th><th>Amount</th><th>Status</th><th style="text-align:right">Action</th></tr></thead><tbody>`+
    (ds.length? ds.map(x=>`<tr><td class="u-name">${x.user?x.user.name:''}<div class="u-sub">+91 ${x.user?x.user.phone:''}</div></td><td>${x.method}</td><td class="u-sub">${x.reference}</td><td>${x.proof?`<img src="${x.proof}" style="width:38px;height:38px;object-fit:cover;border-radius:6px;cursor:pointer" onclick="lightbox(this.src)">`:'<span class="u-sub">—</span>'}</td><td class="amt">${inr(x.amount)}</td><td><span class="pill ${x.status==='approved'?'on':x.status==='rejected'?'off':'pend'}">${cap(x.status)}</span></td><td><div class="row-actions">${x.status==='pending'?`<button class="btn sm ok" onclick="approveDep('${x.id}',${x.amount})">Approve</button><button class="btn sm no" onclick="decideDep('${x.id}','reject')">Reject</button>`:'<span class="u-sub">Done</span>'}</div></td></tr>`).join('') : '<tr><td colspan="7" style="color:var(--muted)">No deposit requests.</td></tr>')+
    `</tbody></table></div></div>`;
  },
  async settings(view){
    const d=await api('/admin/settings'); const s=d.settings||{};
    view.innerHTML=`<div class="panel"><h3>Deposit / payment details</h3><p class="sub">Shown to players on the Add Fund screen so they know where to pay. Upload your UPI/bank QR and enter your UPI ID.</p>`+
    `<div class="step"><label class="lbl">UPI ID</label><input class="in" id="set-upi" value="${(s.upiId||'').replace(/"/g,'&quot;')}" placeholder="yourname@bank"></div>`+
    `<div class="step"><label class="lbl">Account name</label><input class="in" id="set-name" value="${(s.upiName||'').replace(/"/g,'&quot;')}" placeholder="Account holder name"></div>`+
    `<div class="step"><label class="lbl">Bank details (optional)</label><textarea class="in" id="set-bank" style="height:90px;padding:10px 14px;resize:vertical" placeholder="Bank name, A/C no, IFSC">${(s.bankDetails||'').replace(/</g,'&lt;')}</textarea></div>`+
    `<div class="step"><label class="lbl">Payment QR image</label>${s.qrImage?`<img id="set-qr-prev" src="${s.qrImage}" style="width:150px;height:150px;object-fit:contain;background:#fff;border-radius:10px;padding:6px;display:block;margin-bottom:8px">`:'<div id="set-qr-prev" class="u-sub" style="margin-bottom:8px">No QR uploaded</div>'}<input type="file" id="set-qr" accept="image/*" style="font-size:12.5px;color:var(--sub)"></div>`+
    `<h3 style="margin-top:26px">Social media links</h3><p class="sub">Paste the full link (https://…). Only the ones you fill in appear on the app's Contact with us screen.</p>`+
    `<div class="step"><label class="lbl">Instagram</label><input class="in" id="set-ig" value="${(s.igUrl||'').replace(/"/g,'&quot;')}" placeholder="https://instagram.com/yourpage"></div>`+
    `<div class="step"><label class="lbl">Facebook</label><input class="in" id="set-fb" value="${(s.fbUrl||'').replace(/"/g,'&quot;')}" placeholder="https://facebook.com/yourpage"></div>`+
    `<div class="step"><label class="lbl">YouTube</label><input class="in" id="set-yt" value="${(s.ytUrl||'').replace(/"/g,'&quot;')}" placeholder="https://youtube.com/@yourchannel"></div>`+
    `<div class="step"><label class="lbl">WhatsApp</label><input class="in" id="set-wa" value="${(s.waUrl||'').replace(/"/g,'&quot;')}" placeholder="https://wa.me/91XXXXXXXXXX"></div>`+
    `<div class="step"><label class="lbl">Telegram</label><input class="in" id="set-tg" value="${(s.tgUrl||'').replace(/"/g,'&quot;')}" placeholder="https://t.me/yourchannel"></div>`+
    `<div style="margin-top:12px"><button class="btn" onclick="saveSettings()">Save all settings</button></div></div>`;
    window._qrData = s.qrImage || null;
    const qi=document.getElementById('set-qr');
    if(qi) qi.addEventListener('change',()=>{ const f=qi.files[0]; if(!f)return; if(f.size>2*1024*1024){ toast('QR image must be under 2MB'); qi.value=''; return; } const r=new FileReader(); r.onload=()=>{ window._qrData=r.result; const p=document.getElementById('set-qr-prev'); if(p&&p.tagName==='IMG'){p.src=r.result;} }; r.readAsDataURL(f); });
  },
  async security(view){
    const me=await api('/admin/me'); const on=me.admin.totpEnabled;
    view.innerHTML=`<div class="panel"><div class="head"><h3>Google Authenticator</h3><span class="pill ${on?'on':'off'}">${on?'Enabled':'Not enabled'}</span></div><p class="sub">Every admin login requires a 6-digit code from the authenticator app — password alone is never enough.</p>`+
    (on? `<p style="color:var(--sub);font-size:13.5px">Two-step verification is active. You'll be asked for a code at every login.</p><div style="margin-top:16px"><button class="btn ghost" onclick="setupTotp()">Re-configure device</button></div>` : `<p style="color:var(--sub);font-size:13.5px">Turn this on to protect the admin panel.</p><div style="margin-top:16px"><button class="btn" onclick="setupTotp()">Set up Google Authenticator</button></div>`)+
    `<div id="twofa-setup" style="margin-top:22px"></div></div>`;
  },
};

/* ---- actions ---- */
async function toggleMarket(id,cur){ try{ await api('/admin/markets/'+id,{method:'PATCH',body:JSON.stringify({status:cur==='open'?'closed':'open'})}); go('markets'); toast('Market updated'); }catch(e){ toast(e.message); } }
async function addMarket(){ const name=v('m-name'),o=v('m-open')||'07:00 PM',c=v('m-close')||'08:00 PM'; if(!name){ toast('Enter a market name'); return; } try{ await api('/admin/markets',{method:'POST',body:JSON.stringify({name,openTime:o,closeTime:c})}); go('markets'); toast('Market "'+name+'" added'); }catch(e){ toast(e.message); } }
async function declareResult(){ const marketId=document.getElementById('r-market').value; const value=v('r-value'); if(!value){ toast('Enter a result value'); return; } try{ await api('/admin/results',{method:'POST',body:JSON.stringify({marketId,value})}); go('results'); toast('Result declared'); }catch(e){ toast(e.message); } }
async function decide(id,status){ try{ await api('/admin/withdrawals/'+id+'/'+(status==='approved'?'approve':'reject'),{method:'POST'}); go('withdrawals'); toast('Withdrawal '+status); }catch(e){ toast(e.message); } }
async function decideDep(id,action){ try{ await api('/admin/deposits/'+id+'/'+action,{method:'POST'}); go('deposits'); toast('Deposit '+(action==='approve'?'approved':'rejected')); }catch(e){ toast(e.message); } }
async function approveDep(id,amt){ const a=prompt('Amount to credit (adjust if needed):',amt); if(a===null)return; const n=Math.floor(Number(a)); if(!n||n<=0){ toast('Enter a valid amount'); return; } try{ const d=await api('/admin/deposits/'+id+'/approve',{method:'POST',body:JSON.stringify({amount:n})}); go('deposits'); toast('Deposit approved: '+inr(d.credited||n)); }catch(e){ toast(e.message); } }
async function resetPw(id,name){ const pw=prompt('Set a new password for '+name+':'); if(pw===null)return; if(pw.length<4){ toast('Password must be at least 4 characters'); return; } try{ await api('/admin/users/'+id+'/reset-password',{method:'POST',body:JSON.stringify({password:pw})}); toast('Password reset for '+name); go('users'); }catch(e){ toast(e.message); } }
async function saveSettings(){
  const upiId=v('set-upi'), upiName=v('set-name'), bankDetails=document.getElementById('set-bank').value.trim(), qrImage=window._qrData||null;
  const igUrl=v('set-ig'), fbUrl=v('set-fb'), ytUrl=v('set-yt'), waUrl=v('set-wa'), tgUrl=v('set-tg');
  try{ await api('/admin/settings',{method:'PUT',body:JSON.stringify({upiId,upiName,bankDetails,qrImage,igUrl,fbUrl,ytUrl,waUrl,tgUrl})}); toast('Settings saved'); }catch(e){ toast(e.message); }
}
function lightbox(src){
  let o=document.getElementById('lightbox');
  if(!o){ o=document.createElement('div'); o.id='lightbox'; o.style.cssText='position:fixed;inset:0;background:rgba(3,3,10,.85);display:grid;place-items:center;z-index:300;cursor:zoom-out;padding:30px'; o.onclick=()=>o.remove(); document.body.appendChild(o); }
  o.innerHTML='<img src="'+src+'" style="max-width:90%;max-height:90%;border-radius:12px">';
}
async function setupTotp(){
  try{ const d=await api('/admin/totp/setup',{method:'POST'});
    document.getElementById('twofa-setup').innerHTML=`<div class="twofa"><div><div id="qrbox"><img src="${d.qr}" alt="QR code"></div><div style="text-align:center;margin-top:12px"><div class="u-sub">Manual key</div><span class="secret">${d.secret}</span></div></div><div><ol class="steps"><li>Install <b>Google Authenticator</b> on your phone.</li><li>Tap <b>+</b> &rarr; <b>Scan a QR code</b> and scan this.</li><li>A 6-digit code for <b>Kalyan Games (admin)</b> appears.</li><li>Enter it below to turn on 2-step login.</li></ol><div class="step" style="max-width:240px"><label class="lbl">Enter the 6-digit code</label><input class="in" id="totp-code" inputmode="numeric" maxlength="6" placeholder="123456"></div><div style="margin-top:12px"><button class="btn" onclick="enableTotp()">Verify &amp; enable</button></div></div></div>`;
  }catch(e){ toast(e.message); }
}
async function enableTotp(){ const code=v('totp-code'); if(code.length!==6){ toast('Enter the 6-digit code'); return; } try{ await api('/admin/totp/enable',{method:'POST',body:JSON.stringify({token:code})}); toast('Google Authenticator enabled'); go('security'); }catch(e){ toast(e.message); } }

/* ---- boot ---- */
(async function(){ if(TOKEN){ try{ await api('/admin/me'); enterApp(); }catch(e){ TOKEN=''; store.del('kg_admin_token'); } } })();
'''.replace('__API__', API)

html = open('/home/user/claudecode/kalyan-games/web/admin.html').read()
# login: blank the prefilled password, make hints real
html = html.replace('<input class="in" id="a-pass" type="password" value="admin123" autocomplete="current-password">',
                    '<input class="in" id="a-pass" type="password" placeholder="Enter password" autocomplete="current-password">')
html = html.replace('<p class="hint">Demo login — <b>admin / admin123</b></p>',
                    '<p class="hint">Sign in with your admin username &amp; password.</p>')
html = html.replace('<p class="hint">Demo — enter any 6 digits to continue.</p>',
                    '<p class="hint">Open Google Authenticator and enter the current 6-digit code.</p>')
# replace the inline logic <script> (the last one) with the API-wired script
idx = html.rfind('<script>')
html = html[:idx] + '<script>\n' + NEWJS + '\n</script>\n'
# wrap as a full mobile-friendly document for Netlify
head = ('<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="theme-color" content="#05050c">\n'
        '</head>\n<body>\n')
open('admin.api.html', 'w').write(head + html + '\n</body>\n</html>\n')
print('written admin.api.html', round(len(head + html) / 1024), 'KB  API=', API)

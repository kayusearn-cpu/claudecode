import base64, json, re, io
from PIL import Image, ImageDraw, ImageFont

API = 'https://satta-matka-app-production.up.railway.app'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def make_icon(size):
    img = Image.new('RGB', (size, size), (0, 0, 0)); d = ImageDraw.Draw(img)
    for y in range(size):
        for xb in range(0, size, 8):
            t = (xb + y) / (2 * size)
            d.rectangle([xb, y, xb + 8, y + 1], fill=(int(0x7a+(0xc2-0x7a)*t), int(0x2b+(0x1f-0x2b)*t), int(0xff+(0xd6-0xff)*t)))
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size-1, size-1], radius=int(size*0.22), fill=255)
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0)); out.paste(img, (0, 0), mask)
    d2 = ImageDraw.Draw(out); f = ImageFont.truetype(FONT, int(size*0.42))
    tb = d2.textbbox((0, 0), 'KG', font=f)
    d2.text(((size-(tb[2]-tb[0]))/2-tb[0], (size-(tb[3]-tb[1]))/2-tb[1]), 'KG', font=f, fill=(255, 255, 255, 255))
    buf = io.BytesIO(); out.save(buf, 'PNG'); return base64.b64encode(buf.getvalue()).decode()

ic512, ic192, ic180 = make_icon(512), make_icon(192), make_icon(180)
manifest = {"name": "Kalyan Games", "short_name": "Kalyan", "start_url": ".", "display": "standalone",
            "orientation": "portrait", "background_color": "#030712", "theme_color": "#030712",
            "icons": [{"src": "data:image/png;base64," + ic192, "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
                      {"src": "data:image/png;base64," + ic512, "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]}
manifest_b64 = base64.b64encode(json.dumps(manifest).encode()).decode()

NEWJS = r'''
  const API='__API__';
  const store={get(k){try{return localStorage.getItem(k)}catch(e){return null}},set(k,v){try{localStorage.setItem(k,v)}catch(e){}},del(k){try{localStorage.removeItem(k)}catch(e){}}};
  let TOKEN=store.get('kg_token')||'';
  let balance=0, currentMarket='', currentMarketId=null, currentGame='Single Digit', marketsCache=[];
  const R='₹';
  const inr=n=>R+Number(n||0).toLocaleString('en-IN');
  const cap=s=>String(s||'').charAt(0).toUpperCase()+String(s||'').slice(1);
  async function api(path,opts){
    opts=opts||{};
    const headers={'Content-Type':'application/json'};
    if(TOKEN) headers.Authorization='Bearer '+TOKEN;
    const res=await fetch(API+path,{method:opts.method||'GET',headers,body:opts.body});
    let data={}; try{data=await res.json();}catch(e){}
    if(!res.ok) throw new Error(data.error||('Error '+res.status));
    return data;
  }
  const games=[
    {n:'Single Digit',k:'single_digit'},{n:'Jodi Digits',k:'jodi'},
    {n:'Single Panna',k:'single_panna'},{n:'Double Panna',k:'double_panna'},
    {n:'Triple Panna',k:'triple_panna'},{n:'SP Motor',k:'sp_motor'},
    {n:'DP Motor',k:'dp_motor'},{n:'SP DP TP',k:'sp_dp_tp'},
    {n:'Half Sangam',k:'double_panna'},{n:'Full Sangam',k:'triple_panna'},
  ];
  async function doLogin(){
    const phone=(document.getElementById('lg-phone').value||'').replace(/\D/g,'');
    const password=document.getElementById('lg-pass').value||'';
    if(!phone||!password){ toast('Enter mobile number and password'); return; }
    try{
      const d=await api('/auth/login',{method:'POST',body:JSON.stringify({phone,password})});
      TOKEN=d.token; store.set('kg_token',TOKEN);
      window.USER=d.user; setDrawerUser();
      balance=d.user.balance; syncBalance();
      await loadMarkets(); go('home');
    }catch(e){ toast(e.message||'Login failed'); }
  }
  function logout(){ TOKEN=''; store.del('kg_token'); balance=0; syncBalance(); go('login'); }
  async function doSignup(){
    const name=(document.getElementById('su-name').value||'').trim();
    const phone=(document.getElementById('su-phone').value||'').replace(/\D/g,'');
    const password=document.getElementById('su-pass').value||'';
    if(!name||!phone||!password){ toast('Please fill in all fields'); return; }
    if(phone.length<10){ toast('Enter a valid mobile number'); return; }
    try{
      const d=await api('/auth/register',{method:'POST',body:JSON.stringify({name,phone,password})});
      TOKEN=d.token; store.set('kg_token',TOKEN);
      window.USER=d.user; setDrawerUser();
      balance=d.user.balance; syncBalance();
      await loadMarkets(); go('home');
    }catch(e){ toast(e.message||'Sign up failed'); }
  }
  async function loadMarkets(){
    try{ const d=await api('/markets'); marketsCache=d.markets||[]; renderMarkets(); }catch(e){ toast(e.message); }
  }
  function renderMarkets(){
    const el=document.getElementById('market-list');
    if(!marketsCache.length){ el.innerHTML='<div style="padding:22px 20px;color:var(--muted);font-size:13px">No markets available.</div>'; return; }
    el.innerHTML=marketsCache.map(m=>{
      const open=m.status==='open'; const nm=(m.name||'').replace(/'/g,'');
      return '<div class="market" onclick="openMarket(\''+m.id+'\',\''+nm+'\')">'+
        '<div class="m-top"><div><div class="m-name">'+m.name+'</div><div class="m-code">XXX-XX-XXX</div></div>'+
        '<div class="m-right"><span class="pill '+(open?'run':'closed')+'">'+(open?'Market running':'Market Closed')+'</span>'+
        '<span class="chart-mini"><svg width="15" height="15"><use href="#i-chart"/></svg></span></div></div>'+
        '<div class="m-div"></div>'+
        '<div class="m-bottom"><div class="times"><span>Time Open: <b>'+m.openTime+'</b></span><span>Time Close: <b>'+m.closeTime+'</b></span></div>'+
        '<button class="btn-grad join" onclick="event.stopPropagation();openMarket(\''+m.id+'\',\''+nm+'\')">Join</button></div></div>';
    }).join('');
  }
  function renderGames(){
    document.getElementById('games-grid').innerHTML=games.map(g=>
      '<div class="game" onclick="openBet(\''+g.n+'\')"><div class="ico"><img src="'+ICONS[g.k]+'" alt="'+g.n+'"></div>'+
      '<div class="gname">'+g.n+'</div><button class="btn-grad start" onclick="event.stopPropagation();openBet(\''+g.n+'\')">Start</button></div>').join('');
  }
  function renderNums(){
    let h=''; for(let i=0;i<100;i++){ const n=String(i).padStart(2,'0');
      h+='<label class="num" id="num-'+i+'"><span class="nn">'+n+'</span><span class="cur">'+R+'</span>'+
         '<input type="number" min="0" placeholder="Enter amount" oninput="onAmt('+i+',this)"></label>'; }
    document.getElementById('num-grid').innerHTML=h; document.getElementById('bet-total').textContent='00';
  }
  async function loadWallet(){
    try{
      const d=await api('/wallet'); balance=d.balance; syncBalance();
      const rows=(d.transactions||[]).map(t=>{
        const pos=t.amount>0, io=pos?'in':'out'; const dt=new Date(t.createdAt);
        const ds=dt.toLocaleDateString('en-IN',{day:'2-digit',month:'short'})+', '+dt.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});
        return '<div class="tx"><span class="ti '+io+'"><svg width="18" height="18"><use href="#i-'+(pos?'up':'down')+'"/></svg></span>'+
          '<div class="tmid"><div class="tt">'+cap(t.type)+'</div><div class="ts">'+(t.note||'')+'</div></div>'+
          '<div><div class="tv '+(pos?'pos':'neg')+'">'+(pos?'+ ':'- ')+inr(Math.abs(t.amount))+'</div><div class="tdate">'+ds+'</div></div></div>';
      }).join('');
      document.getElementById('tx-list').innerHTML=rows||'<div style="padding:22px 20px;color:var(--muted);font-size:13px">No transactions yet.</div>';
    }catch(e){ toast(e.message); }
  }
  async function loadResults(){
    try{
      const d=await api('/results');
      const rows=(d.results||[]).map(r=>'<div class="market" style="cursor:default"><div class="m-bottom">'+
        '<div><div class="m-name">'+r.market+'</div><div class="m-code" style="margin-top:6px">'+(r.time||'')+'</div></div>'+
        '<div style="font-weight:800;font-size:19px;letter-spacing:.06em;color:var(--cream-ink)">'+r.value+'</div></div></div>').join('');
      document.getElementById('results-list').innerHTML=rows||'<div style="padding:22px 20px;color:var(--muted);font-size:13px">No results declared yet.</div>';
    }catch(e){ toast(e.message); }
  }
  const navItems=[['home','i-home'],['mybids','i-games'],['wallet','i-wallet'],['results','i-chart']];
  function buildNav(){
    document.querySelectorAll('.nav').forEach(nav=>{ const cur=nav.dataset.nav;
      nav.innerHTML=navItems.map(a=>'<button class="'+(cur===a[0]?'active':'')+'" onclick="navGo(\''+a[0]+'\')"><svg width="24" height="24"><use href="#'+a[1]+'"/></svg></button>').join('');
    });
  }
  function navGo(v){
    if(v==='mybids'){ openMyBids(); }
    else if(v==='wallet'){ go('wallet'); loadWallet(); }
    else if(v==='results'){ go('results'); loadResults(); }
    else go(v);
  }
  function go(id){
    document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    const sc=document.querySelector('#'+id+' .scroll'); if(sc) sc.scrollTop=0;
  }
  function openMarket(id,name){ currentMarketId=id; currentMarket=name; document.getElementById('games-title').textContent=name; renderGames(); go('games'); }
  function openBet(g){ currentGame=g; document.getElementById('bet-title').textContent=currentMarket+' - '+g; renderNums(); go('bet'); }
  function onAmt(i,el){
    document.getElementById('num-'+i).classList.toggle('filled',!!el.value&&+el.value>0);
    let t=0; document.querySelectorAll('#num-grid input').forEach(x=>t+=(+x.value||0));
    document.getElementById('bet-total').textContent=t.toLocaleString('en-IN');
  }
  async function submitBet(){
    const selections={}; let total=0;
    document.querySelectorAll('#num-grid input').forEach((x,i)=>{ const v=+x.value; if(v>0){ selections[String(i).padStart(2,'0')]=v; total+=v; } });
    if(total<=0){ toast('Enter an amount to submit'); return; }
    try{
      const d=await api('/bids',{method:'POST',body:JSON.stringify({marketId:currentMarketId,gameType:currentGame,selections})});
      balance=d.balance; syncBalance();
      const rc=document.getElementById('receipt');
      rc.style.display='block';
      rc.innerHTML=
        '<div class="r"><span>Market</span><b>'+currentMarket+'</b></div>'+
        '<div class="r"><span>Digits played</span><b>'+Object.keys(selections).length+'</b></div>'+
        '<div class="r"><span>Total bid</span><b>'+inr(total)+'</b></div>'+
        '<div class="r"><span>New balance</span><b>'+inr(balance)+'</b></div>';
      document.getElementById('success-title').textContent='Submission Successful';
      document.getElementById('success-msg').textContent='Your bid has been placed. Good luck for the draw!';
      document.getElementById('success').classList.add('show');
    }catch(e){ toast(e.message); }
  }
  function closeSuccess(){ document.getElementById('success').classList.remove('show'); go('home'); loadMarkets(); }
  function openSheet(kind){
    const s=document.getElementById('sheet');
    if(kind==='add'){
      s.innerHTML='<div class="grab"></div><h4>Add Fund</h4><p>Pay to the account/UPI below, then enter the amount and your UTR, and/or upload the payment screenshot. Your deposit will be added within 24 hours after the admin verifies your payment.</p>'+
        '<div id="pay-info" style="background:#0d0a1c;border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-bottom:16px;font-size:12.5px;color:var(--sub)">Loading payment details…</div>'+
        '<div class="field"><label>Amount</label><div class="input"><span class="pre">'+R+'</span><input type="number" id="sheet-amt" placeholder="Enter amount"></div></div>'+
        '<div class="field"><label>Payment method</label><div class="input" style="padding:0 6px 0 14px"><select id="sheet-method" style="flex:1;background:transparent;border:none;outline:none;color:var(--ink);font-family:inherit;font-size:14px;height:100%"><option>UPI</option><option>Bank Transfer</option></select></div></div>'+
        '<div class="field"><label>Transaction / UTR number</label><div class="input"><input id="sheet-ref" type="text" placeholder="e.g. 4051XXXXXXXX"></div></div>'+
        '<div class="field"><label>Payment screenshot (optional)</label><input type="file" id="sheet-proof" accept="image/*" style="width:100%;font-size:12.5px;color:var(--sub)"></div>'+
        '<button class="btn-grad big-btn" style="margin-top:6px" onclick="doDeposit()">Submit deposit request</button>';
      loadPayInfo();
    }else if(kind==='withdraw'){
      s.innerHTML='<div class="grab"></div><h4>Withdraw Funds</h4><p>Amount will be paid to your saved bank account after admin review.</p>'+
        '<div id="wd-bank" style="background:#0d0a1c;border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-bottom:16px;font-size:12.5px;color:var(--sub)">Loading your bank account…</div>'+
        '<div class="field"><label>Amount</label><div class="input"><span class="pre">'+R+'</span><input type="number" id="sheet-amt" placeholder="Enter amount"></div></div>'+
        '<button class="btn-grad big-btn" id="wd-btn" style="margin-top:8px" onclick="doWithdraw()">Send Request</button>';
      loadWithdrawBank();
    }else if(kind==='bank'){
      s.innerHTML='<div class="grab"></div><h4>Bank account</h4><p id="bank-note">Loading…</p>'+
        '<div class="field"><label>Account holder name</label><div class="input"><input id="bk-holder" type="text" placeholder="Full name"></div></div>'+
        '<div class="field"><label>Account number</label><div class="input"><input id="bk-acc" type="text" inputmode="numeric" placeholder="Bank account number"></div></div>'+
        '<div class="field"><label>IFSC code</label><div class="input"><input id="bk-ifsc" type="text" placeholder="e.g. HDFC0001234"></div></div>'+
        '<div class="field"><label>Bank name (optional)</label><div class="input"><input id="bk-name" type="text" placeholder="Bank name"></div></div>'+
        '<div class="field"><label>UPI ID (optional)</label><div class="input"><input id="bk-upi" type="text" placeholder="yourname@bank"></div></div>'+
        '<button class="btn-grad big-btn" id="bk-btn" style="margin-top:6px" onclick="doSaveBank()">Save bank details</button>'+
        '<div id="bk-extra" style="margin-top:10px"></div>';
      loadBank();
    }else if(kind==='logout'){
      s.innerHTML='<div class="grab"></div><h4>Confirm Logout</h4><p>Are you sure you want to log out of your account?</p>'+
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px">'+
        '<button class="sheet-btn cancel" onclick="closeSheet()">Cancel</button>'+
        '<button class="sheet-btn danger" onclick="closeSheet();logout()">Yes, Logout</button></div>';
    }else{
      s.innerHTML='<div class="grab"></div><h4>My Account</h4>'+
        '<button class="chipsel" style="width:100%;justify-content:center;color:var(--ink);margin-bottom:18px" onclick="openSheet(\'bank\')">Bank account (for withdrawal)</button>'+
        '<h4 style="font-size:16px">Change password</h4><p>Enter your current password and choose a new one.</p>'+
        '<div class="field"><label>Current password</label><div class="input"><input id="sheet-oldpass" type="password" placeholder="Current password"></div></div>'+
        '<div class="field"><label>New password</label><div class="input"><input id="sheet-newpass" type="password" placeholder="Create a new password"></div></div>'+
        '<button class="btn-grad big-btn" style="margin-top:6px" onclick="doChangePass()">Update password</button>'+
        '<button class="chipsel" style="width:100%;justify-content:center;margin-top:12px;color:var(--red);border-color:rgba(245,47,50,.4)" onclick="openSheet(\'logout\')">Log out</button>';
    }
    document.getElementById('overlay').classList.add('show');
    setTimeout(()=>{ const a=document.getElementById('sheet-amt')||document.getElementById('bk-holder')||document.getElementById('sheet-oldpass'); if(a)a.focus(); },200);
  }
  function closeSheet(){ document.getElementById('overlay').classList.remove('show'); }
  async function loadPayInfo(){
    try{
      const d=await api('/wallet/payment-info'); const box=document.getElementById('pay-info'); if(!box)return;
      if(!d.upiId && !d.bankDetails && !d.qrImage){ box.innerHTML='Ask the admin for payment details, then enter your UTR below.'; return; }
      let h='';
      if(d.qrImage) h+='<img src="'+d.qrImage+'" alt="Pay QR" style="width:150px;height:150px;object-fit:contain;background:#fff;border-radius:10px;padding:6px;display:block;margin:0 auto 10px">';
      window._upi=d.upiId||'';
      if(d.upiId) h+='<div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><span>UPI: <b style="color:var(--ink)">'+d.upiId+'</b>'+(d.upiName?' ('+d.upiName+')':'')+'</span><button class="chipsel" style="padding:5px 10px;color:var(--ink)" onclick="copyUpi()">Copy</button></div>';
      if(d.bankDetails) h+='<div style="margin-top:8px;white-space:pre-wrap;color:var(--ink)">'+d.bankDetails+'</div>';
      box.innerHTML=h;
    }catch(e){ const box=document.getElementById('pay-info'); if(box)box.textContent='Could not load payment details.'; }
  }
  function copyUpi(){ try{ navigator.clipboard.writeText(window._upi||''); toast('UPI copied'); }catch(e){ toast('Copy not supported'); } }
  function fileToDataUrl(file){ return new Promise((res,rej)=>{ if(!file){res(null);return;} const r=new FileReader(); r.onload=()=>res(r.result); r.onerror=()=>rej(new Error('Could not read file')); r.readAsDataURL(file); }); }
  async function doDeposit(){
    const a=+document.getElementById('sheet-amt').value;
    const method=document.getElementById('sheet-method').value;
    const reference=(document.getElementById('sheet-ref').value||'').trim();
    const file=document.getElementById('sheet-proof').files[0];
    if(a<=0){ toast('Enter a valid amount'); return; }
    if(file && file.size>2*1024*1024){ toast('Screenshot must be under 2MB'); return; }
    if(!reference && !file){ toast('Enter your UTR or upload the screenshot'); return; }
    try{ const proof=await fileToDataUrl(file);
      await api('/wallet/deposit',{method:'POST',body:JSON.stringify({amount:a,method,reference,proof})}); closeSheet(); toast('Deposit submitted — it will be added within 24 hours after verification.'); }catch(e){ toast(e.message); }
  }
  async function doChangePass(){
    const oldPassword=document.getElementById('sheet-oldpass').value||'';
    const newPassword=document.getElementById('sheet-newpass').value||'';
    if(!oldPassword||!newPassword){ toast('Enter your current and new password'); return; }
    if(newPassword.length<4){ toast('New password must be at least 4 characters'); return; }
    try{ const d=await api('/auth/change-password',{method:'POST',body:JSON.stringify({oldPassword,newPassword})}); closeSheet(); toast(d.message||'Password updated'); }catch(e){ toast(e.message); }
  }
  async function doWithdraw(){
    const a=+document.getElementById('sheet-amt').value;
    if(a<=0){ toast('Enter a valid amount'); return; }
    try{ await api('/wallet/withdraw',{method:'POST',body:JSON.stringify({amount:a})}); closeSheet(); showSuccess('Withdrawal Submitted','Your withdrawal request has been submitted and will be paid to your bank account within 24 hours.'); }catch(e){ toast(e.message); }
  }
  async function loadWithdrawBank(){
    const box=document.getElementById('wd-bank'); const btn=document.getElementById('wd-btn');
    try{ const b=await api('/wallet/bank');
      if(b.hasBank){ box.innerHTML='Pay to: <b style="color:var(--ink)">'+b.holder+'</b><br>A/C '+mask(b.account)+' &middot; '+b.ifsc+(b.bankName?' &middot; '+b.bankName:'')+'<div style="margin-top:6px"><span onclick="openSheet(\'bank\')" style="color:var(--violet);cursor:pointer">Change bank account</span></div>'; }
      else { box.innerHTML='No bank account saved. <span onclick="openSheet(\'bank\')" style="color:var(--violet);cursor:pointer">Add your bank account</span> to withdraw.'; if(btn){ btn.style.opacity='.5'; btn.style.pointerEvents='none'; } }
    }catch(e){ box.textContent='Could not load your bank account.'; }
  }
  function mask(a){ a=String(a||''); return a.length>4? a.slice(0,2)+'****'+a.slice(-4): a; }
  async function loadBank(){
    try{ const b=await api('/wallet/bank'); const note=document.getElementById('bank-note');
      document.getElementById('bk-holder').value=b.holder||''; document.getElementById('bk-acc').value=b.account||'';
      document.getElementById('bk-ifsc').value=b.ifsc||''; document.getElementById('bk-name').value=b.bankName||''; document.getElementById('bk-upi').value=b.upi||'';
      if(!b.canChange){
        note.innerHTML='Bank details can be changed only once every 30 days. Next change on <b style="color:var(--ink)">'+new Date(b.nextChangeAt).toLocaleDateString('en-IN')+'</b>.';
        ['bk-holder','bk-acc','bk-ifsc','bk-name','bk-upi'].forEach(id=>document.getElementById(id).disabled=true);
        const btn=document.getElementById('bk-btn'); btn.style.opacity='.5'; btn.style.pointerEvents='none';
      } else { note.textContent='Add the bank account where you want withdrawals paid. You can change this only once every 30 days.'; }
      const ex=document.getElementById('bk-extra');
      if(ex && b.hasBank && b.canChange){ ex.innerHTML='<button class="chipsel" style="width:100%;justify-content:center;color:var(--red)" onclick="doRemoveBank()">Remove bank account</button>'; }
    }catch(e){ const note=document.getElementById('bank-note'); if(note)note.textContent='Could not load bank details.'; }
  }
  async function doSaveBank(){
    const holder=document.getElementById('bk-holder').value.trim();
    const account=document.getElementById('bk-acc').value.replace(/\s/g,'');
    const ifsc=document.getElementById('bk-ifsc').value.trim();
    const bankName=document.getElementById('bk-name').value.trim();
    const upi=document.getElementById('bk-upi').value.trim();
    if(!holder||!account||!ifsc){ toast('Enter holder name, account number and IFSC'); return; }
    try{ const d=await api('/wallet/bank',{method:'POST',body:JSON.stringify({holder,account,ifsc,bankName,upi})}); closeSheet(); toast(d.message||'Bank details saved'); }catch(e){ toast(e.message); }
  }
  async function doRemoveBank(){
    if(!confirm('Remove your saved bank account?')) return;
    try{ const d=await api('/wallet/bank/remove',{method:'POST'}); closeSheet(); toast(d.message||'Bank account removed'); }catch(e){ toast(e.message); }
  }
  function openNotif(){ go('notif'); loadActivity(); }
  async function loadActivity(){
    const el=document.getElementById('notif-list'); if(!el)return;
    el.innerHTML='<div style="padding:24px 4px;color:var(--muted);font-size:13px">Loading…</div>';
    try{
      const d=await api('/wallet/activity'); const items=d.items||[];
      if(!items.length){ el.innerHTML='<div style="padding:40px 4px;color:var(--muted);font-size:13px;text-align:center">No notifications yet.</div>'; return; }
      const now=new Date();
      const dayKey=dt=>{ const x=new Date(dt); const diff=Math.floor((new Date(now.getFullYear(),now.getMonth(),now.getDate())-new Date(x.getFullYear(),x.getMonth(),x.getDate()))/86400000); if(diff===0)return 'Today'; if(diff===1)return 'Yesterday'; return x.toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}); };
      const ICON={deposit:['🏦','#c8f0d7'],withdraw:['💸','#c6f0d6'],win:['🎉','#a9bff1'],loss:['🎯','#ffcbd8'],security:['🔑','#ffeaa2'],bonus:['🎁','#ffeca7'],bid:['🎫','#a9bff1']};
      let html='',last='',first=true;
      for(const it of items){
        const k=dayKey(it.at); if(k!==last){ html+='<div class="nt-day">'+k+'</div>'; last=k; }
        const ic=ICON[it.kind]||['🔔','#d7d0ea'];
        const now2=(k==='Today'&&first);
        const tm=now2?'Just now':new Date(it.at).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});
        const body=it.body?(it.title+' '+it.body):it.title;
        html+='<div class="nt"><span class="nic" style="background:'+ic[1]+'">'+ic[0]+(first?'<span class="undot"></span>':'')+'</span>'+
          '<div class="ntx">'+body+'</div>'+
          '<span class="ntm'+(now2?' now':'')+'">'+tm+'</span></div>';
        first=false;
      }
      el.innerHTML=html;
    }catch(e){ el.innerHTML='<div style="padding:24px 4px;color:var(--red);font-size:13px">'+e.message+'</div>'; }
  }
  function showSuccess(title,msg){ document.getElementById('success-title').textContent=title; document.getElementById('success-msg').textContent=msg; const r=document.getElementById('receipt'); if(r)r.style.display='none'; document.getElementById('success').classList.add('show'); }
  function setDrawerUser(){
    const u=window.USER; if(!u)return;
    const init=(u.name||'P').trim().split(/\s+/).map(w=>w[0]||'').slice(0,2).join('').toUpperCase()||'P';
    const nm=document.getElementById('dr-name'), ph=document.getElementById('dr-phone'), av=document.getElementById('dr-av'), hav=document.querySelector('.home-top .avatar');
    if(nm)nm.textContent=u.name||'Player'; if(ph)ph.textContent='+91 '+(u.phone||''); if(av)av.textContent=init; if(hav)hav.textContent=init;
  }
  function openDrawer(){ document.getElementById('drawer-ov').classList.add('show'); }
  function closeDrawer(){ document.getElementById('drawer-ov').classList.remove('show'); }
  function shareApp(){ closeDrawer(); const url=location.href; if(navigator.share){ navigator.share({title:'Kalyan Games',text:'Play Kalyan Games',url}).catch(function(){}); } else { try{ navigator.clipboard.writeText(url); toast('App link copied'); }catch(e){ toast('Share: '+url); } } }
  function openMyBids(){ go('mybids'); loadMyBids(); }
  async function loadMyBids(){
    const el=document.getElementById('mybids-list'); el.innerHTML='<div style="padding:24px 4px;color:var(--muted);font-size:13px">Loading…</div>';
    try{ const d=await api('/bids/history'); const bs=d.bids||[];
      if(!bs.length){ el.innerHTML='<div style="padding:40px 4px;color:var(--muted);font-size:13px;text-align:center">No bids yet.</div>'; return; }
      el.innerHTML='<div style="height:8px"></div>'+bs.map(function(b){ const dt=new Date(b.createdAt);
        const nums=Object.keys(b.selections||{}).join(', ')||'-';
        const st=(b.session||'').toLowerCase()==='close'?'close':'open';
        return '<div class="bid-card"><div class="bh"><div class="bn">'+(b.market?b.market.name:'Market')+'</div>'+
          '<span class="bstatus '+st+'">'+(st==='close'?'Close':'Open')+'</span></div>'+
          '<div class="bd"><div><div class="bl">Game Type</div><div class="bv">'+b.gameType+'</div></div>'+
          '<div><div class="bl">Digits</div><div class="bv">'+nums+'</div></div>'+
          '<div><div class="bl">Points</div><div class="bv">'+inr(b.total)+'</div></div></div>'+
          '<div class="bf"><span class="bm">Best of luck</span><span class="bdt">'+dt.toLocaleDateString('en-IN',{day:'2-digit',month:'short'})+', '+dt.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})+'</span></div></div>'; }).join('');
    }catch(e){ el.innerHTML='<div style="padding:24px 4px;color:var(--red);font-size:13px">'+e.message+'</div>'; }
  }
  function openPassbook(){ go('passbook'); loadPassbook(); }
  async function loadPassbook(){
    const el=document.getElementById('passbook-list'); el.innerHTML='<div style="padding:24px 4px;color:var(--muted);font-size:13px">Loading…</div>';
    try{ const d=await api('/wallet/passbook'); const ts=d.transactions||[];
      if(!ts.length){ el.innerHTML='<div style="padding:40px 4px;color:var(--muted);font-size:13px;text-align:center">No transactions yet.</div>'; return; }
      const map={deposit:'Deposit',withdraw:'Withdrawal',bid:'Bid placed',win:'Winning',loss:'Bid lost'};
      const esc=function(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;'); };
      const rows=ts.map(function(t){ const dt=new Date(t.createdAt);
        const desc=t.note?esc(t.note):(map[t.type]||t.type);
        const sign=t.amount<0?'- ':'';
        return '<tr><td>'+dt.toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'})+'</td>'+
          '<td>'+desc+'</td><td class="amt">'+sign+inr(Math.abs(t.amount))+'</td></tr>'; }).join('');
      el.innerHTML='<div style="height:6px"></div><div class="pb-wrap"><table class="pb-table"><thead><tr><th style="width:95px">Date</th><th>Description</th><th class="amt" style="width:90px">Amount</th></tr></thead><tbody>'+rows+'</tbody></table></div>';
    }catch(e){ el.innerHTML='<div style="padding:24px 4px;color:var(--red);font-size:13px">'+e.message+'</div>'; }
  }
  function openChart(){ go('chart'); loadChart(); }
  async function loadChart(){
    const el=document.getElementById('chart-list'); el.innerHTML='<div style="padding:24px 20px;color:var(--muted);font-size:13px">Loading…</div>';
    try{ const d=await api('/markets'); const ms=d.markets||[];
      if(!ms.length){ el.innerHTML='<div style="padding:40px 20px;color:var(--muted);font-size:13px;text-align:center">No markets yet.</div>'; return; }
      el.innerHTML=ms.map(function(m){ const nm=(m.name||'').replace(/'/g,'');
        return '<div class="chart-row"><div><div class="cn">'+m.name+'</div>'+(m.latestResult?'<div class="cv">'+m.latestResult+'</div>':'<div class="cv" style="color:var(--muted)">No result yet</div>')+'</div><button class="btn-grad" style="padding:9px 22px;font-size:13px" onclick="openChartDetail(\''+m.id+'\',\''+nm+'\')">View</button></div>'; }).join('');
    }catch(e){ el.innerHTML='<div style="padding:24px 20px;color:var(--red);font-size:13px">'+e.message+'</div>'; }
  }
  function openChartDetail(id,name){ document.getElementById('chartd-title').textContent=name+' Chart'; go('chartd'); loadChartDetail(id); }
  async function loadChartDetail(id){
    const el=document.getElementById('chartd-list'); el.innerHTML='<div style="padding:24px 0;color:var(--muted);font-size:13px">Loading…</div>';
    try{ const d=await api('/markets/'+id+'/results'); const rs=d.results||[];
      if(!rs.length){ el.innerHTML='<div style="padding:40px 0;color:var(--muted);font-size:13px;text-align:center">No results declared yet.</div>'; return; }
      el.innerHTML='<table class="ctable"><thead><tr><th>Date</th><th style="text-align:right">Result</th></tr></thead><tbody>'+
        rs.map(function(r){ return '<tr><td>'+new Date(r.declaredAt).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'})+'</td><td class="v">'+r.value+'</td></tr>'; }).join('')+'</tbody></table>';
    }catch(e){ el.innerHTML='<div style="padding:24px 0;color:var(--red);font-size:13px">'+e.message+'</div>'; }
  }
  const LANGS=[['en','English'],['hi','हिन्दी'],['bn','বাংলা'],['mr','मराठी'],['te','తెలుగు'],['ta','தமிழ்'],['gu','ગુજરાતી'],['ur','اردو'],['kn','ಕನ್ನಡ']];
  let curLang=store.get('kg_lang')||'en';
  function openLang(){ go('lang'); loadLang(); }
  function loadLang(){ const el=document.getElementById('lang-list'); if(!el)return;
    el.innerHTML=LANGS.map(function(l){ return '<div class="lang-row'+(l[0]===curLang?' sel':'')+'" onclick="pickLang(\''+l[0]+'\')"><span class="radio"></span><span class="lname">'+l[1]+'</span></div>'; }).join(''); }
  function pickLang(c){ curLang=c; loadLang(); }
  function saveLang(){ store.set('kg_lang',curLang); toast('Language saved'); go('home'); }
  function openContact(){ go('contact'); loadContact(); }
  async function loadContact(){
    const el=document.getElementById('contact-list'); el.innerHTML='<div style="grid-column:1/-1;padding:24px 20px;color:var(--muted);font-size:13px">Loading…</div>';
    try{ const d=await api('/wallet/social');
      const items=[['instagram','Instagram','i-cam','#ff005d'],['facebook','Facebook','i-globe2','#287be8'],['youtube','YouTube','i-play','#ff0033'],['whatsapp','WhatsApp','i-chat','#00d66b'],['telegram','Telegram','i-send','#29a9ea']];
      let h='';
      for(const it of items){ const url=d[it[0]]; if(!url)continue;
        h+='<a class="social-card" href="'+url+'" target="_blank" rel="noopener" style="text-decoration:none"><span class="sc-ic" style="color:'+it[3]+'"><svg width="26" height="26"><use href="#'+it[2]+'"/></svg></span><b>'+it[1]+'</b><span>Tap to open</span></a>'; }
      el.innerHTML=h||'<div style="grid-column:1/-1;padding:40px 0;color:var(--muted);font-size:13px;text-align:center">No links added yet.</div>';
    }catch(e){ el.innerHTML='<div style="grid-column:1/-1;padding:24px 20px;color:var(--red);font-size:13px">'+e.message+'</div>'; }
  }
  function syncBalance(){
    const b=Number(balance||0).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});
    const hb=document.getElementById('home-bal'); if(hb)hb.textContent=b;
    const wb=document.getElementById('wallet-bal'); if(wb)wb.textContent=b;
    document.querySelectorAll('.wallet-chip').forEach(c=>c.innerHTML='<svg width="16" height="16"><use href="#i-wallet2"/></svg> '+R+Math.round(balance).toLocaleString('en-IN'));
  }
  let toastT;
  function toast(m){ const t=document.getElementById('toast'); t.textContent=m; t.classList.add('show'); clearTimeout(toastT); toastT=setTimeout(()=>t.classList.remove('show'),2600); }
  function togglePw(btn){ const inp=btn.parentNode.querySelector('input'); if(!inp)return; const show=inp.type==='password'; inp.type=show?'text':'password'; const u=btn.querySelector('use'); if(u)u.setAttribute('href',show?'#i-eye-off':'#i-eye'); }
  buildNav();
'''.replace('__API__', API)

tpl = open('template.html').read()
# inject icons
keys = ['single_digit', 'jodi', 'single_panna', 'double_panna', 'triple_panna', 'sp_motor', 'dp_motor', 'sp_dp_tp']
icons = {k: 'data:image/png;base64,' + base64.b64encode(open('icon_%s.png' % k, 'rb').read()).decode() for k in keys}
tpl = tpl.replace('__ICONS__', json.dumps(icons))
# replace the logic <script> (the last one) with the API-wired script,
# preserving any trailing content (e.g. late <style> blocks) after it
idx = tpl.rfind('<script>')
end = tpl.find('</script>', idx)
tail = tpl[end + len('</script>'):] if end != -1 else ''
tpl = tpl[:idx] + '<script>\n' + NEWJS + '\n</script>\n' + tail
# login: add ids + real handler
tpl = tpl.replace('<input type="tel" inputmode="numeric" placeholder="98765 43210" value="98765 43210">',
                  '<input id="lg-phone" type="tel" inputmode="numeric" placeholder="Enter mobile number">')
tpl = tpl.replace('<input type="password" placeholder="Enter password" value="demo1234">',
                  '<input id="lg-pass" type="password" placeholder="Enter password">')
tpl = tpl.replace('<button class="btn-grad big-btn" onclick="go(\'home\')">Log In</button>',
                  '<button class="btn-grad big-btn" onclick="doLogin()">Log In</button>')
# strip desktop pitch panel
tpl = re.sub(r'<section class="pitch">.*?</section>', '', tpl, flags=re.DOTALL)

overrides = """
  html,body{height:100%;margin:0}
  body{padding:0!important;gap:0!important;display:block!important;background:var(--bg)!important;min-height:100dvh}
  .pitch{display:none!important}
  .phone{width:100%!important;max-width:520px!important;height:100dvh!important;min-height:100dvh!important;margin:0 auto!important;padding:0!important;border-radius:0!important;box-shadow:none!important;background:var(--bg)!important;flex:none!important}
  .screen{border-radius:0!important}.notch{display:none!important}
  .statusbar{padding-top:calc(8px + env(safe-area-inset-top))!important}
  .nav{padding-bottom:env(safe-area-inset-bottom)!important;height:calc(84px + env(safe-area-inset-bottom))!important}
  #login .pad,.scroll{padding-bottom:calc(20px + env(safe-area-inset-bottom))}
"""
head = ('<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="theme-color" content="#030712">\n'
        '<meta name="mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
        '<meta name="apple-mobile-web-app-title" content="Kalyan Games">\n'
        '<link rel="apple-touch-icon" href="data:image/png;base64,' + ic180 + '">\n'
        '<link rel="manifest" href="data:application/manifest+json;base64,' + manifest_b64 + '">\n'
        '<style>' + overrides + '</style>\n</head>\n<body>\n')
open('index.api.html', 'w').write(head + tpl + '\n</body>\n</html>\n')
print('written index.api.html', round(len(head + tpl) / 1024), 'KB  API=', API)

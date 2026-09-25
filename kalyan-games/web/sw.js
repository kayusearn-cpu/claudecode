const CACHE="kalyan-v2";
const ASSETS=["/","/index.html","/manifest.json","/icon-192.png","/icon-512.png"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting()))});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",e=>{
  const req=e.request; if(req.method!=="GET")return;
  const url=new URL(req.url);
  if(url.origin!==self.location.origin)return; // never touch API (Railway) calls
  // Suppress Netlify's injected "Powered by Netlify" HUD/badge script
  if(url.pathname.startsWith("/.netlify/scripts/")){e.respondWith(new Response("",{headers:{"Content-Type":"application/javascript"}}));return;}
  if(req.mode==="navigate"){e.respondWith(fetch(req).catch(()=>caches.match("/index.html")));return;}
  e.respondWith(caches.match(req).then(r=>r||fetch(req).then(res=>{const cp=res.clone();caches.open(CACHE).then(c=>c.put(req,cp));return res}).catch(()=>r)));
});

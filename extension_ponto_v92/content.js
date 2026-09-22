(() => {
  if (location.port !== "7075") return;

  const SLOTS = [
    {id:"entrada",time:"07:50",label:"Entrada"},
    {id:"saida_almoco",time:"12:08",label:"Saída para almoço"},
    {id:"volta_almoco",time:"13:30",label:"Volta do almoço"},
    {id:"saida_final",time:"18:00",label:"Saída final"}
  ];

  let overlay = null;
  let checking = false;

  function pad(n){ return String(n).padStart(2,"0"); }
  function dayKey(d=new Date()){ return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate()); }
  function minsNow(d=new Date()){ return d.getHours()*60+d.getMinutes(); }
  function mins(t){ const p=t.split(":").map(Number); return p[0]*60+p[1]; }
  function isWorkday(d=new Date()){ const w=d.getDay(); return w>=1 && w<=5; }
  function key(){ return "aliyvoPontoGuard:"+dayKey(); }

  function getLocalState(){
    return new Promise(resolve => chrome.storage.local.get([key()], r => resolve(r[key()] || {resolved:{}})));
  }
  function setLocalState(state){
    return new Promise(resolve => chrome.storage.local.set({[key()]:state}, resolve));
  }

  async function fallbackPending(){
    if (!isWorkday()) return null;
    const state = await getLocalState();
    const current = minsNow();
    for (const slot of SLOTS){
      if (current >= mins(slot.time) && !state.resolved?.[slot.id]) return slot;
    }
    return null;
  }

  function askBackground(message){
    return new Promise(resolve => {
      try {
        chrome.runtime.sendMessage(message, response => {
          if (chrome.runtime.lastError) return resolve({available:false});
          resolve(response || {available:false});
        });
      } catch(_e){
        resolve({available:false});
      }
    });
  }

  async function syncLocalFromApi(data){
    if (!data || !Array.isArray(data.slots)) return;
    const state = await getLocalState();
    state.resolved = state.resolved || {};
    for (const row of data.slots){
      if (row && (row.status === "confirmed" || row.status === "missed")){
        state.resolved[row.id] = {status:row.status,at:row.resolved_at || new Date().toISOString()};
      }
    }
    await setLocalState(state);
  }

  async function currentPending(){
    const forced = await new Promise(resolve => chrome.storage.local.get(["aliyvoPontoForceTest"], r => resolve(r.aliyvoPontoForceTest || null)));
    if (forced && Number(forced.until || 0) > Date.now()){
      return {slot:{id:"__test__",time:"AGORA",label:"Teste do bloqueio"}, source:"test", bridge:false};
    }

    const bridge = await askBackground({type:"ponto-status"});
    if (bridge.available && bridge.data && bridge.data.ok){
      await syncLocalFromApi(bridge.data);
      return {slot:bridge.data.pending || null, source:"aliyvo", bridge:true};
    }
    return {slot:await fallbackPending(), source:"fallback", bridge:false};
  }

  function removeOverlay(){
    if (overlay){ overlay.remove(); overlay=null; }
    document.documentElement.classList.remove("aliyvo-ponto-locked");
  }

  function whenBody(fn){
    if (document.body) return fn();
    const mo = new MutationObserver(() => {
      if (document.body){ mo.disconnect(); fn(); }
    });
    mo.observe(document.documentElement,{childList:true,subtree:true});
  }

  async function resolveFallback(slot, status){
    const state = await getLocalState();
    state.resolved = state.resolved || {};
    state.resolved[slot.id] = {status,at:new Date().toISOString()};
    await setLocalState(state);
  }

  async function action(slot, kind, bridgeAvailable){
    const checkbox = overlay?.querySelector("#aliyvo-ponto-check");
    const msg = overlay?.querySelector("#aliyvo-ponto-msg");

    if (kind === "confirm" && !checkbox?.checked){
      if (msg) msg.textContent = "Marque a confirmação somente depois que o Ahgora confirmar a batida.";
      checkbox?.focus();
      return;
    }

    if (kind === "missed"){
      const ok = confirm("Você realmente perdeu essa batida no Ahgora?\n\nO Sankhya será liberado, mas o ALIYVO manterá o aviso de ajuste necessário.");
      if (!ok) return;
    }

    if (slot.id === "__test__"){
      await chrome.storage.local.remove("aliyvoPontoForceTest");
      removeOverlay();
      return;
    }

    const localStatus = kind === "confirm" ? "confirmed" : "missed";
    if (bridgeAvailable){
      const type = kind === "confirm" ? "ponto-confirm" : "ponto-missed";
      await askBackground({type,slot_id:slot.id});
    }
    // Mantém contingência sincronizada mesmo quando o ALIYVO está disponível.
    await resolveFallback(slot, localStatus);

    removeOverlay();
    setTimeout(checkNow, 400);
  }

  function render(slot, bridgeAvailable){
    whenBody(() => {
      if (overlay && overlay.dataset.slot === slot.id) return;
      removeOverlay();

      overlay=document.createElement("div");
      overlay.id="aliyvo-ponto-overlay";
      overlay.dataset.slot=slot.id;
      overlay.innerHTML =
        '<div class="aliyvo-ponto-card" role="dialog" aria-modal="true">' +
          '<div class="aliyvo-ponto-badge">PONTO PENDENTE</div>' +
          '<h1>'+slot.label+'</h1>' +
          '<div class="aliyvo-ponto-time">'+slot.time+'</div>' +
          '<p class="aliyvo-ponto-lead">Antes de continuar no Sankhya, registre sua batida no <strong>Ahgora Ponto Online</strong>.</p>' +
          '<div class="aliyvo-ponto-step"><b>1</b><span>Clique no ícone do Ahgora no canto superior direito do Chrome e faça a batida.</span></div>' +
          '<div class="aliyvo-ponto-step"><b>2</b><span>Espere o Ahgora confirmar. Depois marque a opção abaixo.</span></div>' +
          '<label class="aliyvo-ponto-check"><input id="aliyvo-ponto-check" type="checkbox"><span>O Ahgora confirmou que minha batida foi registrada.</span></label>' +
          '<button id="aliyvo-ponto-confirm" class="aliyvo-primary" type="button">✅ CONFIRMEI NO AHGORA — LIBERAR SANKHYA</button>' +
          '<button id="aliyvo-ponto-missed" class="aliyvo-secondary" type="button">⚠ PERDI ESSA BATIDA — PRECISO CORRIGIR</button>' +
          '<p id="aliyvo-ponto-msg" aria-live="polite"></p>' +
          '<div class="aliyvo-ponto-source">'+
            (bridgeAvailable ? 'Conectado ao Controle de Ponto do ALIYVO.' : 'ALIYVO não respondeu; usando proteção local de contingência.')+
          '</div>' +
        '</div>';

      document.body.appendChild(overlay);
      document.documentElement.classList.add("aliyvo-ponto-locked");
      overlay.querySelector("#aliyvo-ponto-confirm").addEventListener("click", () => action(slot,"confirm",bridgeAvailable));
      overlay.querySelector("#aliyvo-ponto-missed").addEventListener("click", () => action(slot,"missed",bridgeAvailable));
    });
  }

  async function checkNow(){
    if (checking) return;
    checking=true;
    try {
      const result=await currentPending();
      if (result.slot) render(result.slot,result.bridge);
      else removeOverlay();
    } finally {
      checking=false;
    }
  }

  checkNow();
  setInterval(checkNow,15000);
  addEventListener("focus",checkNow);
  addEventListener("pageshow",checkNow);
  document.addEventListener("visibilitychange",() => { if (!document.hidden) checkNow(); });
})();

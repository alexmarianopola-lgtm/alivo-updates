function ask(message){
  return new Promise(resolve => {
    chrome.runtime.sendMessage(message, response => {
      if (chrome.runtime.lastError) return resolve({available:false});
      resolve(response || {available:false});
    });
  });
}

async function refresh(){
  const result=await ask({type:"ponto-status"});
  const bridge=document.getElementById("bridge");
  const status=document.getElementById("status");
  if (result.available && result.data?.ok){
    bridge.textContent="● Conectado ao ALIYVO";
    bridge.className="ok";
    if (result.data.pending){
      status.innerHTML='<span class="bad">PENDENTE</span><br>'+result.data.pending.time+' • '+result.data.pending.label;
    } else if ((result.data.missed||[]).length){
      status.innerHTML='<span class="warn">AJUSTE NECESSÁRIO</span><br>Existe uma batida perdida registrada no ALIYVO.';
    } else if (result.data.next){
      status.innerHTML='<span class="ok">PONTO OK</span><br>Próxima: '+result.data.next.time+' • '+result.data.next.label;
    } else {
      status.innerHTML='<span class="ok">PONTO OK</span><br>Nenhuma batida pendente.';
    }
  } else {
    bridge.textContent="ALIYVO não respondeu — contingência local ativa";
    bridge.className="warn";
    status.textContent="A extensão continuará cobrando os horários no Sankhya mesmo com o ALIYVO fechado.";
  }
}

document.getElementById("test").addEventListener("click", async () => {
  await chrome.storage.local.set({aliyvoPontoForceTest:{until:Date.now()+5*60*1000}});
  document.getElementById("status").textContent="Teste ativado por 5 minutos. Volte para a aba do Sankhya.";
});
refresh();

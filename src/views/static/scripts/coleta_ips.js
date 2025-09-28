// coleta_ips.js - polling de status e logs, integra com window.COLETOR

const startBtn = document.getElementById('btn-start');
const stopBtn  = document.getElementById('btn-stop');
const resultsBtn = document.getElementById('btn-results');

const statusText = document.getElementById('status-text');
const scannedEl  = document.getElementById('scanned');
const totalEl    = document.getElementById('total');
const foundEl    = document.getElementById('found');
const logEl      = document.getElementById('log');

let pollInterval = null;
let lastLogText = "";

function safeFetch(url, opts){
  return fetch(url, opts).catch(e => {
    console.error('fetch fail', url, e);
    return new Response(null, { status: 500, statusText: 'fetch-failed' });
  });
}

async function startCollector(){
  const network = document.getElementById('network').value;
  const ports   = document.getElementById('ports').value;

  startBtn.disabled = true;
  statusText.textContent = 'iniciando...';

  const resp = await safeFetch(window.COLETOR.startUrl, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ network, ports })
  });

  if (!resp.ok){
    statusText.textContent = 'erro ao iniciar';
    startBtn.disabled = false;
    const txt = await resp.text().catch(()=>resp.statusText);
    alert('Erro ao iniciar: ' + (txt || resp.status));
    return;
  }

  stopBtn.disabled = false;
  statusText.textContent = 'rodando';
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(updateStatusAndLogs, 1000);
  updateStatusAndLogs();
}

async function stopCollector(){
  stopBtn.disabled = true;
  statusText.textContent = 'parada solicitada';
  await safeFetch(window.COLETOR.stopUrl, { method: "POST" });
  // mantém polling para acompanhar término
}

async function updateStatusAndLogs(){
  try {
    // busca status e logs em paralelo
    const [s, l] = await Promise.all([
      safeFetch(window.COLETOR.statusUrl),
      safeFetch(window.COLETOR.logsUrl)
    ]);

    if (s.ok){
      const j = await s.json().catch(()=>({}));
      statusText.textContent = j.running ? 'rodando' : 'parado';
      scannedEl.textContent = j.scanned ?? 0;
      totalEl.textContent = j.total ?? 0;
      // preferir result_count quando disponível
      foundEl.textContent = j.result_count ?? (j.found ?? 0);
      if (!j.running){
        startBtn.disabled = false;
        stopBtn.disabled = true;
      }
    }

    if (l.ok){
      const txt = await l.text();
      if (txt !== lastLogText){
        logEl.textContent = txt;
        logEl.scrollTop = logEl.scrollHeight;
        lastLogText = txt;
      }
    }
  } catch (e){
    console.error("update error", e);
  }
}

async function showResults(){
  const r = await safeFetch(window.COLETOR.resultsUrl);
  if (!r.ok){
    alert('Nenhum resultado disponível ainda.');
    return;
  }
  const json = await r.json().catch(()=>null);
  if (!json){
    const txt = await r.text().catch(()=>null);
    alert('Conteúdo: ' + (txt || 'vazio'));
    return;
  }

  const w = window.open("", "_blank");
  const rows = json.map(d => `<tr>
    <td>${d.ip || ''}</td>
    <td>${d.mac || ''}</td>
    <td>${(d.portas||[]).join(', ')}</td>
    <td>${d.subnet || ''}</td>
  </tr>`).join("");
  w.document.write(`
    <h2>Resultados da varredura (${json.length})</h2>
    <table border="1" cellpadding="6" cellspacing="0">
      <thead><tr><th>IP</th><th>MAC</th><th>Portas</th><th>Subnet</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `);
  w.document.close();
}

/* event listeners */
startBtn.addEventListener('click', startCollector);
stopBtn.addEventListener('click', stopCollector);
resultsBtn.addEventListener('click', showResults);

/* inicia polling leve ao carregar página para mostrar estado atual */
updateStatusAndLogs();
pollInterval = setInterval(updateStatusAndLogs, 3000);

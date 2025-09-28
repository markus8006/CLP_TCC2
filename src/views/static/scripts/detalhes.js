// static/scripts/detalhes.js
// Detalhes do CLP - script unificado e resiliente
(() => {
  // --- Helpers ---
  function getCsrfToken() {
    const m = document.querySelector('meta[name="csrf-token"]') || document.querySelector('meta[name="csrf_token"]');
    return m ? m.content : null;
  }

  function defaultFetchOpts(method = 'GET', body = null) {
    const headers = { 'Accept': 'application/json' };
    const token = getCsrfToken();
    if (token) {
      headers['X-CSRFToken'] = token;
      headers['X-CSRF-Token'] = token;
    }
    if (method !== 'GET' && method !== 'HEAD') {
      headers['Content-Type'] = 'application/json';
    }
    const opts = {
      method,
      credentials: 'same-origin',
      headers
    };
    if (body !== null) opts.body = JSON.stringify(body);
    return opts;
  }

  async function fetchJson(url, opts) {
    try {
      const resp = await fetch(url, opts);
      const text = await resp.text();
      // tenta parsear json, senão retorna texto
      let data = null;
      try { data = text ? JSON.parse(text) : null; } catch (e) { data = text; }
      return { ok: resp.ok, status: resp.status, data };
    } catch (err) {
      return { ok: false, status: 0, error: err };
    }
  }

  function showActionMsg(text, timeout = 4000) {
    const el = document.getElementById('mensagem');
    if (!el) return;
    el.textContent = text;
    if (timeout) setTimeout(() => { if (el) el.textContent = ''; }, timeout);
  }

  function showClpMsg(text, timeout = 4000) {
    const el = document.getElementById('mensagemCLP');
    if (!el) return;
    el.textContent = text;
    if (timeout) setTimeout(() => { if (el) el.textContent = ''; }, timeout);
  }

  // safe element getter
  const $ = id => document.getElementById(id);

  // --- Main ---
  document.addEventListener('DOMContentLoaded', () => {
    // IP can come from multiple places depending on template
    let ip = null;
    const ipEl = $('clpIp') || document.querySelector('[data-clp-ip]');
    if (ipEl) ip = (ipEl.textContent || ipEl.dataset.clpIp || '').trim();
    if (!ip && window.IP_CLP) ip = window.IP_CLP;
    if (!ip) {
      console.error('detalhes.js: IP do CLP não encontrado (precisa de #clpIp ou data-clp-ip ou window.IP_CLP).');
      return;
    }

    // Elements (support different templates/ids)
    const btnConnect = $('btnConnect');
    const btnDisconnect = $('btnDisconnect');
    const btnReadRegister = $('btnReadRegister') || $('btnRead');
    const readResult = $('readResult');
    const logContainer = $('logContainer');
    const tagListContainer = $('tag-list-container') || $('tagListContainer');
    const tagMessage = $('tagMessage') || $('tag-message');
    const inputAssignTag = $('inputAssignTag') || $('inputTag') || $('inputAssign') || $('inputTagNew');
    const globalTagsDatalist = $('globalTags') || $('global-tags');
    const btnAssignTag = $('btnAssignTag') || $('btnAddTag') || $('btnAddTagAssign');

    const viewMode = $('viewMode');
    const editMode = $('editMode');
    const editNameBtn = $('editNameBtn');
    const saveNameBtn = $('saveNameBtn');
    const cancelNameBtn = $('cancelNameBtn');
    const clpNameSpan = $('clpName');
    const inputClpName = $('inputClpName');

    const statusText = $('statusText');
    const connectContainer = $('connect-container');
    const disconnectContainer = $('disconnect-container');

    // Utility to update tag list DOM from array
    function renderTags(tags) {
      if (!tagListContainer) return;
      tagListContainer.innerHTML = '';
      if (!tags || tags.length === 0) {
        const li = document.createElement('li');
        li.id = 'no-tags-msg';
        li.textContent = 'Nenhuma tag associada.';
        tagListContainer.appendChild(li);
        return;
      }
      tags.forEach(t => {
        const li = document.createElement('li');
        li.className = 'tag-item';
        li.innerHTML = `<span class="tag-text">${t}</span> <span class="remove-tag" data-tag="${t}" title="Remover Tag">&times;</span>`;
        tagListContainer.appendChild(li);
      });
    }

    // fetch info endpoint (tries several fallback urls)
    async function fetchClpInfo() {
      // preferred: /clp/<ip>/info
      let res = await fetchJson(`/clp/${encodeURIComponent(ip)}/info`, defaultFetchOpts('GET'));
      if (res.ok && res.data && res.data.clp) return res.data.clp;
      // fallback: /clp/<ip>/values (contains status/logs/registers)
      res = await fetchJson(`/clp/${encodeURIComponent(ip)}/values`, defaultFetchOpts('GET'));
      if (res.ok && res.data) {
        // normalize to clp-like object
        const d = res.data;
        return {
          ip,
          status: d.status || 'Offline',
          registers_values: d.registers_values || {},
          logs: d.logs || [],
          tags: d.tags || [],
          portas: d.portas || []
        };
      }
      // final fallback: /clp/<ip>/status + local fields
      res = await fetchJson(`/clp/${encodeURIComponent(ip)}/status`, defaultFetchOpts('GET'));
      const status = (res.ok && res.data && res.data.status) ? res.data.status : 'Offline';
      return { ip, status, logs: [], registers_values: {}, tags: [], portas: [] };
    }

    // update UI with clp info
    async function atualizarInfo() {
      const clp = await fetchClpInfo();
      if (!clp) return;

      // status
      if (statusText) {
        statusText.textContent = 'Status: ' + (clp.status || 'Offline');
        statusText.className = (clp.status === 'Online') ? 'status_online' : 'status_offline';
      }
      if (connectContainer) connectContainer.style.display = clp.status === 'Online' ? 'none' : 'inline-block';
      if (disconnectContainer) disconnectContainer.style.display = clp.status === 'Online' ? 'inline-block' : 'none';

      // logs
      if (logContainer) {
        logContainer.innerHTML = '';
        const logs = clp.logs || [];
        // show newest at bottom
        logs.slice(-200).forEach(l => {
          const div = document.createElement('div');
          div.textContent = l;
          logContainer.appendChild(div);
        });
        logContainer.scrollTop = logContainer.scrollHeight;
      }

      // tags
      if (tagListContainer) renderTags(clp.tags || []);

      // optionally show last register read
      if (readResult && clp.registers_values) {
        const keys = Object.keys(clp.registers_values || {});
        if (keys.length) {
          const k = keys[keys.length - 1];
          const v = clp.registers_values[k];
          readResult.textContent = `${k}: ${JSON.stringify(v.value)} (ts: ${v.timestamp ? new Date(v.timestamp * 1000).toLocaleTimeString() : '-'})`;
        }
      }
    }

    // periodic update
    setInterval(atualizarInfo, 2000);
    atualizarInfo();

    // --- Connect / Start Polling (tries /poll/start then /connect) ---
    async function startPolling(port) {
      showClpMsg(`Iniciando conexão na porta ${port}...`);
      // try poll/start (preferred)
      let res = await fetchJson(`/clp/${encodeURIComponent(ip)}/poll/start`, defaultFetchOpts('POST', { port: Number(port) }));
      if (!res.ok || res.status === 404) {
        // fallback older endpoint
        res = await fetchJson(`/clp/${encodeURIComponent(ip)}/connect`, defaultFetchOpts('POST', { port: Number(port) }));
      }
      if (res.ok) {
        showClpMsg('Conexão iniciada', 2500);
        atualizarInfo();
      } else {
        const msg = res.data && res.data.message ? res.data.message : (res.error ? String(res.error) : `HTTP ${res.status}`);
        showClpMsg('Falha ao conectar: ' + msg, 5000);
      }
    }

    if (btnConnect) {
      btnConnect.addEventListener('click', async () => {
        const portSel = document.getElementById('portSelect');
        const port = portSel ? Number(portSel.value) : 502;
        await startPolling(port);
      });
    }

    // --- Disconnect / Stop polling (tries /poll/stop then /disconnect) ---
    async function stopPolling() {
      showClpMsg('Desconectando...');
      let res = await fetchJson(`/clp/${encodeURIComponent(ip)}/poll/stop`, defaultFetchOpts('POST'));
      if (!res.ok || res.status === 404) {
        res = await fetchJson(`/clp/${encodeURIComponent(ip)}/disconnect`, defaultFetchOpts('POST'));
      }
      if (res.ok) {
        showClpMsg('Desconectado', 2500);
        atualizarInfo();
      } else {
        showClpMsg('Falha ao desconectar', 4000);
      }
    }

    if (btnDisconnect) {
      btnDisconnect.addEventListener('click', async () => {
        await stopPolling();
      });
    }

    // --- Read register (tries /read_register then /read) ---
    if (btnReadRegister) {
      btnReadRegister.addEventListener('click', async () => {
        const addrEl = document.getElementById('inputAddress') || document.getElementById('addressInput');
        const resultDiv = readResult || $('read_result') || null;
        if (!addrEl) { showActionMsg('Elemento de endereço não encontrado'); return; }
        const address = Number(addrEl.value);
        if (Number.isNaN(address)) { if (resultDiv) resultDiv.innerHTML = '<span style="color:red">Endereço inválido</span>'; return; }
        showActionMsg(`Lendo registrador ${address}...`);
        let res = await fetchJson(`/clp/${encodeURIComponent(ip)}/read_register`, defaultFetchOpts('POST', { address: address, count: 1 }));
        if (!res.ok || res.status === 404) {
          res = await fetchJson(`/clp/${encodeURIComponent(ip)}/read`, defaultFetchOpts('POST', { address: address, count: 1 }));
        }
        if (res.ok && res.data && res.data.success !== false) {
          const value = (res.data && res.data.value !== undefined) ? res.data.value : res.data;
          if (resultDiv) resultDiv.innerHTML = `Endereço <strong>${address}</strong> = <strong>${JSON.stringify(value)}</strong>`;
          showActionMsg('Leitura concluída', 3000);
        } else {
          const msg = res.data && res.data.message ? res.data.message : res.error ? String(res.error) : `HTTP ${res.status}`;
          if (resultDiv) resultDiv.innerHTML = `<span style="color:red">Erro: ${msg}</span>`;
          showActionMsg('Falha na leitura', 3500);
        }
      });
    }

    // --- Tags: load global tags (GET /clp/tags) ---
    async function carregarTagsGlobais() {
      if (!globalTagsDatalist) return;
      const res = await fetchJson('/clp/tags', defaultFetchOpts('GET'));
      if (res.ok && res.data && Array.isArray(res.data.tags)) {
        globalTagsDatalist.innerHTML = '';
        res.data.tags.forEach(t => {
          const opt = document.createElement('option');
          opt.value = t;
          globalTagsDatalist.appendChild(opt);
        });
      }
    }
    carregarTagsGlobais();

    // --- Assign tag ---
    async function assignTag(tagValue) {
      if (!tagValue) return;
      // ensure global exists
      await fetchJson('/clp/tags', defaultFetchOpts('POST', { tag: tagValue }));
      // associate to clp
      let res = await fetchJson(`/clp/${encodeURIComponent(ip)}/tags/assign`, defaultFetchOpts('POST', { tag: tagValue }));
      if (!res.ok || res.status === 404) {
        // fallback older endpoint: POST /clp/<ip>/tags
        res = await fetchJson(`/clp/${encodeURIComponent(ip)}/tags`, defaultFetchOpts('POST', { tag: tagValue }));
      }
      if (res.ok) {
        showActionMsg('Tag associada', 2500);
        // optimistic UI update
        const noTags = $('no-tags-msg');
        if (noTags) noTags.remove();
        if (tagListContainer) {
          // avoid duplicates
          const exists = Array.from(tagListContainer.querySelectorAll('.tag-text')).some(el => el.textContent === tagValue);
          if (!exists) {
            const li = document.createElement('li');
            li.className = 'tag-item';
            li.innerHTML = `<span class="tag-text">${tagValue}</span> <span class="remove-tag" data-tag="${tagValue}" title="Remover Tag">&times;</span>`;
            tagListContainer.appendChild(li);
          }
        }
        carregarTagsGlobais();
      } else {
        const msg = res.data && res.data.message ? res.data.message : res.error ? String(res.error) : `HTTP ${res.status}`;
        if (tagMessage) tagMessage.textContent = msg;
      }
    }

    if (btnAssignTag && inputAssignTag) {
      btnAssignTag.addEventListener('click', async (ev) => {
        ev.preventDefault();
        const tagValue = (inputAssignTag.value || '').trim();
        if (!tagValue) { if (tagMessage) tagMessage.textContent = 'Digite ou escolha uma tag.'; return; }
        await assignTag(tagValue);
        if (inputAssignTag) inputAssignTag.value = '';
      });
    }

    // Remove tag (delegation)
    if (tagListContainer) {
      tagListContainer.addEventListener('click', async (ev) => {
        const target = ev.target;
        if (!target || !target.classList.contains('remove-tag')) return;
        const tag = target.dataset.tag;
        if (!tag) return;
        if (!confirm(`Remover tag "${tag}"?`)) return;
        // try DELETE /clp/<ip>/tags/<tag>
        let res = await fetchJson(`/clp/${encodeURIComponent(ip)}/tags/${encodeURIComponent(tag)}`, defaultFetchOpts('DELETE'));
        if (!res.ok || res.status === 404) {
          // fallback: POST /clp/<ip>/tags/remove with {tag}
          res = await fetchJson(`/clp/${encodeURIComponent(ip)}/tags/remove`, defaultFetchOpts('POST', { tag }));
        }
        if (res.ok) {
          // remove from DOM
          const li = target.closest('.tag-item');
          if (li) li.remove();
          // if empty, add no-tags message
          if (tagListContainer.children.length === 0) {
            const li2 = document.createElement('li');
            li2.id = 'no-tags-msg';
            li2.textContent = 'Nenhuma tag associada.';
            tagListContainer.appendChild(li2);
          }
          if (tagMessage) tagMessage.textContent = res.data && res.data.message ? res.data.message : 'Tag removida';
        } else {
          if (tagMessage) tagMessage.textContent = res.data && res.data.message ? res.data.message : 'Falha ao remover tag';
        }
      });
    }

    // --- Rename CLP (tries /<ip>/edit-name then /clp/rename) ---
    async function renameClp(newName) {
      if (!newName) return;
      let res = await fetchJson(`/clp/${encodeURIComponent(ip)}/edit-name`, defaultFetchOpts('POST', { nome: newName }));
      if (!res.ok || res.status === 404) {
        res = await fetchJson('/clp/rename', defaultFetchOpts('POST', { ip, novo_nome: newName }));
      }
      if (res.ok) {
        if (clpNameSpan) clpNameSpan.textContent = newName;
        showActionMsg('Nome atualizado', 2000);
      } else {
        const msg = res.data && res.data.message ? res.data.message : res.error ? String(res.error) : `HTTP ${res.status}`;
        alert('Erro ao renomear: ' + msg);
      }
    }

    // Edit name UI binding
    if (editNameBtn && editMode && viewMode && saveNameBtn && cancelNameBtn && inputClpName) {
      editNameBtn.addEventListener('click', () => {
        viewMode.style.display = 'none';
        editMode.style.display = 'flex';
        inputClpName.value = clpNameSpan ? clpNameSpan.textContent : '';
        inputClpName.focus();
      });
      cancelNameBtn.addEventListener('click', () => {
        editMode.style.display = 'none';
        viewMode.style.display = 'flex';
      });
      saveNameBtn.addEventListener('click', async () => {
        const novo = inputClpName.value.trim();
        editMode.style.display = 'none';
        viewMode.style.display = 'flex';
        if (!novo || (clpNameSpan && novo === clpNameSpan.textContent)) return;
        await renameClp(novo);
      });
    }

    // --- initial UI population for tags/buttons safety ---
    // if tagListContainer is present but empty, try to render placeholder
    if (tagListContainer && tagListContainer.children.length === 0) {
      const li = document.createElement('li');
      li.id = 'no-tags-msg';
      li.textContent = 'Nenhuma tag associada.';
      tagListContainer.appendChild(li);
    }

    // final: expose a debug function
    window.__CLP_det_update = atualizarInfo;
  });
})();

// detalhes.js

// --- Funções auxiliares ---
function showActionMsg(text, timeout = 4000) {
    const el = document.getElementById('mensagem');
    if (el) {
        el.textContent = text;
        if (timeout) setTimeout(() => el.textContent = '', timeout);
    }
}

function showClpMsg(text, timeout = 4000) {
    const el = document.getElementById('mensagemCLP');
    if (el) {
        el.textContent = text;
        if (timeout) setTimeout(() => el.textContent = '', timeout);
    }
}

async function fetchJson(url, opts) {
    try {
        const resp = await fetch(url, opts);
        if (!resp.ok) {
            return { ok: false, error: `HTTP error! status: ${resp.status}` };
        }
        return await resp.json();
    } catch (err) {
        return { ok: false, error: err.toString() };
    }
}

// --- Bloco principal ---
document.addEventListener('DOMContentLoaded', () => {

    // --- Elementos principais ---
    const ip = document.getElementById('clpIp')?.textContent.trim();
    if (!ip) {
        console.error("Não foi possível encontrar o IP do CLP.");
        return;
    }

    const btnConnect = document.getElementById('btnConnect');
    const btnDisconnect = document.getElementById('btnDisconnect');
    const btnReadRegister = document.getElementById('btnReadRegister');
    const logContainer = document.getElementById('logContainer');
    const tagListContainer = document.getElementById('tag-list-container');
    const tagMessage = document.getElementById('tagMessage');
    const inputAssignTag = document.getElementById('inputAssignTag');
    const globalTagsDatalist = document.getElementById('globalTags');
    const btnAssignTag = document.getElementById('btnAssignTag');

    const viewMode = document.getElementById('viewMode');
    const editMode = document.getElementById('editMode');
    const editNameBtn = document.getElementById('editNameBtn');
    const saveNameBtn = document.getElementById('saveNameBtn');
    const cancelNameBtn = document.getElementById('cancelNameBtn');
    const clpNameSpan = document.getElementById('clpName');
    const inputClpName = document.getElementById('inputClpName');

    // --- Atualiza informações do CLP ---
    async function atualizarInfo() {
        const res = await fetchJson(`/clp/${ip}/info`);
        if (!res.ok) return;

        const clp = res.clp;
        const statusEl = document.getElementById('statusText');
        const connectContainer = document.getElementById('connect-container');
        const disconnectContainer = document.getElementById('disconnect-container');

        if (!statusEl || !connectContainer || !disconnectContainer) return;

        statusEl.textContent = 'Status: ' + clp.status;
        statusEl.className = clp.status === 'Online' ? 'status_online' : 'status_offline';

        connectContainer.style.display = clp.status === 'Online' ? 'none' : 'inline-block';
        disconnectContainer.style.display = clp.status === 'Online' ? 'inline-block' : 'none';

        // Logs
        if (logContainer && clp.logs) {
            logContainer.innerHTML = '';
            clp.logs.slice().reverse().forEach(logLine => {
                const logEntry = document.createElement('div');
                logEntry.textContent = logLine;
                logContainer.appendChild(logEntry);
            });
        }
    }

    setInterval(atualizarInfo, 5000);
    atualizarInfo();

    // --- Conectar / Desconectar ---
    if (btnConnect) {
        btnConnect.addEventListener('click', async () => {
            const selectedPort = document.getElementById('portSelect').value;
            showClpMsg(`Iniciando conexão na porta ${selectedPort}...`);
            await fetchJson(`/clp/${ip}/connect`, {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ port: Number(selectedPort) })
            });
        });
    }

    if (btnDisconnect) {
        btnDisconnect.addEventListener('click', async () => {
            showClpMsg('Desconectando...');
            await fetchJson(`/clp/${ip}/disconnect`, { method: 'POST' });
            atualizarInfo();
        });
    }

    // --- Leitura de registrador ---
    if (btnReadRegister) {
        btnReadRegister.addEventListener('click', async () => {
            const address = document.getElementById('inputAddress').value;
            const resultDiv = document.getElementById('readResult');
            if (!address) {
                resultDiv.innerHTML = `<span style="color:red;">Por favor, insira um endereço.</span>`;
                return;
            }
            showActionMsg(`Lendo endereço ${address}...`);
            const res = await fetchJson(`/clp/${ip}/read_register`, {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ address: Number(address) })
            });
            if (res.ok) {
                resultDiv.innerHTML = `Endereço <strong>${res.address}</strong> = <strong>${res.value}</strong>`;
                showActionMsg('Leitura concluída!');
            } else {
                resultDiv.innerHTML = `<span style="color:red;">Erro: ${res.error}</span>`;
                showActionMsg(`Falha na leitura do endereço ${address}.`);
            }
        });
    }

    // --- Edição do nome do CLP ---
    const enterEditMode = () => { viewMode.style.display='none'; editMode.style.display='flex'; inputClpName.value=clpNameSpan.textContent; inputClpName.focus(); };
    const exitEditMode = () => { viewMode.style.display='flex'; editMode.style.display='none'; };

    const saveNewName = () => {
        const novoNome = inputClpName.value.trim();
        if (!novoNome || novoNome === clpNameSpan.textContent) { exitEditMode(); return; }

        fetch('/clp/rename', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ ip, novo_nome: novoNome })
        }).then(r=>r.json()).then(data=>{
            if(data.success){ clpNameSpan.textContent = novoNome; }
            else{ alert('Erro: '+data.message); }
        }).catch(err=>{ console.error(err); alert('Erro de comunicação.'); })
          .finally(()=>exitEditMode());
    };

    if(editNameBtn) editNameBtn.addEventListener('click', enterEditMode);
    if(saveNameBtn) saveNameBtn.addEventListener('click', saveNewName);
    if(cancelNameBtn) cancelNameBtn.addEventListener('click', exitEditMode);

    // --- Carregar tags globais ---
    async function carregarTagsGlobais() {
        try {
            const res = await fetchJson('/clp/tags');
            if(res.ok && res.tags){
                globalTagsDatalist.innerHTML = '';
                res.tags.forEach(tag=>{
                    const opt = document.createElement('option');
                    opt.value = tag;
                    globalTagsDatalist.appendChild(opt);
                });
            }
        } catch(e){ console.error('Erro tags globais:', e); }
    }
    carregarTagsGlobais();

    // --- Adicionar / Associar tag ---
    if(btnAssignTag){
        btnAssignTag.addEventListener('click', async ()=>{
            const tagValue = inputAssignTag.value.trim();
            tagMessage.textContent = '';
            if(!tagValue){ tagMessage.textContent='Insira ou escolha uma tag.'; return; }

            // Garante que exista na lista global
            await fetchJson('/clp/tags', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body: JSON.stringify({ tag: tagValue })
            });

            // Associa ao CLP
            const assignRes = await fetchJson(`/clp/${ip}/tags/assign`, {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body: JSON.stringify({ tag: tagValue })
            });

            tagMessage.textContent = assignRes.message;

            if(assignRes.success){
                const noTagsMsg = document.getElementById('no-tags-msg');
                if(noTagsMsg) noTagsMsg.remove();

                const exists = Array.from(tagListContainer.querySelectorAll('.tag-item > span:first-child'))
                                    .some(item=>item.textContent===tagValue);
                if(!exists){
                    const li = document.createElement('li');
                    li.className='tag-item';
                    li.innerHTML = `<span>${tagValue}</span><span class="remove-tag" data-tag="${tagValue}" title="Remover Tag">&times;</span>`;
                    tagListContainer.appendChild(li);
                }
                inputAssignTag.value='';
                carregarTagsGlobais();
            }
        });
    }

    // --- Remover tag ---
    if(tagListContainer){
        tagListContainer.addEventListener('click', async (event)=>{
            if(event.target && event.target.classList.contains('remove-tag')){
                const tagToRemove = event.target.dataset.tag;
                try{
                    const encodedTag = encodeURIComponent(tagToRemove);
                    const res = await fetchJson(`/clp/${ip}/tags/${encodedTag}`, { method:'DELETE' });
                    tagMessage.textContent = res.message;
                    if(res.success){
                        event.target.parentElement.remove();
                        if(tagListContainer.children.length===0){
                            const li = document.createElement('li');
                            li.id='no-tags-msg';
                            li.textContent='Nenhuma tag associada.';
                            tagListContainer.appendChild(li);
                        }
                    }
                }catch(err){ console.error(err); tagMessage.textContent='Erro ao remover a tag.'; }
            }
        });
    }

});

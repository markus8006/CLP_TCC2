
document.addEventListener('DOMContentLoaded', () => {

    // --------------------------
    // Funções auxiliares
    // --------------------------
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
            if (!resp.ok) return { ok: false, error: `HTTP error! status: ${resp.status}` };
            return await resp.json();
        } catch (err) {
            return { ok: false, error: err.toString() };
        }
    }

    // --------------------------
    // Parte 1: Tags
    // --------------------------
    const btnAddTag = document.getElementById('btnAddTag');
    if (btnAddTag) {
        btnAddTag.addEventListener('click', async () => {
            const ip = document.getElementById('clpIp')?.textContent;
            const inputTag = document.getElementById('inputTag');
            const tagMessage = document.getElementById('tagMessage');
            if (!ip || !inputTag || !tagMessage) return;

            const newTag = inputTag.value.trim();
            if (!newTag) {
                tagMessage.textContent = 'Por favor, insira uma tag.';
                return;
            }

            const data = await fetchJson(`/clp/${ip}/tags`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tag: newTag })
            });

            tagMessage.textContent = data.message;
            if (data.success) {
                const tagListContainer = document.getElementById('tag-list-container');
                if (tagListContainer) {
                    tagListContainer.innerHTML = '';
                    data.tags.forEach(tag => {
                        const li = document.createElement('li');
                        li.className = 'tag-item';
                        li.textContent = tag;
                        tagListContainer.appendChild(li);
                    });
                }
                inputTag.value = '';
            }
        });
    }

    // --------------------------
    // Parte 2: Conexão e leitura
    // --------------------------
    const ip = document.getElementById('clpIp')?.textContent;
    if (ip) {
        const btnConnect = document.getElementById('btnConnect');
        const btnDisconnect = document.getElementById('btnDisconnect');
        const btnReadRegister = document.getElementById('btnReadRegister');
        const logContainer = document.getElementById('logContainer');

        async function atualizarInfo(ip) {
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

            if (logContainer && clp.logs) {
                logContainer.innerHTML = '';
                clp.logs.slice().reverse().forEach(logLine => {
                    const logEntry = document.createElement('div');
                    logEntry.textContent = logLine;
                    logContainer.appendChild(logEntry);
                });
            }
        }

        if (btnConnect) {
            btnConnect.addEventListener('click', async () => {
                const selectedPort = document.getElementById('portSelect')?.value;
                if (!selectedPort) return;
                showClpMsg(`Iniciando conexão na porta ${selectedPort}...`);
                await fetchJson(`/clp/${ip}/connect`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ port: Number(selectedPort) })
                });
            });
        }

        if (btnDisconnect) {
            btnDisconnect.addEventListener('click', async () => {
                showClpMsg('Desconectando...');
                await fetchJson(`/clp/${ip}/disconnect`, { method: 'POST' });
                atualizarInfo(ip);
            });
        }

        if (btnReadRegister) {
            btnReadRegister.addEventListener('click', async () => {
                const address = document.getElementById('inputAddress')?.value;
                const resultDiv = document.getElementById('readResult');
                if (!address || !resultDiv) return;

                showActionMsg(`Lendo endereço ${address}...`);
                const res = await fetchJson(`/clp/${ip}/read_register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ address: Number(address) })
                });

                if (res.ok) {
                    resultDiv.innerHTML = `Endereço <strong>${res.address}</strong> = <strong>${res.value}</strong>`;
                    showActionMsg('Leitura concluída com sucesso!');
                } else {
                    resultDiv.innerHTML = `<span style="color: red;">Erro: ${res.error}</span>`;
                    showActionMsg(`Falha na leitura do endereço ${address}.`);
                }
            });
        }

        // Atualização periódica
        setInterval(() => atualizarInfo(ip), 5000);
        atualizarInfo(ip);
    }

    // --------------------------
    // Parte 3: Edição do nome
    // --------------------------
    const viewMode = document.getElementById('viewMode');
    const editMode = document.getElementById('editMode');
    const editNameBtn = document.getElementById('editNameBtn');
    const saveNameBtn = document.getElementById('saveNameBtn');
    const cancelNameBtn = document.getElementById('cancelNameBtn');
    const clpNameSpan = document.getElementById('clpName');
    const inputClpName = document.getElementById('inputClpName');
    const clpIpSpan = document.getElementById('clpIp');

    const enterEditMode = () => {
        if(viewMode && editMode && inputClpName && clpNameSpan) {
            viewMode.style.display = 'none';
            editMode.style.display = 'flex';
            inputClpName.value = clpNameSpan.textContent;
            inputClpName.focus();
        }
    };

    const exitEditMode = () => {
        if(viewMode && editMode) {
            viewMode.style.display = 'flex';
            editMode.style.display = 'none';
        }
    };

    const saveNewName = () => {
        if (!inputClpName || !clpNameSpan || !clpIpSpan) return;
        const novoNome = inputClpName.value.trim();
        const clpIp = clpIpSpan.textContent;

        if (!novoNome || novoNome === clpNameSpan.textContent) {
            exitEditMode();
            return;
        }

        fetch('/clp/rename', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip: clpIp, novo_nome: novoNome }),
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) clpNameSpan.textContent = novoNome;
            else alert('Erro ao atualizar o nome: ' + data.message);
        })
        .catch(err => {
            console.error(err);
            alert('Erro de comunicação com o servidor.');
        })
        .finally(() => exitEditMode());
    };

    if (editNameBtn) editNameBtn.addEventListener('click', enterEditMode);
    if (saveNameBtn) saveNameBtn.addEventListener('click', saveNewName);
    if (cancelNameBtn) cancelNameBtn.addEventListener('click', exitEditMode);

});


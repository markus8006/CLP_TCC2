// Funções auxiliares globais
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


// --- CORREÇÃO: Bloco Único de Execução ---
document.addEventListener('DOMContentLoaded', () => {

    // --- Parte 1: Lógica de Conexão e Atualização ---
    const ip = document.getElementById('clpIp')?.textContent;
    if (!ip) {
        console.error("Não foi possível encontrar o IP do CLP na página.");
        return;
    }
    
    const btnConnect = document.getElementById('btnConnect');
    const btnDisconnect = document.getElementById('btnDisconnect');
    const btnReadRegister = document.getElementById('btnReadRegister');
    const logContainer = document.getElementById('logContainer');

    // Função para atualizar informações da página
    async function atualizarInfo(ip) {
        const res = await fetchJson(`/clp/${ip}/info`);
        if (!res.ok) return;

        const clp = res.clp;
        const statusEl = document.getElementById('statusText');
        const connectContainer = document.getElementById('connect-container');
        const disconnectContainer = document.getElementById('disconnect-container');

        // Verificação para garantir que os elementos existem antes de usá-los
        if (!statusEl || !connectContainer || !disconnectContainer) {
            console.error("Elementos de status ou botões não encontrados no HTML.");
            return;
        }
        
        statusEl.textContent = 'Status: ' + clp.status;
        statusEl.className = clp.status === 'Online' ? 'status_online' : 'status_offline';

        if (clp.status === 'Online') {
            connectContainer.style.display = 'none';
            disconnectContainer.style.display = 'inline-block';
        } else {
            connectContainer.style.display = 'inline-block';
            disconnectContainer.style.display = 'none';
        }

        if (logContainer && clp.logs) {
            logContainer.innerHTML = '';
            clp.logs.slice().reverse().forEach(logLine => {
                const logEntry = document.createElement('div');
                logEntry.textContent = logLine;
                logContainer.appendChild(logEntry);
            });
        }
    }
    
    // Listeners dos botões de conexão/desconexão
    if (btnConnect) {
        btnConnect.addEventListener('click', async () => {
            const selectedPort = document.getElementById('portSelect').value;
            showClpMsg(`Iniciando conexão na porta ${selectedPort}...`);
            await fetchJson(`/clp/${ip}/connect`, {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ port: Number(selectedPort) })
            });
            // A atualização automática vai pegar o novo status
        });
    }

    if (btnDisconnect) {
        btnDisconnect.addEventListener('click', async () => {
            showClpMsg('Desconectando...');
            await fetchJson(`/clp/${ip}/disconnect`, { method: 'POST' });
            atualizarInfo(ip); // Força uma atualização imediata
        });
    }

    // Listener do botão de ler registrador
    if (btnReadRegister) {
        btnReadRegister.addEventListener('click', async () => {
            const address = document.getElementById('inputAddress').value;
            const resultDiv = document.getElementById('readResult');
            if (!address) {
                resultDiv.innerHTML = `<span style="color: red;">Por favor, insira um endereço.</span>`;
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
                showActionMsg('Leitura concluída com sucesso!');
            } else {
                resultDiv.innerHTML = `<span style="color: red;">Erro: ${res.error}</span>`;
                showActionMsg(`Falha na leitura do endereço ${address}.`);
            }
        });
    }

    // Inicia a atualização periódica e chama uma vez no início
    setInterval(() => atualizarInfo(ip), 5000);
    atualizarInfo(ip);


    // --- Parte 2: Lógica para Edição do Nome do CLP ---
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
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                clpNameSpan.textContent = novoNome;
            } else {
                alert('Erro ao atualizar o nome: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erro na requisição:', error);
            alert('Ocorreu um erro de comunicação com o servidor.');
        })
        .finally(() => {
            exitEditMode();
        });
    };

    if (editNameBtn) editNameBtn.addEventListener('click', enterEditMode);
    if (saveNameBtn) saveNameBtn.addEventListener('click', saveNewName);
    if (cancelNameBtn) cancelNameBtn.addEventListener('click', exitEditMode);
});
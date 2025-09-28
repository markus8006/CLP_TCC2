// static/scripts/detalhes.js
// Script unificado para página de detalhes do CLP
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
        const opts = { method, credentials: 'same-origin', headers };
        if (body !== null) opts.body = JSON.stringify(body);
        return opts;
    }

    async function fetchJson(url, opts) {
        try {
            const resp = await fetch(url, opts);
            const text = await resp.text();
            let data = null;
            try { data = text ? JSON.parse(text) : null; } catch (e) { data = text; }
            return { ok: resp.ok, status: resp.status, data };
        } catch (err) {
            return { ok: false, status: 0, error: err };
        }
    }

    function showClpMsg(text, timeout = 4000) {
        const el = document.getElementById('mensagemCLP');
        if (!el) return;
        el.textContent = text;
        if (timeout) setTimeout(() => { if (el) el.textContent = ''; }, timeout);
    }

    const $ = id => document.getElementById(id);

    // --- Main ---
    document.addEventListener('DOMContentLoaded', () => {
        let ip = null;
        const ipEl = $('clpIp');
        if (ipEl) ip = ipEl.textContent.trim();
        if (!ip) {
            console.error('detalhes.js: IP do CLP não encontrado.');
            return;
        }

        // --- Elements ---
        const btnConnect = $('btnConnect');
        const btnDisconnect = $('btnDisconnect');
        const btnReadRegister = $('btnReadRegister');
        const readResult = $('readResult');
        const logContainer = $('logContainer');
        const statusText = $('statusText');
        const connectContainer = $('connect-container');
        const disconnectContainer = $('disconnect-container');
        const registersContainer = $('registers-container');

        // --- Fetch e Atualização ---
        async function atualizarInfo() {
            // Rota corrigida para /clp/ (singular)
            const res = await fetchJson(`/clp/${encodeURIComponent(ip)}/values`, defaultFetchOpts('GET'));
            if (!res.ok || !res.data) return;

            const clp = res.data;

            // Atualiza o Status
            if (statusText) {
                statusText.textContent = 'Status: ' + (clp.status || 'Offline');
                statusText.className = (clp.status === 'Online') ? 'status_online' : 'status_offline';
            }
            if (connectContainer) connectContainer.style.display = clp.status === 'Online' ? 'none' : 'inline-block';
            if (disconnectContainer) disconnectContainer.style.display = clp.status === 'Online' ? 'inline-block' : 'none';

            // Atualiza os Logs
            if (logContainer) {
                logContainer.innerHTML = '';
                const logs = clp.logs || [];
                logs.slice(-200).forEach(logEntry => {
                    const div = document.createElement('div');
                    if (typeof logEntry === 'object' && logEntry.data && logEntry.detalhes) {
                        div.textContent = `[${logEntry.data}] ${logEntry.detalhes}`;
                    } else {
                        div.textContent = logEntry;
                    }
                    logContainer.appendChild(div);
                });
                logContainer.scrollTop = logContainer.scrollHeight;
            }

            // Atualiza a exibição dos valores dos registradores
            if (registersContainer && clp.registers_values) {
                registersContainer.innerHTML = '';
                const registers = clp.registers_values;
                const addresses = Object.keys(registers);

                if (addresses.length === 0) {
                    registersContainer.innerHTML = '<p>Nenhum registrador lido ainda.</p>';
                } else {
                    addresses.sort((a, b) => a - b).forEach(addr => {
                        const value = registers[addr];
                        const card = document.createElement('div');
                        card.className = 'register-card';
                        card.innerHTML = `
                            <div class="register-addr">Endereço: ${addr}</div>
                            <div class="register-val">${value}</div>
                        `;
                        registersContainer.appendChild(card);
                    });
                }
            }
        }

        setInterval(atualizarInfo, 2000);
        atualizarInfo();

        // --- Lógica de Conectar/Desconectar ---
        if (btnConnect) {
            btnConnect.addEventListener('click', async () => {
                const portSel = $('portSelect');
                const port = portSel ? Number(portSel.value) : 502;
                showClpMsg(`Iniciando conexão na porta ${port}...`);
                // Rota corrigida para /clp/ (singular)
                const res = await fetchJson(`/clp/${encodeURIComponent(ip)}/poll/start`, defaultFetchOpts('POST', { port }));
                if (res.ok) {
                    showClpMsg('Conexão iniciada', 2500);
                    atualizarInfo();
                } else {
                    showClpMsg('Falha ao conectar: ' + (res.data?.message || 'Erro'), 5000);
                }
            });
        }

        if (btnDisconnect) {
            btnDisconnect.addEventListener('click', async () => {
                showClpMsg('Desconectando...');
                // Rota corrigida para /clp/ (singular)
                const res = await fetchJson(`/clp/${encodeURIComponent(ip)}/poll/stop`, defaultFetchOpts('POST'));
                if (res.ok) {
                    showClpMsg('Desconectado', 2500);
                    atualizarInfo();
                } else {
                    showClpMsg('Falha ao desconectar', 4000);
                }
            });
        }
        
        // --- Lógica de Leitura Manual de Registrador ---
        if (btnReadRegister) {
            btnReadRegister.addEventListener('click', async () => {
                const addrEl = $('inputAddress');
                if (!addrEl) return;
                const address = Number(addrEl.value);
                if (Number.isNaN(address)) {
                    if (readResult) readResult.innerHTML = '<span style="color:red">Endereço inválido</span>';
                    return;
                }
                
                // Rota corrigida para /clp/ (singular)
                const res = await fetchJson(`/clp/${encodeURIComponent(ip)}/read`, defaultFetchOpts('POST', { address, count: 1 }));
                
                if (res.ok && res.data.success) {
                    if (readResult) readResult.innerHTML = `Endereço <strong>${address}</strong> = <strong>${JSON.stringify(res.data.value)}</strong>`;
                } else {
                    if (readResult) readResult.innerHTML = `<span style="color:red">Erro: ${res.data.message || 'Falha na leitura'}</span>`;
                }
            });
        }
    });
})();
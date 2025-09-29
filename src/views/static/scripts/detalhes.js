(() => {
    // --- Helpers (sem alterações) ---
    function getCsrfToken() {
        const m = document.querySelector('meta[name="csrf-token"]') || document.querySelector('meta[name="csrf_token"]');
        return m ? m.content : null;
    }

    function defaultFetchOpts(method = 'GET', body = null) {
        const headers = { 'Accept': 'application/json' };
        const token = getCsrfToken();
        if (token) { headers['X-CSRFToken'] = token; headers['X-CSRF-Token'] = token; }
        if (method !== 'GET' && method !== 'HEAD') headers['Content-Type'] = 'application/json';
        const opts = { method, credentials: 'same-origin', headers };
        if (body !== null) opts.body = JSON.stringify(body);
        return opts;
    }

    async function fetchJson(url, opts) {
        try {
            const resp = await fetch(url, opts);
            const text = await resp.text();
            let data = null;
            try { data = text ? JSON.parse(text) : null; } catch { data = text; }
            return { ok: resp.ok, status: resp.status, data };
        } catch (err) { return { ok: false, status: 0, error: err }; }
    }

    const $ = id => document.getElementById(id);
    const charts = {};

    // --- Lógica dos Gráficos ---
    function criarGraficos() {
        // Remove gráficos de CPU/Memória que são de exemplo
        const container = document.querySelector('.graficos .linha-graficos');
        if (container) container.innerHTML = '';
        
        // Cria um único gráfico para todos os registradores
        const canvasRegs = document.createElement('canvas');
        canvasRegs.id = 'graficoRegistradores';
        
        if (container) {
            const div = document.createElement('div');
            div.className = 'grafico-container';
            div.style.width = '100%'; // Ocupa a largura toda
            div.innerHTML = '<h3>Valores dos Registradores</h3>';
            div.appendChild(canvasRegs);
            container.appendChild(div);
            
            const ctxRegs = canvasRegs.getContext('2d');
            charts.registradores = new Chart(ctxRegs, {
                type: 'line',
                data: { labels: [], datasets: [] },
                options: {
                    animation: false,
                    responsive: true,
                    scales: { x: { display: false } },
                    plugins: { legend: { position: 'top' } }
                }
            });
        }
    }

    function atualizarGraficoRegistradores(registers) {
        const chart = charts.registradores;
        if (!chart) return;

        const now = new Date().toLocaleTimeString();

        // Adiciona um novo ponto no tempo (eixo X)
        chart.data.labels.push(now);
        if (chart.data.labels.length > 50) chart.data.labels.shift();

        // Itera sobre cada nome de registador (ex: "Dados_Simulados_Bloco_1")
        Object.entries(registers).forEach(([name, values]) => {
            // Garante que o valor é um array
            const valueArray = Array.isArray(values) ? values : [values];

            // Itera sobre cada valor dentro do array (ex: 0, 1, 2, 3, 4)
            valueArray.forEach((value, index) => {
                const datasetLabel = `${name}[${index}]`; // Cria uma legenda única, ex: "Bloco_1[0]"

                let dataset = chart.data.datasets.find(d => d.label === datasetLabel);

                // Se não existe uma linha para este registador, cria uma nova
                if (!dataset) {
                    dataset = {
                        label: datasetLabel,
                        data: Array(chart.data.labels.length - 1).fill(null), // Preenche dados passados com nulo
                        borderColor: '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0'),
                        fill: false,
                        tension: 0.1
                    };
                    chart.data.datasets.push(dataset);
                }

                // Adiciona o novo valor e remove o mais antigo se necessário
                dataset.data.push(value);
                if (dataset.data.length > 50) {
                    dataset.data.shift();
                }
            });
        });

        // Garante que todos os datasets têm o mesmo comprimento
        chart.data.datasets.forEach(dataset => {
            while (dataset.data.length < chart.data.labels.length) {
                dataset.data.unshift(null); // Adiciona nulos no início se um novo dataset foi criado
            }
        });
        
        chart.update('quiet');
    }

    // --- Função Principal de Atualização ---
    async function atualizarInfo(ip) {
        const res = await fetchJson(`/clp/${encodeURIComponent(ip)}/values`, defaultFetchOpts('GET'));
        if (!res.ok || !res.data) return;
        const clp = res.data;

        // Atualiza Status e Logs (sem alterações)
        // ...

        // Atualiza os cards de registradores (sem alterações)
        if ($('registers-container') && clp.registers_values) {
            const container = $('registers-container');
            container.innerHTML = '';
            const addresses = Object.keys(clp.registers_values);
            if (addresses.length === 0) container.innerHTML = '<p>Nenhum registrador lido ainda.</p>';
            else {
                addresses.forEach(addr => {
                    const card = document.createElement('div');
                    card.className = 'register-card';
                    // Mostra o array completo no card
                    card.innerHTML = `<div class="register-addr">${addr}</div><div class="register-val">${JSON.stringify(clp.registers_values[addr])}</div>`;
                    container.appendChild(card);
                });
            }
        }
        
        // --- ATUALIZAÇÃO DOS GRÁFICOS ---
        if (clp.registers_values) {
            atualizarGraficoRegistradores(clp.registers_values);
        }
    }

    // --- Inicialização ---
    document.addEventListener('DOMContentLoaded', () => {
        const ip = $('clpIp')?.textContent.trim();
        if (!ip) return console.error('IP do CLP não encontrado.');
        
        criarGraficos();
        
        // Inicia a atualização periódica
        atualizarInfo(ip);
        setInterval(() => atualizarInfo(ip), 2000); // Intervalo de 2 segundos

        // Adiciona eventos aos botões (sem alterações)
        // ...
    });
})();
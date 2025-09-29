(() => {
    // --- Helpers ---
    const $ = id => document.getElementById(id);

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

    const charts = {};

    // --- Criação dos gráficos ---
    function criarGraficos() {
        // CPU
        const ctxCpu = $('graficoCpu').getContext('2d');
        charts.cpu = new Chart(ctxCpu, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Uso de CPU (%)', data: [], borderColor: '#ff00ff', backgroundColor: 'rgba(255,0,255,0.2)', fill: true, tension: 0.4 }] },
            options: { responsive: true, maintainAspectRatio: false }
        });

        // Memória
        const ctxMem = $('graficoMemoria').getContext('2d');
        charts.memoria = new Chart(ctxMem, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Uso de Memória (%)', data: [], borderColor: '#00ffff', backgroundColor: 'rgba(0,255,255,0.2)', fill: true, tension: 0.4 }] },
            options: { responsive: true, maintainAspectRatio: false }
        });

        // Registradores
        const container = document.querySelector('.graficos .linha-graficos');
        const canvasRegs = document.createElement('canvas');
        canvasRegs.id = 'graficoRegistradores';
        const div = document.createElement('div');
        div.className = 'grafico-container';
        div.innerHTML = '<h3>Valores dos Registradores</h3>';
        div.appendChild(canvasRegs);
        container.appendChild(div);

        charts.registradores = new Chart(canvasRegs.getContext('2d'), {
            type: 'line',
            data: { labels: [], datasets: [] },
            options: {
                animation: false,
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { display: false },
                    y: { beginAtZero: true }
                },
                plugins: { legend: { position: 'top', labels: { color: 'white' } } }
            }
        });
    }

    // --- Funções de atualização dos gráficos ---
    function atualizarGraficoSimples(chart, value) {
        if (!chart) return;
        const now = new Date().toLocaleTimeString();
        chart.data.labels.push(now);
        chart.data.datasets[0].data.push(value);

        if (chart.data.labels.length > 20) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }
        chart.update('quiet');
    }

    function atualizarGraficoRegistradores(registers) {
        const chart = charts.registradores;
        if (!chart) return;

        const now = new Date().toLocaleTimeString();
        chart.data.labels.push(now);
        if (chart.data.labels.length > 50) chart.data.labels.shift();

        Object.entries(registers).forEach(([name, obj]) => {
            const valuesRaw = obj && typeof obj === 'object' && 'value' in obj ? obj.value : obj;
            const valueArray = Array.isArray(valuesRaw) ? valuesRaw : [valuesRaw];

            valueArray.forEach((value, index) => {
                const label = `${name}[${index}]`;
                let dataset = chart.data.datasets.find(d => d.label === label);
                if (!dataset) {
                    dataset = {
                        label,
                        data: Array(chart.data.labels.length - 1).fill(null),
                        borderColor: '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0'),
                        fill: false,
                        tension: 0.1
                    };
                    chart.data.datasets.push(dataset);
                }
                dataset.data.push(value);
                if (dataset.data.length > 50) dataset.data.shift();
            });
        });

        chart.data.datasets.forEach(d => {
            while (d.data.length < chart.data.labels.length) d.data.unshift(null);
        });

        chart.update('quiet');
    }

    // --- Atualização periódica ---
    async function atualizarInfo(ip) {
        const res = await fetchJson(`/clp/${encodeURIComponent(ip)}/values`, defaultFetchOpts('GET'));
        if (!res.ok || !res.data) return;
        const clp = res.data;

        // Atualiza cards de registradores
        if ($('registers-container') && clp.registers_values) {
            const container = $('registers-container');
            container.innerHTML = '';
            const addresses = Object.keys(clp.registers_values);
            if (addresses.length === 0) {
                container.innerHTML = '<p>Nenhum registrador lido ainda.</p>';
            } else {
                addresses.forEach(addr => {
                    const card = document.createElement('div');
                    card.className = 'register-card';
                    card.innerHTML = `<div class="register-addr">${addr}</div><div class="register-val">${JSON.stringify(clp.registers_values[addr])}</div>`;
                    container.appendChild(card);
                });
            }
        }

        // Atualiza os gráficos
        if (clp.registers_values) {
            atualizarGraficoRegistradores(clp.registers_values);
        }

        // **LÓGICA ADICIONADA: Atualiza CPU e Memória com dados simulados**
        const fakeCpuUsage = Math.random() * 100;
        const fakeMemUsage = 50 + Math.random() * 20;
        atualizarGraficoSimples(charts.cpu, fakeCpuUsage.toFixed(2));
        atualizarGraficoSimples(charts.memoria, fakeMemUsage.toFixed(2));
    }

    // --- Inicialização ---
    document.addEventListener('DOMContentLoaded', () => {
        const ip = $('clpIp')?.textContent.trim();
        if (!ip) return console.error('IP do CLP não encontrado.');

        criarGraficos();
        atualizarInfo(ip);
        setInterval(() => atualizarInfo(ip), 2000);
    });
})();
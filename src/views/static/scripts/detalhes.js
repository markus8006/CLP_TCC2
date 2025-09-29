(() => {
    // --- Helpers ---
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

    // --- Criação dos gráficos ---
    function criarGraficos() {
        const container = document.querySelector('.graficos .linha-graficos');
        if (!container) return;

        container.innerHTML = ''; // limpa exemplos antigos

        const canvasRegs = document.createElement('canvas');
        canvasRegs.id = 'graficoRegistradores';

        const div = document.createElement('div');
        div.className = 'grafico-container';
        div.style.width = '100%';
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

    // --- Atualiza gráfico com os valores do CLP ---
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
                const datasetLabel = `${name}[${index}]`;
                let dataset = chart.data.datasets.find(d => d.label === datasetLabel);

                if (!dataset) {
                    dataset = {
                        label: datasetLabel,
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

        // Garante mesmo comprimento de todos datasets
        chart.data.datasets.forEach(dataset => {
            while (dataset.data.length < chart.data.labels.length) {
                dataset.data.unshift(null);
            }
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
            if (addresses.length === 0) container.innerHTML = '<p>Nenhum registrador lido ainda.</p>';
            else {
                addresses.forEach(addr => {
                    const card = document.createElement('div');
                    card.className = 'register-card';
                    card.innerHTML = `<div class="register-addr">${addr}</div><div class="register-val">${JSON.stringify(clp.registers_values[addr])}</div>`;
                    container.appendChild(card);
                });
            }
        }

        // Atualiza gráfico
        if (clp.registers_values) atualizarGraficoRegistradores(clp.registers_values);
    }

    // --- Inicialização ---
    document.addEventListener('DOMContentLoaded', () => {
        const ip = $('clpIp')?.textContent.trim();
        if (!ip) return console.error('IP do CLP não encontrado.');

        criarGraficos();

        atualizarInfo(ip);
        setInterval(() => atualizarInfo(ip), 2000); // atualiza a cada 2s
    });
})();

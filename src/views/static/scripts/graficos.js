document.addEventListener('DOMContentLoaded', () => {
    const ctxCpu = document.getElementById('graficoCpu').getContext('2d');
    const graficoCpu = new Chart(ctxCpu, {
        type: 'line',
        data: {
            labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
            datasets: [{
                label: 'Uso de CPU (%)',
                data: [20, 35, 40, 30, 50, 45],
                borderColor: '#00cfff',
                backgroundColor: 'rgba(0, 207, 255, 0.2)',
                fill: true,
                tension: 0.3
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
    ctxCpu.canvas.classList.add('line-chart');

    const ctxMem = document.getElementById('graficoMemoria').getContext('2d');
    const graficoMemoria = new Chart(ctxMem, {
        type: 'doughnut',
        data: {
            labels: ['Usada', 'Livre'],
            datasets: [{ data: [65, 35], backgroundColor: ['#00cfff', '#222'], borderWidth: 2 }]
        },
        options: { responsive: true, maintainAspectRatio: false, cutout: '70%' }
    });
    ctxMem.canvas.classList.add('doughnut-chart');

    // Rede e Disco
    const ctxRede = document.getElementById('graficoRede').getContext('2d');
    const graficoRede = new Chart(ctxRede, { /* seu dataset */ });
    ctxRede.canvas.classList.add('line-chart');

    const ctxDisco = document.getElementById('graficoDisco').getContext('2d');
    const graficoDisco = new Chart(ctxDisco, { /* seu dataset */ });
    ctxDisco.canvas.classList.add('line-chart');
});

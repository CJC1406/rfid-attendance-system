/* =====================================================
   charts.js — Chart.js builders for admin + student analytics
   ===================================================== */

Chart.defaults.color = '#a0a0c0';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = "'Inter', sans-serif";

const PALETTE = {
  accent:  '#6c63ff',
  success: '#00d48a',
  warning: '#ffa502',
  danger:  '#ff4757',
  info:    '#45b3e0',
  purple:  '#a855f7',
};

function gradientFill(ctx, top, bottom) {
  const g = ctx.createLinearGradient(0, 0, 0, ctx.canvas.offsetHeight || 280);
  g.addColorStop(0, top);
  g.addColorStop(1, bottom);
  return g;
}

// ── Attendance Donut ──
function buildDonutChart(canvasId, present, late, absent) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Present', 'Late', 'Absent'],
      datasets: [{
        data: [present, late, absent],
        backgroundColor: [PALETTE.success, PALETTE.warning, PALETTE.danger],
        borderWidth: 2,
        borderColor: '#0a0a0f',
        hoverOffset: 8,
      }],
    },
    options: {
      cutout: '75%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 16, boxWidth: 12, borderRadius: 3, usePointStyle: true },
        },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed}` } },
      },
      animation: { animateScale: true, animateRotate: true },
    },
  });
}

// ── Trend Line Chart ──
function buildTrendChart(canvasId, rows) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  const labels  = rows.map(r => fmtDate(r.date));
  const data    = rows.map(r => r.c);
  const gradient = gradientFill(ctx.getContext('2d'), 'rgba(108,99,255,0.4)', 'rgba(108,99,255,0)');
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Students Present',
        data,
        borderColor: PALETTE.accent,
        backgroundColor: gradient,
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: PALETTE.accent,
        pointBorderColor: '#0a0a0f',
        pointBorderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
      },
    },
  });
}

// ── Branch Bar Chart ──
function buildBranchChart(canvasId, rows) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  const labels = rows.map(r => r.branch || 'Unknown');
  const data   = rows.map(r => {
    const max = (r.total_students || 1) * 40;
    return max > 0 ? Math.round(r.present_count / max * 100) : 0;
  });
  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Avg Attendance %',
        data,
        backgroundColor: [PALETTE.accent, PALETTE.success, PALETTE.warning, PALETTE.info, PALETTE.purple],
        borderRadius: 8,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' } },
        x: { grid: { display: false } },
      },
    },
  });
}

// ── Top Students Horizontal Bar ──
function buildTopChart(canvasId, rows) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  const labels = rows.map(r => r.name.split(' ')[0]);
  const data   = rows.map(r => r.present_days);
  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Days Present',
        data,
        backgroundColor: 'rgba(0,212,138,0.7)',
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true }, y: { grid: { display: false } } },
    },
  });
}

// ── Monthly Bar Chart (Student) ──
function buildMonthlyChart(canvasId, rows) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: rows.map(r => r.month),
      datasets: [{
        label: 'Days Present',
        data: rows.map(r => r.c),
        backgroundColor: 'rgba(108,99,255,0.7)',
        borderRadius: 8,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true },
        x: { grid: { display: false } },
      },
    },
  });
}

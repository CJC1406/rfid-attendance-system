/* =====================================================
   main.js — Shared utilities, real-time polling, toasts
   ===================================================== */

// ── Toast system ──
const toastContainer = (() => {
  let el = document.getElementById('toast-container');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toast-container';
    el.className = 'toast-container';
    document.body.appendChild(el);
  }
  return el;
})();

function showToast(msg, type = 'info', duration = 3500) {
  const icons = { success: '✅', danger: '❌', warning: '⚠️', info: 'ℹ️' };
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span>
                     <span class="toast-msg">${msg}</span>`;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('fade-out');
    toast.addEventListener('animationend', () => toast.remove());
  }, duration);
}

// ── Modal helpers ──
function openModal(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.add('active'); document.body.style.overflow = 'hidden'; }
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.remove('active'); document.body.style.overflow = ''; }
}

// Close on overlay click
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
    document.body.style.overflow = '';
  }
});

// Close on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.active').forEach(m => {
      m.classList.remove('active');
    });
    document.body.style.overflow = '';
  }
});

// ── API helpers ──
async function apiFetch(url, options = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
  };
  const res = await fetch(url, { ...defaults, ...options });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Real-time polling ──
class DataPoller {
  constructor(url, callback, interval = 3000) {
    this.url      = url;
    this.callback = callback;
    this.interval = interval;
    this.timer    = null;
  }
  start() { this.fetch(); this.timer = setInterval(() => this.fetch(), this.interval); }
  stop()  { clearInterval(this.timer); }
  async fetch() {
    try {
      const data = await apiFetch(this.url);
      this.callback(data);
    } catch (e) { console.warn('Polling error:', e.message); }
  }
}

// ── Sidebar active link ──
document.addEventListener('DOMContentLoaded', () => {
  const path  = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(link => {
    if (link.getAttribute('href') === path) link.classList.add('active');
  });

  // Mobile menu toggle
  const toggleBtn = document.getElementById('menu-toggle');
  const sidebar   = document.querySelector('.sidebar');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
  }
});

// ── Format helpers ──
function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function fmtTime(t) { return t || '—'; }

function badgeHtml(status) {
  const map = { present: 'present', late: 'late', absent: 'absent' };
  const cls = map[status] || 'absent';
  return `<span class="badge badge-${cls}">${status}</span>`;
}

function photoHtml(row, size = 36) {
  if (row.photo) {
    return `<img src="/static/images/${row.photo}" class="photo-thumb" width="${size}" height="${size}" alt="${row.name}">`;
  }
  const initials = (row.name || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  return `<div class="photo-placeholder" style="width:${size}px;height:${size}px">${initials}</div>`;
}

function initials(name) {
  return (name || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
}

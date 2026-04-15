/* =====================================================
   admin.js — Student CRUD, Attendance management, Filters
   ===================================================== */

// ─────────────────────────────────────────────────────
// STUDENT MANAGEMENT
// ─────────────────────────────────────────────────────
let editingUid = null;
let allStudents = [];

async function loadStudents(filter = '') {
  try {
    allStudents = await apiFetch('/api/students');
    renderStudentTable(filter);
  } catch (e) { showToast(e.message, 'danger'); }
}

function renderStudentTable(filter = '') {
  const tbody = document.getElementById('student-tbody');
  if (!tbody) return;
  const rows = filter
    ? allStudents.filter(s =>
        s.name.toLowerCase().includes(filter.toLowerCase()) ||
        s.usn.toLowerCase().includes(filter.toLowerCase()) ||
        s.branch.toLowerCase().includes(filter.toLowerCase()))
    : allStudents;

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><span class="empty-icon">🎓</span><p>No students found</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map(s => `
    <tr>
      <td>${photoHtml(s)}</td>
      <td><strong>${s.name}</strong></td>
      <td><span style="color:var(--text3);font-size:.8rem">${s.usn}</span></td>
      <td>${s.branch || '—'}</td>
      <td>${s.year || '—'}</td>
      <td><code style="font-size:.8rem;color:var(--accent2)">${s.uid}</code></td>
      <td>
        <div class="d-flex gap-1">
          <button class="btn btn-ghost btn-sm btn-icon" onclick="openEditStudent('${s.uid}')" title="Edit">✏️</button>
          <button class="btn btn-danger btn-sm btn-icon" onclick="deleteStudent('${s.uid}','${s.name}')" title="Delete">🗑️</button>
          <label class="btn btn-ghost btn-sm btn-icon" title="Upload Photo" style="cursor:pointer">
            📷<input type="file" hidden accept="image/*" onchange="uploadPhoto('${s.uid}',this)">
          </label>
        </div>
      </td>
    </tr>`).join('');
}

function openAddStudent() {
  editingUid = null;
  document.getElementById('student-form').reset();
  document.getElementById('student-modal-title').textContent = 'Add Student';
  openModal('student-modal');
}

function openEditStudent(uid) {
  const s = allStudents.find(x => x.uid === uid);
  if (!s) return;
  editingUid = uid;
  document.getElementById('f-uid').value    = s.uid;
  document.getElementById('f-name').value   = s.name;
  document.getElementById('f-usn').value    = s.usn;
  document.getElementById('f-branch').value = s.branch;
  document.getElementById('f-year').value   = s.year;
  document.getElementById('f-uid').disabled = true;
  document.getElementById('student-modal-title').textContent = 'Edit Student';
  openModal('student-modal');
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('student-form');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        uid:      document.getElementById('f-uid').value.trim().toUpperCase(),
        name:     document.getElementById('f-name').value.trim(),
        usn:      document.getElementById('f-usn').value.trim(),
        branch:   document.getElementById('f-branch').value.trim(),
        year:     document.getElementById('f-year').value.trim(),
        password: document.getElementById('f-password').value.trim(),
      };
      try {
        if (editingUid) {
          await apiFetch(`/api/students/${editingUid}`, { method: 'PUT', body: JSON.stringify(payload) });
          showToast('Student updated!', 'success');
        } else {
          await apiFetch('/api/students', { method: 'POST', body: JSON.stringify(payload) });
          showToast('Student added!', 'success');
        }
        closeModal('student-modal');
        loadStudents();
      } catch (e) { showToast(e.message, 'danger'); }
    });
  }

  // Search
  const searchInput = document.getElementById('student-search');
  if (searchInput) {
    searchInput.addEventListener('input', () => renderStudentTable(searchInput.value));
  }

  if (document.getElementById('student-tbody')) loadStudents();
});

async function deleteStudent(uid, name) {
  if (!confirm(`Delete ${name}? This also removes all their attendance records.`)) return;
  try {
    await apiFetch(`/api/students/${uid}`, { method: 'DELETE' });
    showToast(`${name} deleted.`, 'warning');
    loadStudents();
  } catch (e) { showToast(e.message, 'danger'); }
}

async function uploadPhoto(uid, input) {
  const file = input.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append('photo', file);
  try {
    const res = await fetch(`/api/students/${uid}/photo`, { method: 'POST', body: fd });
    if (!res.ok) throw new Error('Upload failed');
    showToast('Photo uploaded!', 'success');
    loadStudents();
  } catch (e) { showToast(e.message, 'danger'); }
}

// ─────────────────────────────────────────────────────
// ATTENDANCE MANAGEMENT
// ─────────────────────────────────────────────────────
async function loadAttendance() {
  const from   = document.getElementById('att-from')?.value || '';
  const to     = document.getElementById('att-to')?.value || '';
  const branch = document.getElementById('att-branch')?.value || '';
  const params = new URLSearchParams({ from, to, branch });
  try {
    const rows = await apiFetch(`/api/attendance?${params}`);
    renderAttendanceTable(rows);
  } catch (e) { showToast(e.message, 'danger'); }
}

function renderAttendanceTable(rows) {
  const tbody = document.getElementById('att-tbody');
  if (!tbody) return;
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><span class="empty-icon">📋</span><p>No records found</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${photoHtml(r)}</td>
      <td><strong>${r.name}</strong><br><span class="text-muted">${r.usn}</span></td>
      <td>${r.branch || '—'}</td>
      <td>${fmtDate(r.date)}</td>
      <td>${fmtTime(r.time)}</td>
      <td>${badgeHtml(r.status)}</td>
      <td>
        <div class="d-flex gap-1">
          <button class="btn btn-ghost btn-sm btn-icon" onclick="editAttendanceStatus(${r.id}, '${r.status}')" title="Edit">✏️</button>
          <button class="btn btn-danger btn-sm btn-icon" onclick="deleteAttendance(${r.id})" title="Delete">🗑️</button>
        </div>
      </td>
    </tr>`).join('');
}

async function editAttendanceStatus(id, currentStatus) {
  const newStatus = prompt(`New status for this record:\n(present / late / absent)`, currentStatus);
  if (!newStatus || !['present','late','absent'].includes(newStatus)) return;
  try {
    await apiFetch(`/api/attendance/${id}`, { method: 'PUT', body: JSON.stringify({ status: newStatus }) });
    showToast('Attendance updated.', 'success');
    loadAttendance();
  } catch (e) { showToast(e.message, 'danger'); }
}

async function deleteAttendance(id) {
  if (!confirm('Delete this attendance record?')) return;
  try {
    await apiFetch(`/api/attendance/${id}`, { method: 'DELETE' });
    showToast('Record deleted.', 'warning');
    loadAttendance();
  } catch (e) { showToast(e.message, 'danger'); }
}

async function manualMark() {
  const uid    = document.getElementById('manual-uid')?.value.trim().toUpperCase();
  const date   = document.getElementById('manual-date')?.value;
  const time   = document.getElementById('manual-time')?.value;
  const status = document.getElementById('manual-status')?.value;
  if (!uid || !date) { showToast('UID and date required.', 'warning'); return; }
  try {
    await apiFetch('/api/attendance/manual', { method: 'POST', body: JSON.stringify({ uid, date, time, status }) });
    showToast('Attendance manually marked!', 'success');
    closeModal('manual-modal');
    loadAttendance();
  } catch (e) { showToast(e.message, 'danger'); }
}

// ─────────────────────────────────────────────────────
// SETTINGS
// ─────────────────────────────────────────────────────
async function loadSettings() {
  if (!document.getElementById('settings-form')) return;
  try {
    const s = await apiFetch('/api/settings');
    document.getElementById('s-cutoff').value      = s.cutoff_time || '09:30';
    document.getElementById('s-late').value        = s.late_threshold || '09:00';
    document.getElementById('s-min-att').value     = s.min_attendance || '75';
    document.getElementById('s-api-key').value     = s.api_key || '';
  } catch(e) { showToast(e.message, 'danger'); }
}

async function saveSettings(e) {
  e.preventDefault();
  const payload = {
    cutoff_time:    document.getElementById('s-cutoff').value,
    late_threshold: document.getElementById('s-late').value,
    min_attendance: document.getElementById('s-min-att').value,
    api_key:        document.getElementById('s-api-key').value,
  };
  try {
    await apiFetch('/api/settings', { method: 'POST', body: JSON.stringify(payload) });
    showToast('Settings saved!', 'success');
  } catch(e) { showToast(e.message, 'danger'); }
}

document.addEventListener('DOMContentLoaded', () => {
  const settingsForm = document.getElementById('settings-form');
  if (settingsForm) {
    loadSettings();
    settingsForm.addEventListener('submit', saveSettings);
  }
  if (document.getElementById('att-tbody')) loadAttendance();
});

let currentFileId = null;
let currentActions = [];

const audioFile = document.getElementById('audioFile');
const fileMeta = document.getElementById('fileMeta');
const playerOriginal = document.getElementById('playerOriginal');
const playerProcessed = document.getElementById('playerProcessed');
const chatInput = document.getElementById('chatInput');
const parseBtn = document.getElementById('parseBtn');
const processBtn = document.getElementById('processBtn');
const actionsList = document.getElementById('actionsList');
const logs = document.getElementById('logs');
const agentSummary = document.getElementById('agentSummary');
const downloadLink = document.getElementById('downloadLink');

const statusText = document.getElementById('statusText');
const formatText = document.getElementById('formatText');
const durationText = document.getElementById('durationText');
const diagnosisText = document.getElementById('diagnosisText');

function setStatus(text) {
  statusText.textContent = text;
}

function renderActions(actions) {
  if (!actions.length) {
    actionsList.innerHTML = '<div class="hint">لم يتم تحديد عمليات بعد.</div>';
    return;
  }
  actionsList.innerHTML = actions.map(a => `<div class="action-item">${a}</div>`).join('');
}

async function uploadFile(file) {
  const form = new FormData();
  form.append('file', file);
  setStatus('جاري الرفع...');

  const res = await fetch('/api/upload', { method: 'POST', body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'فشل الرفع');

  currentFileId = data.file_id;
  playerOriginal.src = URL.createObjectURL(file);
  formatText.textContent = file.name.split('.').pop().toUpperCase();
  durationText.textContent = `${data.analysis.duration_sec} ثانية`;
  diagnosisText.textContent = (data.analysis.diagnosis || []).join('، ');
  fileMeta.innerHTML = `
    <strong>${data.filename}</strong><br>
    القنوات: ${data.analysis.channels} | معدل العينة: ${data.analysis.frame_rate}Hz | dBFS: ${data.analysis.dbfs}<br>
    ${data.analysis.ffmpeg_hint ? `<span style="color:#ffd0a8">${data.analysis.ffmpeg_hint}</span>` : ''}
  `;
  setStatus('تم رفع الملف');
}

audioFile.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    await uploadFile(file);
  } catch (err) {
    setStatus('خطأ');
    alert(err.message);
  }
});

parseBtn.addEventListener('click', async () => {
  const message = chatInput.value.trim();
  if (!message) return alert('اكتب طلبك أولاً.');
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  const data = await res.json();
  currentActions = data.actions || [];
  agentSummary.textContent = data.summary || 'تم فهم الطلب.';
  renderActions(currentActions);
});

processBtn.addEventListener('click', async () => {
  if (!currentFileId) return alert('ارفع ملفًا أولاً.');
  if (!currentActions.length) return alert('اجعل الوكيل يفهم طلبك أولاً.');

  setStatus('جاري المعالجة...');
  logs.innerHTML = 'جاري تنفيذ المعالجة...';
  downloadLink.style.display = 'none';

  const res = await fetch('/api/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: currentFileId, actions: currentActions, silence_min_ms: 900, silence_keep_ms: 120 }),
  });
  const data = await res.json();
  if (!res.ok) {
    setStatus('خطأ');
    logs.innerHTML = data.detail || 'تعذر تنفيذ المعالجة.';
    return;
  }

  playerProcessed.src = data.download_url;
  logs.innerHTML = (data.logs || []).map(x => `• ${x}`).join('<br>');
  durationText.textContent = `${data.analysis.duration_sec} ثانية`;
  diagnosisText.textContent = (data.analysis.diagnosis || []).join('، ');
  downloadLink.href = data.download_url;
  downloadLink.style.display = 'inline-block';
  setStatus('اكتملت المعالجة');
});

document.querySelectorAll('.chip').forEach(btn => {
  btn.addEventListener('click', () => {
    const text = btn.textContent.trim();
    chatInput.value = chatInput.value ? `${chatInput.value}، ${text}` : text;
  });
});

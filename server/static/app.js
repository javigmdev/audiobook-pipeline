const drop = document.getElementById('drop');
const fileInput = document.getElementById('file');
const fname = document.getElementById('fname');
const btn = document.getElementById('btn');
const cancelBtn = document.getElementById('cancel');
const logEl = document.getElementById('log');
const dlBtn = document.getElementById('dl');
const notice = document.getElementById('notice');
let file = null;
let currentJobId = null;

drop.addEventListener('click', () => fileInput.click());
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('over'); });
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', e => {
  e.preventDefault();
  drop.classList.remove('over');
  const f = e.dataTransfer.files[0];
  if (f) setFile(f);
});
fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});

function setFile(f) {
  if (!f.name.toLowerCase().endsWith('.epub')) {
    showNotice('Solo se aceptan archivos .epub', 'warn');
    return;
  }
  file = f;
  fname.textContent = f.name;
  btn.disabled = false;
  hideNotice();
}

function logLine(text, isErr) {
  const p = document.createElement('p');
  if (isErr) p.className = 'err';
  p.textContent = text;
  logEl.appendChild(p);
  logEl.scrollTop = logEl.scrollHeight;
}

function showNotice(msg, type) {
  notice.textContent = msg;
  notice.style.background = type === 'warn' ? '#fff9e6' : '#ffefe6';
  notice.style.color = type === 'warn' ? '#b27b00' : '#ff453a';
  notice.style.display = 'block';
}
function hideNotice() {
  notice.style.display = 'none';
}

cancelBtn.addEventListener('click', async () => {
  if (!currentJobId) return;
  cancelBtn.disabled = true;
  await fetch(`cancel/${currentJobId}`, { method: 'POST' });
});

btn.addEventListener('click', async () => {
  if (!file) return;
  btn.disabled = true;
  cancelBtn.style.display = 'block';
  cancelBtn.disabled = false;
  dlBtn.style.display = 'none';
  logEl.style.display = 'block';
  logEl.innerHTML = '';
  hideNotice();

  const fd = new FormData();
  fd.append('epub', file);
  fd.append('voice', document.getElementById('voice').value);

  let res;
  try {
    res = await fetch('convert', { method: 'POST', body: fd });
  } catch {
    showNotice('Error de red al conectar con el servidor.', 'err');
    btn.disabled = false;
    return;
  }

  const data = await res.json();
  if (data.error) {
    showNotice(data.error, 'err');
    btn.disabled = false;
    cancelBtn.style.display = 'none';
    return;
  }

  currentJobId = data.job_id;
  const evtSrc = new EventSource(`status/${data.job_id}`);

  function finish() {
    evtSrc.close();
    btn.disabled = false;
    cancelBtn.style.display = 'none';
    cancelBtn.disabled = false;
    currentJobId = null;
  }

  evtSrc.onmessage = e => {
    if (e.data === 'DONE') {
      finish();
      logLine('Conversión completada.');
      dlBtn.href = `download/${data.job_id}`;
      dlBtn.style.display = 'block';
    } else if (e.data.startsWith('ERROR:') || e.data === 'CANCELLED') {
      finish();
      logLine(e.data, true);
    } else {
      logLine(e.data);
    }
  };

  evtSrc.onerror = () => {
    finish();
    logLine('Conexión SSE interrumpida.', true);
  };
});

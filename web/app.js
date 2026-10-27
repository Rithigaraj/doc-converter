const form = document.getElementById('convertForm');
const jobsDiv = document.getElementById('jobs');
const warningsDiv = document.getElementById('warnings');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const files = document.getElementById('files').files;
  const target_ext = document.getElementById('target_ext').value;
  const dpi = document.getElementById('dpi').value;
  const quality = document.getElementById('quality').value;
  const options = { dpi: Number(dpi), quality: Number(quality) };
  const fd = new FormData();
  for (let i = 0; i < files.length; i++) {
    fd.append('files', files[i]);
  }
  fd.append('target_ext', target_ext);
  fd.append('options', JSON.stringify(options));
  const res = await fetch('/api/convert/', { method: 'POST', body: fd });
  const data = await res.json();
  if (data.job_ids) {
    data.job_ids.forEach(jid => trackJob(jid));
  }
});

function trackJob(jid) {
  const el = document.createElement('div');
  el.className = 'job';
  el.id = 'job-' + jid;
  el.innerHTML = `<div class="job-header"><span>${jid.slice(0,8)}</span><span class="badge">queued</span></div><div class="job-body">Waiting...</div>`;
  jobsDiv.prepend(el);
  poll(jid, el);
}

async function poll(jid, el) {
  const res = await fetch('/api/jobs/' + jid);
  const data = await res.json();
  const status = data.meta?.status || data.status;
  const badge = el.querySelector('.badge');
  badge.textContent = status;
  badge.className = 'badge ' + status;
  const body = el.querySelector('.job-body');
  if (status === 'finished') {
    const files = data.meta?.files || [];
    const warns = data.meta?.warnings || [];
    if (warns.length) {
      warningsDiv.textContent = warns.map(w => '- ' + w).join('\n');
    }
    body.innerHTML = files.map(f => {
      const name = f.split('/').pop().split('\\').pop();
      return `<div><a href="/api/download/${name}">${name}</a></div>`;
    }).join('');
    return;
  }
  if (status === 'failed') {
    body.textContent = data.meta?.error || 'Failed';
    const warns = data.meta?.warnings || [];
    if (warns.length) {
      warningsDiv.textContent = warns.map(w => '- ' + w).join('\n');
    }
    return;
  }
  setTimeout(() => poll(jid, el), 1500);
}

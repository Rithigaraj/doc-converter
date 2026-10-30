// Doc Converter — Client Controller (Formal Liquid Glass)

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('convertForm');
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const selectedFilesList = document.getElementById('selectedFilesList');
  const targetExtSelect = document.getElementById('targetExtSelect');
  const submitBtn = document.getElementById('submitBtn');
  const queueSection = document.getElementById('queueSection');
  const jobsContainer = document.getElementById('jobsContainer');
  const queueCountBadge = document.getElementById('queueCountBadge');
  const dpiGroup = document.getElementById('dpiGroup');
  const qualityGroup = document.getElementById('qualityGroup');
  const customDpi = document.getElementById('customDpi');
  const customQuality = document.getElementById('customQuality');

  let stagedFiles = [];
  let activeJobs = new Map();

  // 1. Target Format Change triggers relevant options
  function updateOptionVisibility() {
    const target = targetExtSelect.value;
    if (target === 'png' || target === 'jpg') {
      dpiGroup.style.display = 'flex';
      qualityGroup.style.display = target === 'jpg' ? 'flex' : 'none';
    } else {
      dpiGroup.style.display = 'none';
      qualityGroup.style.display = 'none';
    }
  }
  targetExtSelect.addEventListener('change', updateOptionVisibility);
  updateOptionVisibility();

  // 2. Drag & Drop Handling
  dropZone.addEventListener('click', () => fileInput.click());
  dropZone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInput.click();
    }
  });

  ['dragenter', 'dragover'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove('dragover');
    });
  });

  dropZone.addEventListener('drop', (e) => {
    if (e.dataTransfer && e.dataTransfer.files.length > 0) {
      handleFilesAdded(Array.from(e.dataTransfer.files));
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleFilesAdded(Array.from(fileInput.files));
    }
  });

  function handleFilesAdded(newFiles) {
    newFiles.forEach(f => {
      if (!stagedFiles.some(existing => existing.name === f.name && existing.size === f.size)) {
        stagedFiles.push(f);
      }
    });
    renderStagedFiles();
  }

  function renderStagedFiles() {
    if (stagedFiles.length === 0) {
      selectedFilesList.style.display = 'none';
      selectedFilesList.innerHTML = '';
      submitBtn.disabled = true;
      return;
    }

    selectedFilesList.style.display = 'flex';
    selectedFilesList.innerHTML = '';
    stagedFiles.forEach((file, index) => {
      const pill = document.createElement('div');
      pill.className = 'file-pill';
      const sizeStr = file.size > 1024 * 1024 
        ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` 
        : `${Math.round(file.size / 1024)} KB`;
      pill.innerHTML = `
        <span>${escapeHtml(file.name)} (${sizeStr})</span>
        <span class="remove-btn" title="Remove file" data-index="${index}">&times;</span>
      `;
      selectedFilesList.appendChild(pill);
    });

    submitBtn.disabled = false;

    // Attach remove handlers
    selectedFilesList.querySelectorAll('.remove-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.dataset.index, 10);
        stagedFiles.splice(idx, 1);
        renderStagedFiles();
      });
    });
  }

  // 3. Tool Cards Click Handlers
  document.querySelectorAll('.tool-card').forEach(card => {
    card.addEventListener('click', () => {
      const target = card.dataset.target;
      if (target) {
        targetExtSelect.value = target;
        updateOptionVisibility();
        dropZone.scrollIntoView({ behavior: 'smooth', block: 'center' });
        dropZone.click();
      }
    });
  });

  // 4. Form Submission & Conversion
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (stagedFiles.length === 0) {
      alert('Please select or drop at least one file to convert.');
      return;
    }

    const targetExt = targetExtSelect.value;
    const dpi = customDpi.value || '200';
    const quality = customQuality.value || '90';
    const options = { dpi: parseInt(dpi, 10), quality: parseInt(quality, 10) };

    const formData = new FormData();
    stagedFiles.forEach(file => {
      formData.append('files', file);
    });
    formData.append('target_ext', targetExt);
    formData.append('options', JSON.stringify(options));

    submitBtn.disabled = true;
    submitBtn.querySelector('span').textContent = 'Starting Job...';

    try {
      const response = await fetch('/api/convert', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned HTTP ${response.status}`);
      }

      const data = await response.json();
      const primaryJobId = data.job_id;
      const fileNames = stagedFiles.map(f => f.name).join(', ');

      queueSection.style.display = 'block';
      createJobCard(primaryJobId, fileNames, targetExt);
      stagedFiles = [];
      renderStagedFiles();
      queueSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      alert(`Conversion request error: ${err.message}`);
    } finally {
      submitBtn.disabled = false;
      submitBtn.querySelector('span').textContent = 'Convert Documents';
    }
  });

  // 5. Job Tracking and Polling
  function createJobCard(jobId, displayName, targetExt) {
    const card = document.createElement('div');
    card.className = 'job-item glass-panel';
    card.id = `job-${jobId}`;
    card.innerHTML = `
      <div class="job-header">
        <div class="job-meta">
          <span class="job-name">${escapeHtml(displayName)}</span>
          <span class="badge queued" id="badge-${jobId}">Queued</span>
        </div>
        <span style="font-size: 12px; color: var(--text-muted);">&rarr; ${targetExt.toUpperCase()}</span>
      </div>
      <div class="progress-container">
        <div class="progress-bar" id="progress-${jobId}" style="width: 10%;"></div>
      </div>
      <div id="jobDetails-${jobId}" style="font-size: 13px; color: var(--text-muted);">
        Initializing conversion engine...
      </div>
      <div id="warningsContainer-${jobId}"></div>
      <div class="job-actions" id="actions-${jobId}" style="margin-top: 14px; display: none;"></div>
    `;

    jobsContainer.prepend(card);
    activeJobs.set(jobId, { status: 'queued', pollCount: 0 });
    updateQueueBadge();
    pollJob(jobId);
  }

  async function pollJob(jobId) {
    const badge = document.getElementById(`badge-${jobId}`);
    const progressBar = document.getElementById(`progress-${jobId}`);
    const details = document.getElementById(`jobDetails-${jobId}`);
    const warningsContainer = document.getElementById(`warningsContainer-${jobId}`);
    const actions = document.getElementById(`actions-${jobId}`);

    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      if (!res.ok) {
        throw new Error(`Job poll failed: ${res.statusText}`);
      }
      const data = await res.json();
      const status = data.status || 'queued';
      const progress = data.progress || 0;

      // Update badge
      badge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
      badge.className = `badge ${status}`;

      // Update progress bar
      progressBar.style.width = `${Math.max(progress, 15)}%`;

      if (status === 'finished') {
        progressBar.style.width = '100%';
        details.innerHTML = '<span style="color: var(--status-success);">&check; Conversion completed successfully.</span>';

        // Render warnings if any
        if (data.warnings && data.warnings.length > 0) {
          warningsContainer.innerHTML = data.warnings.map(w => 
            `<div class="job-warning"><strong>Notice:</strong> ${escapeHtml(w)}</div>`
          ).join('');
        }

        // Render download & chat action buttons
        actions.style.display = 'flex';
        const outputs = data.outputs || [];
        let buttonsHtml = '';

        if (outputs.length > 1) {
          buttonsHtml += `
            <a href="/api/download/${jobId}" class="btn-primary" style="padding: 8px 18px; font-size: 13px;" download>
              Download All as ZIP
            </a>
          `;
        }

        outputs.forEach(fname => {
          const cleanDisplayName = fname.includes('_') && fname.split('_')[0].length >= 32
            ? fname.split('_').slice(1).join('_')
            : fname;
          buttonsHtml += `
            <a href="/api/download/${fname}" class="btn-secondary" style="font-size: 13px;" download>
              Download ${escapeHtml(cleanDisplayName)}
            </a>
            <button type="button" class="btn-secondary summarize-btn" data-filename="${escapeHtml(fname)}" style="font-size: 13px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
              <span>Summarise in Chat</span>
            </button>
          `;
        });

        actions.innerHTML = buttonsHtml;

        // Hook up "Summarise in Chat" buttons to the chat assistant
        actions.querySelectorAll('.summarize-btn').forEach(btn => {
          btn.addEventListener('click', () => {
            const fname = btn.dataset.filename;
            if (window.DocChatAssistant) {
              window.DocChatAssistant.attachExistingFile(fname);
              document.getElementById('chatSection').scrollIntoView({ behavior: 'smooth' });
            }
          });
        });

        activeJobs.delete(jobId);
        updateQueueBadge();
        return;
      }

      if (status === 'failed') {
        progressBar.style.width = '100%';
        progressBar.style.background = 'var(--status-error)';
        details.innerHTML = `<div class="job-error"><strong>Error:</strong> ${escapeHtml(data.error || 'Conversion encountered an error.')}</div>`;
        if (data.warnings && data.warnings.length > 0) {
          warningsContainer.innerHTML = data.warnings.map(w => 
            `<div class="job-warning">${escapeHtml(w)}</div>`
          ).join('');
        }
        activeJobs.delete(jobId);
        updateQueueBadge();
        return;
      }

      if (status === 'started') {
        details.textContent = 'Processing document layout and converting formats...';
      }

      // Schedule next poll
      setTimeout(() => pollJob(jobId), 1200);
    } catch (e) {
      setTimeout(() => pollJob(jobId), 2000);
    }
  }

  function updateQueueBadge() {
    const count = activeJobs.size;
    queueCountBadge.textContent = `${count} Active`;
    queueCountBadge.className = `badge ${count > 0 ? 'started' : 'finished'}`;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Check system health on load
  fetch('/api/health')
    .then(r => r.json())
    .then(data => {
      const badge = document.getElementById('healthStatusText');
      if (data.status === 'ok') {
        badge.textContent = 'Engine Ready';
      }
    })
    .catch(() => {});
});

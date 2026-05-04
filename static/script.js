  const dropZone         = document.getElementById('dropZone');
  const fileInput        = document.getElementById('fileInput');
  const uploadingName    = document.getElementById('uploadingName');
  const uploadSuccess    = document.getElementById('uploadSuccess');
  const uploadSuccessName= document.getElementById('uploadSuccessName');
  const changeBtn        = document.getElementById('changeBtn');
  const genBtn           = document.getElementById('genBtn');
  const progressWrap     = document.getElementById('progressWrap');
  const statusDot        = document.getElementById('statusDot');
  const logs             = document.getElementById('logs');
  const downloadSection  = document.getElementById('downloadSection');
  const downloadSingle   = document.getElementById('downloadSingle');
  const downloadEmail    = document.getElementById('downloadEmail');
  const downloadBtnSingle  = document.getElementById('downloadBtnSingle');
  const downloadBtnDesktop = document.getElementById('downloadBtnDesktop');
  const downloadBtnMobile  = document.getElementById('downloadBtnMobile');

  let folderPath   = null;
  let packageType  = null;   // 'edetailer' | 'email'

  // ── Drag events ──
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('dragover'); handleFiles(e.dataTransfer.files); });
  fileInput.addEventListener('change', () => handleFiles(fileInput.files));
  changeBtn.addEventListener('click', resetToIdle);
  downloadBtnSingle.addEventListener('click', e => handleDesktopDownload(e, 'full'));
  downloadBtnDesktop.addEventListener('click', e => handleDesktopDownload(e, 'desktop'));
  downloadBtnMobile.addEventListener('click', e => handleDesktopDownload(e, 'mobile'));

  function resetToIdle() {
    folderPath = null; packageType = null;
    fileInput.value = '';
    dropZone.classList.remove('uploading', 'uploaded');
    uploadSuccess.classList.remove('visible');
    genBtn.classList.remove('visible');
    downloadSection.classList.remove('visible');
    downloadSingle.style.display = 'none';
    downloadEmail.style.display  = 'none';
    logs.innerHTML = '<span class="empty-state">Awaiting input...</span>';
    statusDot.className = 'status-dot';
  }

  function handleFiles(files) {
    const zip = Array.from(files).find(f => f.name.endsWith('.zip'));
    if (!zip) { alert('Please provide a .zip archive of your folder.'); return; }
    uploadFile(zip);
  }

  async function uploadFile(zip) {
    uploadingName.textContent = zip.name + ' (' + (zip.size / 1024).toFixed(1) + ' KB)';
    dropZone.classList.add('uploading');
    uploadSuccess.classList.remove('visible');
    genBtn.classList.remove('visible');
    downloadSection.classList.remove('visible');
    logs.innerHTML = '<span class="empty-state">Awaiting input...</span>';

    const formData = new FormData();
    formData.append('folder_zip', zip);

    let res, json;
    try {
      res  = await fetch('/upload', { method: 'POST', body: formData });
      if (!res.ok) throw new Error(res.statusText);
      json = await res.json();
      if (json.error) throw new Error(json.error);
    } catch (err) {
      dropZone.classList.remove('uploading');
      alert('❌ Upload failed: ' + err.message);
      return;
    }

    folderPath  = json.folder_path;
    packageType = json.package_type;   // 'edetailer' or 'email'

    dropZone.classList.remove('uploading');
    dropZone.classList.add('uploaded');
    uploadSuccessName.textContent = zip.name + ' (' + (zip.size / 1024).toFixed(1) + ' KB)';
    uploadSuccess.classList.add('visible');
    genBtn.classList.add('visible');
  }

  function startGeneration() {
    if (!folderPath) return;

    logs.innerHTML = '';
    downloadSection.classList.remove('visible');
    downloadSingle.style.display = 'none';
    downloadEmail.style.display  = 'none';
    statusDot.className = 'status-dot active';
    genBtn.disabled = true;
    genBtn.classList.add('running');
    progressWrap.classList.add('visible');

    const es = new EventSource('/generate?folder=' + encodeURIComponent(folderPath));

    es.onmessage = function(e) {
      const d = e.data;
      if (d.includes('❌') || d.includes('ERROR')) {
        logLine(d); es.close(); finishUI('error'); return;
      }
      if (d.trim() === 'DONE') {
        logLine('🎉 Completed!', 'log-success');
        es.close();
        finishUI('done');
        showDownload();
        return;
      }
      logLine(d, (d.startsWith('✅') || d.startsWith('🎉')) ? 'log-success' : '');
    };
    es.onerror = function() { logLine('❌ Connection lost.'); es.close(); finishUI('error'); };
  }

  function showDownload() {
    const base = '/download?folder=' + encodeURIComponent(folderPath);

    if (packageType === 'email') {
      downloadBtnDesktop.href = base + '&view=desktop';
      downloadBtnMobile.href  = base + '&view=mobile';
      downloadEmail.style.display = 'block';
    } else {
      // eDetailer or anything else → single merged PDF
      downloadBtnSingle.href = base + '&view=full';
      downloadSingle.style.display = 'flex';
    }

    downloadSection.classList.add('visible');
  }

  async function handleDesktopDownload(event, view) {
    if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.save_pdf) {
      return;
    }

    event.preventDefault();

    if (!folderPath) {
      alert('Please generate a PDF first.');
      return;
    }

    try {
      const result = await window.pywebview.api.save_pdf(folderPath, view);
      if (result && result.cancelled) return;

      if (!result || !result.ok) {
        throw new Error((result && result.error) || 'Unable to save PDF.');
      }

      logLine('Saved PDF to ' + result.path, 'log-success');
    } catch (err) {
      alert('Download failed: ' + err.message);
    }
  }

  function logLine(msg, cls) {
    const span = document.createElement('span');
    span.className = 'log-line' + (cls ? ' ' + cls : '');
    span.textContent = msg;
    logs.appendChild(span);
    logs.appendChild(document.createElement('br'));
    logs.scrollTop = logs.scrollHeight;
  }

  function finishUI(state) {
    genBtn.disabled = false;
    genBtn.classList.remove('running');
    progressWrap.classList.remove('visible');
    statusDot.className = 'status-dot ' + (state === 'done' ? 'done' : 'error');
  }

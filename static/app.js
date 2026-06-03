/* ── Helpers ───────────────────────────────────────────────────────────── */
function showResult(id, data, ok = true) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = 'result-box ' + (ok ? 'ok' : 'error');
  el.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
}

function showInfo(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = 'result-box info';
  el.textContent = msg;
}

async function post(endpoint, body) {
  const resp = await fetch('/api/' + endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return resp.json();
}

async function pollJob(jobId, resultId, btnId, onDone) {
  const btn = document.getElementById(btnId);
  while (true) {
    await new Promise(r => setTimeout(r, 1200));
    const data = await fetch('/api/jobs/' + jobId).then(r => r.json());
    if (data.status === 'done') {
      if (btn) btn.disabled = false;
      showResult(resultId, data.result, true);
      if (onDone) onDone(data.result);
      return data.result;
    }
    if (data.status === 'error') {
      if (btn) btn.disabled = false;
      showResult(resultId, data.error || 'Unknown error', false);
      return;
    }
    showInfo(resultId, `Running… (job ${jobId})`);
  }
}

function csvToList(str) {
  return str.split(',').map(s => s.trim()).filter(Boolean);
}

function splitDoiInputs(str) {
  return str.split(/[\n,]+/).map(s => s.trim()).filter(Boolean);
}

const OVERLEAF_PROJECTS_URL = 'https://www.overleaf.com/project';
let createdProjectZipPath = '';

/* ── Open-folder buttons ───────────────────────────────────────────────── */
const PATH_BUTTONS = {
  'create-dir': { action: 'select', mode: 'folder', title: 'Select project folder' },
  'mod-folder': { action: 'select', mode: 'folder', title: 'Select project folder' },
  'mod-file': { action: 'select', mode: 'file', fileKind: 'tex', base: 'mod-folder', title: 'Select main .tex file' },
  'os-dir': { action: 'select', mode: 'folder', title: 'Select folder containing .tex files' },
  'os-outdir': { action: 'open' },
  're-folder': { action: 'select', mode: 'folder', title: 'Select project folder' },
  're-file': { action: 'select', mode: 'file', fileKind: 'tex', base: 're-folder', title: 'Select main .tex file' },
  'clean-file': { action: 'select', mode: 'file', fileKind: 'tex', title: 'Select LaTeX file' },
  'fl-folder': { action: 'select', mode: 'folder', title: 'Select project folder' },
  'fl-file': { action: 'select', mode: 'file', fileKind: 'tex', base: 'fl-folder', title: 'Select .tex file' },
  'fig-folder': { action: 'select', mode: 'folder', title: 'Select project folder' },
  'fig-file': { action: 'select', mode: 'file', fileKind: 'tex', base: 'fig-folder', title: 'Select .tex file' },
  'bea-folder': { action: 'select', mode: 'folder', title: 'Select project folder' },
  'bea-file': { action: 'select', mode: 'file', fileKind: 'tex', base: 'bea-folder', title: 'Select .tex file' },
  'rv-output': { action: 'open' },
  'ld-old': { action: 'select', mode: 'file-or-folder', fileKind: 'zip', title: 'Select old project folder or zip' },
  'ld-new': { action: 'select', mode: 'file-or-folder', fileKind: 'zip', title: 'Select new project folder or zip' },
  'ld-main': { action: 'select', mode: 'file', fileKind: 'tex', base: 'ld-new', title: 'Select main .tex file in new project' },
  'ld-workspace': { action: 'open' },
  'doi-output': { action: 'select', mode: 'file', fileKind: 'bib', title: 'Select reference .bib file' },
  'doi-html-files': { action: 'select', mode: 'file', fileKind: 'html', title: 'Select saved article HTML file', appendSelection: true },
  'cs-file': { action: 'select', mode: 'file', fileKind: 'tex', title: 'Select main .tex file' },
  'cs-out': { action: 'open' },
  'cs-miktex': { action: 'select', mode: 'folder', title: 'Select TeX latex folder' },
  'sd-outfolder': { action: 'open' },
};

function isAbsolutePath(v) {
  return /^([a-zA-Z]:[\\/]|[\\/]|~([\\/]|$))/.test(v);
}

async function openPath(id, base) {
  let val = resolvedFieldPath(id, base);
  if (!val && base) val = (document.getElementById(base).value || '').trim();
  if (!val) { alert('Enter a path first.'); return; }
  const data = await post('open-folder', { path: val });
  if (data.status !== 'ok') alert(data.error || 'Could not open folder.');
}

function resolvedFieldPath(id, base) {
  let val = (document.getElementById(id).value || '').trim();
  if (val && base && !isAbsolutePath(val)) {
    const b = (document.getElementById(base).value || '').trim();
    if (b) val = b.replace(/[\\/]+$/, '') + '/' + val;
  }
  return val;
}

function splitPath(path) {
  const parts = path.split(/[\\/]+/);
  const name = parts.pop() || '';
  const dir = path.slice(0, path.length - name.length).replace(/[\\/]+$/, '');
  return { dir, name };
}

async function selectPath(id, config) {
  const input = document.getElementById(id);
  const base = config.base || null;
  const baseInput = base ? document.getElementById(base) : null;
  const initialPath = resolvedFieldPath(id, base) || (baseInput ? baseInput.value.trim() : '');
  const data = await post('select-path', {
    mode: config.mode || 'file',
    title: config.title || 'Select path',
    initial_path: initialPath,
    file_kind: config.fileKind || '',
  });
  if (data.status !== 'ok') {
    alert(data.error || 'Could not select path.');
    return;
  }
  if (!data.path) return;

  if (config.appendSelection) {
    const lines = input.value.split('\n').map(s => s.trim()).filter(Boolean);
    if (!lines.some(line => line.toLowerCase() === data.path.toLowerCase())) {
      lines.push(data.path);
    }
    input.value = lines.join('\n');
    return;
  }

  if (baseInput && config.mode === 'file') {
    const selected = splitPath(data.path);
    baseInput.value = selected.dir;
    input.value = selected.name;
  } else {
    input.value = data.path;
  }
}

function updateOverleafHelper(zipPath) {
  const helper = document.getElementById('create-overleaf');
  const pathEl = document.getElementById('create-zip-path');
  const openBtn = document.getElementById('create-open-zip');
  const copyBtn = document.getElementById('create-copy-zip');
  createdProjectZipPath = zipPath || '';
  if (!helper || !pathEl) return;
  pathEl.textContent = createdProjectZipPath || 'No ZIP generated yet.';
  if (openBtn) openBtn.disabled = !createdProjectZipPath;
  if (copyBtn) copyBtn.disabled = !createdProjectZipPath;
  helper.hidden = false;
}

async function openCreatedZipFolder() {
  if (!createdProjectZipPath) {
    alert('Create a project with the zip option enabled first.');
    return;
  }
  const data = await post('open-folder', { path: createdProjectZipPath });
  if (data.status !== 'ok') alert(data.error || 'Could not open ZIP folder.');
}

async function copyCreatedZipPath() {
  if (!createdProjectZipPath) {
    alert('Create a project with the zip option enabled first.');
    return;
  }
  try {
    await navigator.clipboard.writeText(createdProjectZipPath);
    alert('ZIP path copied.');
  } catch (e) {
    window.prompt('Copy this ZIP path:', createdProjectZipPath);
  }
}

function openOverleafProjects() {
  window.open(OVERLEAF_PROJECTS_URL, '_blank', 'noopener,noreferrer');
}

function initPathButtons() {
  for (const [id, config] of Object.entries(PATH_BUTTONS)) {
    const input = document.getElementById(id);
    if (!input || input.dataset.hasOpenBtn) continue;
    input.dataset.hasOpenBtn = '1';
    const wrap = document.createElement('div');
    wrap.className = 'input-with-btn';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-open';
    if (config.action === 'select') {
      btn.title = config.title || 'Select path';
      btn.textContent = '...';
      btn.addEventListener('click', () => selectPath(id, config));
    } else {
      btn.title = 'Open this location in your file explorer';
      btn.textContent = '\uD83D\uDCC2';
      btn.addEventListener('click', () => openPath(id, config.base || null));
    }
    wrap.appendChild(btn);
  }
}

/* ── Step 1: Create Project ────────────────────────────────────────────── */
async function runCreateProject() {
  const btn = event.target;
  btn.disabled = true;
  const body = {
    project_dir: document.getElementById('create-dir').value.trim(),
    sections:    csvToList(document.getElementById('create-sections').value),
    appendices:  csvToList(document.getElementById('create-appendices').value),
    zip_result:  document.getElementById('create-zip').checked,
  };
  const data = await post('project/create', body);
  btn.disabled = false;
  if (data.status === 'ok') {
    updateOverleafHelper(data.zip_path);
    showResult('create-result', data, true);
  } else {
    updateOverleafHelper('');
    showResult('create-result', data.error, false);
  }
}

/* ── Modularize ────────────────────────────────────────────────────────── */
async function runModularize() {
  const btn = event.target; btn.disabled = true;
  const data = await post('modularize', {
    input_folder: document.getElementById('mod-folder').value.trim(),
    source_file:  document.getElementById('mod-file').value.trim(),
  });
  btn.disabled = false;
  data.status === 'ok' ? showResult('mod-result', data, true) : showResult('mod-result', data.error, false);
}

/* ── One Sentence ──────────────────────────────────────────────────────── */
async function runOneSentence() {
  const btn = event.target; btn.disabled = true;
  const data = await post('one-sentence', {
    root_dir:   document.getElementById('os-dir').value.trim(),
    output_dir: document.getElementById('os-outdir').value.trim(),
  });
  btn.disabled = false;
  data.status === 'ok' ? showResult('os-result', data, true) : showResult('os-result', data.error, false);
}

/* ── Step 2: Reassemble ────────────────────────────────────────────────── */
async function runReassemble() {
  const btn = event.target; btn.disabled = true;
  const data = await post('reassemble', {
    input_folder: document.getElementById('re-folder').value.trim(),
    filename:     document.getElementById('re-file').value.trim(),
  });
  btn.disabled = false;
  data.status === 'ok' ? showResult('re-result', data, true) : showResult('re-result', data.error, false);
}

/* ── Step 3: Clean ─────────────────────────────────────────────────────── */
async function runClean() {
  const btn = event.target; btn.disabled = true;
  const data = await post('clean', {
    latex_file: document.getElementById('clean-file').value.trim(),
    keep_bib:   document.getElementById('clean-keepbib').checked,
  });
  btn.disabled = false;
  data.status === 'ok' ? showResult('clean-result', data, true) : showResult('clean-result', data.error, false);
}

/* ── Step 4: Review Floats ─────────────────────────────────────────────── */
async function runReviewFloats() {
  const btn = event.target; btn.disabled = true;
  const data = await post('review-floats', {
    input_folder:    document.getElementById('fl-folder').value.trim(),
    input_filename:  document.getElementById('fl-file').value.trim(),
    environments:    csvToList(document.getElementById('fl-envs').value),
  });
  btn.disabled = false;
  data.status === 'ok' ? showResult('fl-result', data, true) : showResult('fl-result', data.error, false);
}

/* ── Step 5: Collect Figures ───────────────────────────────────────────── */
async function runCollectFigures() {
  const btn = event.target; btn.disabled = true;
  const data = await post('collect-figures', {
    input_folder: document.getElementById('fig-folder').value.trim(),
    source_file:  document.getElementById('fig-file').value.trim(),
  });
  btn.disabled = false;
  data.status === 'ok' ? showResult('fig-result', data, true) : showResult('fig-result', data.error, false);
}

/* ── Step 6: Beautify ──────────────────────────────────────────────────── */
async function runBeautify() {
  const btn = event.target; btn.disabled = true;
  const data = await post('beautify', {
    root_dir:       document.getElementById('bea-folder').value.trim(),
    input_file:     document.getElementById('bea-file').value.trim(),
    comment_column: parseInt(document.getElementById('bea-col').value) || 0,
  });
  btn.disabled = false;
  data.status === 'ok' ? showResult('bea-result', data, true) : showResult('bea-result', data.error, false);
}

/* ── Step 7: Reviewer Template ─────────────────────────────────────────── */
async function runReviewerTemplate() {
  const btn = event.target; btn.disabled = true;
  let authors, affils, counts;
  try {
    authors = JSON.parse(document.getElementById('rv-authors').value);
    affils  = JSON.parse(document.getElementById('rv-affils').value);
    counts  = JSON.parse(document.getElementById('rv-counts').value);
  } catch (e) {
    btn.disabled = false;
    return showResult('rv-result', 'JSON parse error: ' + e.message, false);
  }
  const data = await post('reviewer-template', {
    manuscript_title:         document.getElementById('rv-title').value.trim(),
    journal_name:             document.getElementById('rv-journal').value.trim(),
    submission_id:            document.getElementById('rv-id').value.trim(),
    corresponding_author_email: document.getElementById('rv-email').value.trim(),
    authors,
    affiliations: affils,
    reviewer_comment_counts: counts,
    output_tex_file: document.getElementById('rv-output').value.trim(),
  });
  btn.disabled = false;
  data.status === 'ok' ? showResult('rv-result', data, true) : showResult('rv-result', data.error, false);
}

/* ── Step 8: LaTeX Diff ────────────────────────────────────────────────── */
async function runLatexdiff() {
  const btn = event.target; btn.disabled = true;
  const bibVal = document.getElementById('ld-bib').value;
  const engine = document.getElementById('ld-engine').value;
  const data = await post('latexdiff', {
    old_project:   document.getElementById('ld-old').value.trim(),
    new_project:   document.getElementById('ld-new').value.trim(),
    main_tex:      document.getElementById('ld-main').value.trim(),
    bib:           bibVal,
    latexdiff_engine: engine,
    use_docker:    engine === 'docker',
    confirm_online_upload: document.getElementById('ld-online-confirm').checked,
    online_latexdiff_url: document.getElementById('ld-online-url').value.trim(),
    workspace_dir: document.getElementById('ld-workspace').value.trim(),
  });
  if (data.status === 'running') {
    showInfo('ld-result', `Job started (${data.job_id}). Compiling…`);
    pollJob(data.job_id, 'ld-result', null).then(() => { btn.disabled = false; });
  } else {
    btn.disabled = false;
    showResult('ld-result', data.error || data, false);
  }
}

/* ── DOI → BibTeX ──────────────────────────────────────────────────────── */
async function runDoi2Bib() {
  const btn = event.target; btn.disabled = true;
  updateBibtexPreview('');
  const dois = splitDoiInputs(document.getElementById('doi-list').value);
  const savedHtmlFiles = document.getElementById('doi-html-files').value
    .split('\n').map(s => s.trim()).filter(Boolean);
  const data = await post('doi2bib', {
    dois,
    saved_html_files: savedHtmlFiles,
    output_bib_file: document.getElementById('doi-output').value.trim(),
    contact_email:   document.getElementById('doi-email').value.trim(),
    append:          document.getElementById('doi-append').checked,
  });
  if (data.status === 'running') {
    showInfo('doi-result', `Job started (${data.job_id}). Fetching…`);
    pollJob(data.job_id, 'doi-result', null, (result) => {
      updateBibtexPreview(result && result.bibtex_text ? result.bibtex_text : '');
    }).then(() => { btn.disabled = false; });
  } else {
    btn.disabled = false;
    showResult('doi-result', data.error || data, false);
  }
}

/* ── Copy Style Files ──────────────────────────────────────────────────── */
function updateBibtexPreview(text) {
  const preview = document.getElementById('doi-preview');
  if (preview) preview.value = text || '';
}

async function runCopyStyles() {
  const btn = event.target; btn.disabled = true;
  const data = await post('copy-styles', {
    latex_file:    document.getElementById('cs-file').value.trim(),
    output_folder: document.getElementById('cs-out').value.trim(),
    miktex_path:   document.getElementById('cs-miktex').value.trim(),
  });
  btn.disabled = false;
  data.status === 'ok' ? showResult('cs-result', data, true) : showResult('cs-result', data.error, false);
}

/* ── Step 9: Submission Docs ───────────────────────────────────────────── */
async function runSubmissionDocs() {
  const btn = event.target; btn.disabled = true;
  let config;
  try {
    config = JSON.parse(document.getElementById('sd-config').value);
  } catch (e) {
    btn.disabled = false;
    return showResult('sd-result', 'JSON parse error: ' + e.message, false);
  }
  const data = await post('submission-docs', {
    config,
    output_folder: document.getElementById('sd-outfolder').value.trim(),
  });
  btn.disabled = false;
  data.status === 'ok' ? showResult('sd-result', data, true) : showResult('sd-result', data.error, false);
}

/* ── Active nav highlight on scroll ────────────────────────────────────── */
function updateActiveNav() {
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-item');
  let current = '';
  sections.forEach(sec => {
    if (sec.getBoundingClientRect().top <= 80) current = sec.id;
  });
  navLinks.forEach(a => {
    a.classList.toggle('active', a.getAttribute('href') === '#' + current);
  });
}

document.addEventListener('scroll', updateActiveNav, { passive: true });

/* ── Init ───────────────────────────────────────────────────────────────── */
initPathButtons();
updateOverleafHelper('');
updateActiveNav();

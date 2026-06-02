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

async function pollJob(jobId, resultId, btnId) {
  const btn = document.getElementById(btnId);
  while (true) {
    await new Promise(r => setTimeout(r, 1200));
    const data = await fetch('/api/jobs/' + jobId).then(r => r.json());
    if (data.status === 'done') {
      if (btn) btn.disabled = false;
      showResult(resultId, data.result, true);
      return;
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

/* ── Open-folder buttons ───────────────────────────────────────────────── */
/* id -> base folder field to join with when the value is a bare filename */
const PATH_FIELDS = {
  'create-dir': null,
  'mod-folder': null, 'mod-file': 'mod-folder',
  'os-dir': null, 'os-outdir': null,
  're-folder': null, 're-file': 're-folder',
  'clean-file': null,
  'fl-folder': null, 'fl-file': 'fl-folder',
  'fig-folder': null, 'fig-file': 'fig-folder',
  'bea-folder': null, 'bea-file': 'bea-folder',
  'rv-output': null,
  'ld-old': null, 'ld-new': null, 'ld-main': 'ld-new', 'ld-workspace': null,
  'doi-output': null,
  'cs-file': null, 'cs-out': null, 'cs-miktex': null,
  'sd-outfolder': null,
};

function isAbsolutePath(v) {
  return /^([a-zA-Z]:[\\/]|[\\/]|~([\\/]|$))/.test(v);
}

async function openPath(id, base) {
  let val = (document.getElementById(id).value || '').trim();
  if (val && base && !isAbsolutePath(val)) {
    const b = (document.getElementById(base).value || '').trim();
    if (b) val = b.replace(/[\\/]+$/, '') + '/' + val;
  }
  if (!val && base) val = (document.getElementById(base).value || '').trim();
  if (!val) { alert('Enter a path first.'); return; }
  const data = await post('open-folder', { path: val });
  if (data.status !== 'ok') alert(data.error || 'Could not open folder.');
}

function initPathButtons() {
  for (const [id, base] of Object.entries(PATH_FIELDS)) {
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
    btn.title = 'Open this location in your file explorer';
    btn.textContent = '\uD83D\uDCC2';
    btn.addEventListener('click', () => openPath(id, base));
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
    showResult('create-result', data, true);
  } else {
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
  const dois = document.getElementById('doi-list').value
    .split('\n').map(s => s.trim()).filter(Boolean);
  const data = await post('doi2bib', {
    dois,
    output_bib_file: document.getElementById('doi-output').value.trim(),
    contact_email:   document.getElementById('doi-email').value.trim(),
    append:          document.getElementById('doi-append').checked,
  });
  if (data.status === 'running') {
    showInfo('doi-result', `Job started (${data.job_id}). Fetching…`);
    pollJob(data.job_id, 'doi-result', null).then(() => { btn.disabled = false; });
  } else {
    btn.disabled = false;
    showResult('doi-result', data.error || data, false);
  }
}

/* ── Copy Style Files ──────────────────────────────────────────────────── */
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
updateActiveNav();

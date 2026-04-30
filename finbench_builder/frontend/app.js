const API = "http://localhost:5000/api";
let currentPage = 1;
let filters = { type: null, entity: null };
let currentArticleId = null;
let annotateSession = { count: 0 };
let currentChunk = null;
let lastLabeled = null;
let skippedIds = [];
let pendingAnswer = null; // selected pos/neg/neu in question form

// ── Navigation ─────────────────────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('[id^="page-"]').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  document.getElementById('page-' + name).classList.remove('hidden');
  document.getElementById('nav-' + name).classList.add('active');
  if (name === 'dashboard') loadStats();
  if (name === 'articles') loadArticles();
  if (name === 'annotate') {
    annotateSession.count = 0;
    skippedIds = [];
    lastLabeled = null;
    loadNextChunk();
  }
}

// ── Stats ──────────────────────────────────────────────────────────────────
async function loadStats() {
  const data = await apiFetch('/stats');
  document.getElementById('s-articles').textContent = data.total_articles;
  document.getElementById('s-chunks').textContent = data.total_chunks;
  document.getElementById('s-labeled').textContent = data.labeled_chunks;
  const pct = data.total_chunks > 0 ? Math.round(data.labeled_chunks / data.total_chunks * 100) : 0;
  document.getElementById('s-pct').textContent = pct + '%';

  const dist = data.label_distribution || {};
  const bar = document.getElementById('label-dist-bar');
  const total = Object.values(dist).reduce((a, b) => a + b, 0) || 1;
  bar.innerHTML = ['positive', 'negative', 'neutral'].map(l => {
    const n = dist[l] || 0;
    const pct = Math.round(n / total * 100);
    const colors = { positive: 'var(--pos)', negative: 'var(--neg)', neutral: 'var(--neu)' };
    return `<div style="flex:${pct || 1};background:${colors[l]};height:10px;border-radius:3px;opacity:.8" title="${l}: ${n}"></div>`;
  }).join('');
  document.getElementById('label-dist-text').innerHTML = ['positive', 'negative', 'neutral'].map(l => {
    const n = dist[l] || 0;
    const colors = { positive: 'var(--pos)', negative: 'var(--neg)', neutral: 'var(--neu)' };
    return `<span style="font-size:12px;color:${colors[l]};margin-right:12px">${l}: ${n}</span>`;
  }).join('');

  const types = data.type_distribution || {};
  document.getElementById('type-dist-text').innerHTML = Object.entries(types).map(([k, v]) =>
    `<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border)">
      <span style="color:var(--muted)">${k}</span><span>${v}</span></div>`
  ).join('') || '<span style="color:var(--muted)">No data yet</span>';
}

// ── Articles ───────────────────────────────────────────────────────────────
async function loadArticles(page = 1) {
  currentPage = page;
  const params = new URLSearchParams({ page, per_page: 20 });
  if (filters.type) params.set('type', filters.type);
  if (filters.entity) params.set('entity_type', filters.entity);
  const data = await apiFetch('/articles?' + params);
  renderArticles(data);
}

function renderArticles(data) {
  const tbody = document.getElementById('articles-tbody');
  if (!data.articles.length) {
    tbody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><p>No articles yet. Use "Fetch News Feeds" on the dashboard.</p></div></td></tr>';
    return;
  }
  tbody.innerHTML = data.articles.map(a => `
    <tr>
      <td class="td-title"><a onclick="openArticle(${a.id})">${escHtml(a.title)}</a></td>
      <td style="color:var(--muted);font-size:12px">${escHtml(a.source || '')}</td>
      <td><span class="tag tag-${a.article_type}">${a.article_type}</span></td>
      <td><span class="tag tag-${a.entity_type}">${a.entity_type}</span></td>
      <td>${a.chunk_count || 0}</td>
      <td>${a.labeled_count || 0} / ${a.chunk_count || 0}</td>
      <td style="color:var(--muted);font-size:12px">${fmtDate(a.published_at)}</td>
      <td><button class="btn btn-ghost btn-sm" onclick="openArticle(${a.id})">View</button></td>
    </tr>
  `).join('');
  renderPagination(data);
}

function renderPagination(data) {
  const el = document.getElementById('articles-pagination');
  if (data.pages <= 1) { el.innerHTML = ''; return; }
  let html = `<button onclick="loadArticles(${data.page - 1})" ${data.page === 1 ? 'disabled' : ''}>‹</button>`;
  for (let i = Math.max(1, data.page - 2); i <= Math.min(data.pages, data.page + 2); i++) {
    html += `<button class="${i === data.page ? 'active' : ''}" onclick="loadArticles(${i})">${i}</button>`;
  }
  html += `<button onclick="loadArticles(${data.page + 1})" ${data.page === data.pages ? 'disabled' : ''}>›</button>`;
  el.innerHTML = html;
}

function setFilter(group, value, el) {
  const groupAttr = group === 'entity' ? '[data-group="entity"]' : ':not([data-group])';
  document.querySelectorAll(`.filter-btn${groupAttr}`).forEach(b => b.classList.remove('active'));
  if (!el.dataset.group) {
    document.querySelectorAll('.filter-btn:not([data-group])').forEach(b => b.classList.remove('active'));
    filters.type = value;
  } else {
    filters.entity = value;
  }
  el.classList.add('active');
  loadArticles(1);
}

// ── Article Modal ──────────────────────────────────────────────────────────
async function openArticle(id) {
  currentArticleId = id;
  document.getElementById('modal').classList.remove('hidden');
  document.getElementById('modal-body').innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner"></div></div>';
  const data = await apiFetch('/articles/' + id);
  document.getElementById('modal-title').textContent = data.title;
  renderChunks(data.chunks, data);
}

function renderChunks(chunks, article) {
  const meta = `
    <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
      <span class="tag tag-${article.article_type}">${article.article_type}</span>
      <span class="tag tag-${article.entity_type}">${article.entity_type}</span>
      ${article.entity ? `<span class="tag" style="background:var(--surface2);color:var(--muted)">${escHtml(article.entity)}</span>` : ''}
      <span class="text-muted">${article.source}</span>
    </div>
    <div style="font-size:12px;color:var(--muted);margin-bottom:16px">${chunks.length} chunks · ${chunks.filter(c => c.label).length} labeled</div>
  `;
  if (!chunks.length) {
    document.getElementById('modal-body').innerHTML = meta + '<p style="color:var(--muted);font-size:13px">No chunks yet. Article content may be too short or not yet fetched.</p>';
    return;
  }
  const cards = chunks.map(c => {
    const cls = c.label ? `labeled-${c.label}` : '';
    const labelBadge = c.label ? `<span class="tag label-${c.label}">${c.label}</span>` : '<span class="text-muted">unlabeled</span>';
    return `
      <div class="chunk-card ${cls}" id="chunk-${c.id}">
        <div class="chunk-header">
          <span class="chunk-num">Chunk ${c.chunk_index + 1} · ~${c.token_count} tokens</span>
          ${labelBadge}
        </div>
        <div class="chunk-text">${escHtml(c.text)}</div>
        <div class="chunk-actions">
          <button class="btn btn-success btn-sm" onclick="labelChunk(${c.id},'positive')">Positive</button>
          <button class="btn btn-danger btn-sm" onclick="labelChunk(${c.id},'negative')">Negative</button>
          <button class="btn btn-warn btn-sm" onclick="labelChunk(${c.id},'neutral')">Neutral</button>
        </div>
      </div>
    `;
  }).join('');
  document.getElementById('modal-body').innerHTML = meta + cards;
}

async function labelChunk(chunkId, label) {
  await apiFetch(`/chunks/${chunkId}/label`, 'POST', { label });
  const card = document.getElementById('chunk-' + chunkId);
  card.className = `chunk-card labeled-${label}`;
  card.querySelector('.chunk-header').querySelector('span:last-child').outerHTML = `<span class="tag label-${label}">${label}</span>`;
  toast('Labeled as ' + label, 'success');
}

async function fetchFullContent() {
  const btn = document.getElementById('fetch-full-btn');
  btn.disabled = true;
  btn.textContent = 'Fetching...';
  const data = await apiFetch(`/articles/${currentArticleId}/fetch-content`, 'POST', {});
  btn.disabled = false;
  btn.textContent = 'Fetch Full Content';
  if (data.error) { toast(data.error, 'error'); return; }
  toast(`Fetched ${data.content_length} chars, ${data.chunks} chunks`, 'success');
  openArticle(currentArticleId);
}

async function rechunkModal() {
  const target = prompt('Target tokens per chunk (default 75):', '75');
  if (!target) return;
  const data = await apiFetch(`/articles/${currentArticleId}/chunk`, 'POST', { target_tokens: parseInt(target) });
  toast(`Re-chunked into ${data.count} chunks`, 'success');
  openArticle(currentArticleId);
}

function closeModal() {
  document.getElementById('modal').classList.add('hidden');
  currentArticleId = null;
}

// ── Annotate ───────────────────────────────────────────────────────────────
async function loadNextChunk() {
  const btn = document.getElementById('load-next-btn');
  btn.disabled = true;
  const type = document.getElementById('anno-type-filter').value;
  const entity = document.getElementById('anno-entity-filter').value;
  const params = new URLSearchParams();
  if (type) params.set('type', type);
  if (entity) params.set('entity_type', entity);
  if (skippedIds.length) params.set('exclude', skippedIds.join(','));
  const data = await apiFetch('/chunks/next-unlabeled?' + params);
  btn.disabled = false;
  if (data.done) {
    document.getElementById('anno-empty').classList.remove('hidden');
    document.getElementById('anno-workspace').classList.add('hidden');
    document.getElementById('anno-empty').innerHTML = `
      <div class="empty-state">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <p>All chunks labeled! You annotated ${annotateSession.count} in this session.</p>
      </div>`;
    currentChunk = null;
    return;
  }
  document.getElementById('anno-empty').classList.add('hidden');
  document.getElementById('anno-workspace').classList.remove('hidden');
  renderAnnotateChunk(data);
  loadPriceData(data.article_id);
  renderQuestionsList(data.questions || []);
  document.getElementById('q-input').value = '';
  document.getElementById('q-answer-custom').value = '';
  pendingAnswer = null;
  updateAnswerButtons();
  updateSessionInfo();
}

function updateSessionInfo() {
  const el = document.getElementById('anno-session-info');
  if (el) el.textContent = `Session: ${annotateSession.count} labeled`;
}

function renderAnnotateChunk(chunk) {
  currentChunk = chunk;
  const labelBadge = chunk.label
    ? `<span class="tag label-${chunk.label}">labeled: ${chunk.label}</span>`
    : '';
  document.getElementById('anno-content').innerHTML = `
    <div class="annotate-meta">
      <span class="tag tag-${chunk.article_type}">${chunk.article_type}</span>
      <span class="tag tag-${chunk.entity_type}">${chunk.entity_type}</span>
      ${chunk.entity ? `<span class="tag" style="background:var(--surface2);color:var(--muted)">${escHtml(chunk.entity)}</span>` : ''}
      <span class="text-muted">~${chunk.token_count} tokens</span>
      ${labelBadge}
    </div>
    <div class="annotate-text">${escHtml(chunk.text)}</div>
    <div style="font-size:12px;color:var(--muted);margin-bottom:14px">
      ${getAnnotationQuestion(chunk.entity_type, chunk.article_type)}
    </div>
    <div class="annotate-btns">
      <button class="btn btn-success" onclick="annotate(${chunk.id},'positive')">Positive</button>
      <button class="btn btn-danger" onclick="annotate(${chunk.id},'negative')">Negative</button>
      <button class="btn btn-warn" onclick="annotate(${chunk.id},'neutral')">Neutral</button>
    </div>
    <div class="annotate-source">${escHtml(chunk.source || '')} · ${escHtml(chunk.title || '')}</div>
  `;
}

function getAnnotationQuestion(entityType, articleType) {
  if (entityType === 'country') return "Does this text suggest growth, shrinkage, or status quo of the country's economy?";
  if (entityType === 'es') return "Does this text reflect good, bad, or neutral news about the company's environmental/social policies?";
  if (articleType === 'transcript') return 'Does this transcript excerpt indicate positive, negative, or neutral long-term investor confidence?';
  return 'Is this news likely to increase, decrease, or not change long-term investor confidence?';
}

async function annotate(chunkId, label) {
  await apiFetch(`/chunks/${chunkId}/label`, 'POST', { label });
  lastLabeled = { chunkId, chunkData: currentChunk, label };
  annotateSession.count++;
  toast('Labeled: ' + label, 'success');
  // Update label badge in-place; user keeps writing questions on this chunk
  if (currentChunk && currentChunk.id === chunkId) {
    currentChunk.label = label;
    renderAnnotateChunk(currentChunk);
  }
  updateSessionInfo();
}

async function undoLastLabel() {
  if (!lastLabeled) { toast('Nothing to undo', 'error'); return; }
  await apiFetch(`/chunks/${lastLabeled.chunkId}/label`, 'POST', { label: null });
  annotateSession.count = Math.max(0, annotateSession.count - 1);
  renderAnnotateChunk(lastLabeled.chunkData);
  toast(`Undone (was: ${lastLabeled.label}) — re-label now`, 'success');
  lastLabeled = null;
}

function skipChunk() {
  if (!currentChunk) return;
  skippedIds.push(currentChunk.id);
  toast('Skipped (this session only)');
  loadNextChunk();
}

// ── Upload ─────────────────────────────────────────────────────────────────
async function submitArticle() {
  const title = document.getElementById('up-title').value.trim();
  const content = document.getElementById('up-content').value.trim();
  if (!title || !content) { toast('Title and content are required', 'error'); return; }
  const data = await apiFetch('/articles', 'POST', {
    title,
    content,
    source: document.getElementById('up-source').value.trim(),
    url: document.getElementById('up-url').value.trim() || `manual-${Date.now()}`,
    article_type: document.getElementById('up-type').value,
    entity_type: document.getElementById('up-entity-type').value,
    entity: document.getElementById('up-entity').value.trim(),
  });
  if (data.id) {
    toast('Article added and chunked!', 'success');
    ['up-title', 'up-content', 'up-source', 'up-url', 'up-entity'].forEach(id => document.getElementById(id).value = '');
  } else {
    toast('Failed to add article', 'error');
  }
}

// ── Scrape ─────────────────────────────────────────────────────────────────
async function scrapeFeeds() {
  const btn = document.getElementById('scrape-btn');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Fetching...';
  const data = await apiFetch('/scrape', 'POST', {});
  btn.disabled = false;
  btn.innerHTML = `<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg> Fetch News Feeds`;
  toast(`Fetched ${data.fetched} articles, ${data.new} new`, 'success');
  loadStats();
}

// ── Export ─────────────────────────────────────────────────────────────────
async function exportData() {
  const fmt = document.getElementById('export-format').value;
  const labeled = document.getElementById('export-labeled').value;
  const mode = document.getElementById('export-mode').value;
  const url = `${API}/export?format=${fmt}&labeled_only=${labeled}&mode=${mode}`;
  const a = document.createElement('a');
  a.href = url;
  a.download = `benchmark_${mode}.${fmt === 'jsonl' ? 'jsonl' : 'json'}`;
  a.click();
}

async function previewExport() {
  const labeled = document.getElementById('export-labeled').value;
  const mode = document.getElementById('export-mode').value;
  const data = await apiFetch(`/export?labeled_only=${labeled}&mode=${mode}`);
  const preview = data.slice(0, 5);
  document.getElementById('export-preview').classList.remove('hidden');
  document.getElementById('export-preview-content').textContent =
    preview.length ? JSON.stringify(preview, null, 2) : '(no records yet)';
}

// ── Utils ──────────────────────────────────────────────────────────────────
async function apiFetch(path, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  try {
    const res = await fetch(API + path, opts);
    return res.json();
  } catch (e) {
    toast('API error: ' + e.message, 'error');
    return {};
  }
}

function escHtml(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function fmtDate(s) {
  if (!s) return '';
  try { return new Date(s).toLocaleDateString(); } catch { return s.slice(0, 10); }
}

let toastTimer;
function toast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'show ' + type;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = ''; }, 2800);
}

// ── Price card ─────────────────────────────────────────────────────────────
async function loadPriceData(articleId, force = false) {
  const card = document.getElementById('price-card');
  card.innerHTML = '<div class="price-loading"><div class="spinner"></div><div style="margin-top:8px">Loading price data...</div></div>';
  const data = await apiFetch(`/articles/${articleId}/price${force ? '?refresh=1' : ''}`);
  renderPriceCard(articleId, data);
}

function renderPriceCard(articleId, data) {
  const card = document.getElementById('price-card');
  const ticker = (currentChunk && currentChunk.entity) || '';

  if (!data.price) {
    card.innerHTML = `
      <h4>Stock Movement</h4>
      <div class="price-ticker">${ticker || 'No ticker set'}</div>
      <div class="price-empty">
        ${data.reason === 'no_ticker'
          ? 'No ticker assigned to this article.<br>Set one below to view price data.'
          : 'No price data available for this ticker / date.'}
      </div>
      <div class="price-ticker-edit">
        <input id="ticker-input" placeholder="e.g. AAPL" value="${escHtml(ticker)}">
        <button class="btn btn-secondary btn-sm" onclick="saveTicker(${articleId})">Save & Fetch</button>
      </div>
    `;
    return;
  }

  const p = data.price;
  const isUp = p.change_pct >= 0;
  const cls = isUp ? 'price-change-pos' : 'price-change-neg';
  const arrow = isUp ? '▲' : '▼';

  card.innerHTML = `
    <h4>Stock Movement <span class="${cls}" style="font-size:13px;margin-left:6px">${arrow} ${Math.abs(p.change_pct)}%</span></h4>
    <div class="price-ticker">${escHtml(p.ticker)} · published ${escHtml(p.publish_date)}</div>
    <div class="price-stats">
      <div class="price-stat"><div class="v">$${p.before_price}</div><div class="l">Before</div></div>
      <div class="price-stat"><div class="v">$${p.after_price}</div><div class="l">After (~7d)</div></div>
      <div class="price-stat"><div class="v ${cls}">${isUp ? '+' : ''}$${p.change}</div><div class="l">Change</div></div>
    </div>
    ${renderPriceChart(p)}
    <div class="price-ticker-edit">
      <input id="ticker-input" value="${escHtml(p.ticker)}">
      <button class="btn btn-secondary btn-sm" onclick="saveTicker(${articleId})">Update</button>
      <button class="btn btn-ghost btn-sm" onclick="loadPriceData(${articleId}, true)" title="Refresh from Yahoo">↻</button>
    </div>
  `;
}

function renderPriceChart(p) {
  const points = p.points || [];
  if (points.length < 2) return '';
  const w = 340, h = 140, pad = 8;
  const closes = points.map(pt => pt.close);
  const min = Math.min(...closes), max = Math.max(...closes);
  const range = max - min || 1;
  const stepX = (w - pad * 2) / (points.length - 1);

  const coords = points.map((pt, i) => {
    const x = pad + i * stepX;
    const y = h - pad - ((pt.close - min) / range) * (h - pad * 2);
    return [x, y, pt];
  });

  const linePath = coords.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const fillPath = `${linePath} L${coords[coords.length - 1][0].toFixed(1)},${h - pad} L${coords[0][0].toFixed(1)},${h - pad} Z`;

  const isUp = p.change_pct >= 0;
  const color = isUp ? 'var(--pos)' : 'var(--neg)';

  // Find publish-date marker
  let publishX = null;
  for (let i = 0; i < points.length; i++) {
    if (points[i].date <= p.publish_date) publishX = coords[i][0];
  }

  return `
    <svg class="price-chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
      <path class="price-chart-fill" d="${fillPath}" fill="${color}" />
      <path class="price-chart-line" d="${linePath}" stroke="${color}" />
      ${publishX !== null ? `<line class="price-chart-publish" x1="${publishX}" y1="${pad}" x2="${publishX}" y2="${h - pad}" stroke="var(--muted)" />` : ''}
      ${coords.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="2" fill="${color}" />`).join('')}
    </svg>
    <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-top:4px">
      <span>${points[0].date}</span>
      <span style="color:var(--accent)">| publish</span>
      <span>${points[points.length - 1].date}</span>
    </div>
  `;
}

async function saveTicker(articleId) {
  const ticker = (document.getElementById('ticker-input').value || '').trim().toUpperCase();
  if (!ticker) { toast('Enter a ticker', 'error'); return; }
  await apiFetch(`/articles/${articleId}/entity`, 'POST', { entity: ticker });
  if (currentChunk) currentChunk.entity = ticker;
  toast('Ticker saved, fetching price...', 'success');
  loadPriceData(articleId, true);
}

// ── Questions ──────────────────────────────────────────────────────────────
function renderQuestionsList(questions) {
  const list = document.getElementById('questions-list');
  if (!questions.length) {
    list.innerHTML = '<div class="questions-empty">No questions yet. Add one above.</div>';
    return;
  }
  list.innerHTML = questions.map(q => `
    <div class="question-item" id="question-${q.id}">
      <div class="qi-q">${escHtml(q.question)}</div>
      <div class="qi-meta">
        ${q.answer ? `<span class="qi-ans qi-ans-${q.answer}">${escHtml(q.answer)}</span>` : '<span class="text-muted">no answer</span>'}
        ${q.notes ? `<span style="color:var(--muted)">· ${escHtml(q.notes)}</span>` : ''}
        <button class="qi-delete" onclick="deleteQuestion(${q.id})" title="Delete">×</button>
      </div>
    </div>
  `).join('');
}

function setPendingAnswer(answer) {
  pendingAnswer = pendingAnswer === answer ? null : answer;
  document.getElementById('q-answer-custom').value = '';
  updateAnswerButtons();
}

function updateAnswerButtons() {
  document.querySelectorAll('.q-ans-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.answer === pendingAnswer);
  });
}

async function addQuestion() {
  if (!currentChunk) return;
  const question = document.getElementById('q-input').value.trim();
  if (!question) { toast('Write a question first', 'error'); return; }
  const customAns = document.getElementById('q-answer-custom').value.trim();
  const answer = customAns || pendingAnswer || null;
  const data = await apiFetch(`/chunks/${currentChunk.id}/questions`, 'POST', {
    question, answer
  });
  if (data.id) {
    toast('Question added', 'success');
    document.getElementById('q-input').value = '';
    document.getElementById('q-answer-custom').value = '';
    pendingAnswer = null;
    updateAnswerButtons();
    refreshQuestions();
  }
}

async function refreshQuestions() {
  if (!currentChunk) return;
  const questions = await apiFetch(`/chunks/${currentChunk.id}/questions`);
  renderQuestionsList(questions);
}

async function deleteQuestion(qid) {
  await apiFetch(`/questions/${qid}`, 'DELETE');
  toast('Deleted');
  refreshQuestions();
}

// Wire up answer buttons after DOM is ready
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.q-ans-btn');
  if (btn) {
    e.preventDefault();
    setPendingAnswer(btn.dataset.answer);
  }
});

// Keyboard shortcuts (only active on Annotate page)
document.addEventListener('keydown', (e) => {
  const annotatePage = document.getElementById('page-annotate');
  if (!annotatePage || annotatePage.classList.contains('hidden')) return;
  const tag = (document.activeElement && document.activeElement.tagName) || '';
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
  const k = e.key.toLowerCase();
  if (k === 'u') { e.preventDefault(); undoLastLabel(); return; }
  if (!currentChunk) return;
  if (k === '1') { e.preventDefault(); annotate(currentChunk.id, 'positive'); }
  else if (k === '2') { e.preventDefault(); annotate(currentChunk.id, 'negative'); }
  else if (k === '3') { e.preventDefault(); annotate(currentChunk.id, 'neutral'); }
  else if (k === 's') { e.preventDefault(); skipChunk(); }
});

// Init
loadStats();

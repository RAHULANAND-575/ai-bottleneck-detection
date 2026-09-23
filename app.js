'use strict';

const editor = document.getElementById('editor');
const output = document.getElementById('output');
const runStatus = document.getElementById('run-status');
const tabStrip = document.getElementById('tab-strip');
const treePanel = document.getElementById('file-tree-panel');
const contextMenu = document.getElementById('context-menu');
const menuPopover = document.getElementById('menu-popover');
const notebookDrawer = document.getElementById('notebook-drawer');
const notesContainer = document.getElementById('notes-container');
const liveBtn = document.getElementById('live-btn');
const appShell = document.getElementById('app-shell');

let fileTree = null;
let tabs = [];
let activeTabId = null;
let liveMode = true;
let currentRunId = null;
let runPollTimer = null;
let notebookState = { categories: [] };
let selectedCategory = null;
let expandAll = false;

const ROOT_TAB = {
  id: 'scratch',
  path: '',
  name: 'scratch.py',
  content: "# Python scratch pad\nprint('Start learning DSA!')\n",
  dirty: false,
};

tabs.push({ ...ROOT_TAB });
activeTabId = ROOT_TAB.id;

function setStatus(text, cls = '') {
  runStatus.textContent = text;
  runStatus.className = `run-status ${cls}`;
}

function getActiveTab() {
  return tabs.find((t) => t.id === activeTabId);
}

function renderTabs() {
  tabStrip.innerHTML = '';
  tabs.forEach((tab) => {
    const el = document.createElement('div');
    el.className = `tab ${tab.id === activeTabId ? 'active' : ''}`;
    el.innerHTML = `<span>🐍</span><span class="tab-name">${tab.name}${tab.dirty ? '*' : ''}</span>`;

    const close = document.createElement('button');
    close.className = 'tab-close';
    close.textContent = '×';
    close.addEventListener('click', (e) => {
      e.stopPropagation();
      closeTab(tab.id);
    });

    el.appendChild(close);
    el.addEventListener('click', () => switchTab(tab.id));
    tabStrip.appendChild(el);
  });
}

function switchTab(tabId) {
  const tab = tabs.find((t) => t.id === tabId);
  if (!tab) return;
  activeTabId = tabId;
  editor.value = tab.content;
  renderTabs();
  highlightTreeSelection();
}

function closeTab(tabId) {
  if (tabs.length === 1) return;
  tabs = tabs.filter((t) => t.id !== tabId);
  if (activeTabId === tabId) {
    activeTabId = tabs[0].id;
    editor.value = tabs[0].content;
  }
  renderTabs();
}

function upsertTab(path, content) {
  const existing = tabs.find((t) => t.path === path);
  const name = path.split('/').pop() || 'untitled.py';
  if (existing) {
    existing.content = content;
    existing.dirty = false;
    switchTab(existing.id);
    return;
  }
  const tab = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    path,
    name,
    content,
    dirty: false,
  };
  tabs.push(tab);
  switchTab(tab.id);
}

function updateActiveFromEditor() {
  const tab = getActiveTab();
  if (!tab) return;
  tab.content = editor.value;
  tab.dirty = true;
  renderTabs();
  if (!editor.value.trim()) {
    stopRun();
    output.textContent = '';
    setStatus('CLEARED', 'stopped');
  }
}

function toggleLiveMode() {
  liveMode = !liveMode;
  liveBtn.classList.toggle('active', liveMode);
  liveBtn.textContent = liveMode ? 'LIVE' : 'LIVE OFF';
}

async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await res.json();
  if (!res.ok || data.status !== 'ok') {
    throw new Error(data.message || `Request failed (${res.status})`);
  }
  return data.data;
}

function createTreeNode(node) {
  const wrapper = document.createElement('div');
  if (node.type === 'folder') {
    const folderBtn = document.createElement('button');
    folderBtn.className = 'tree-folder';
    folderBtn.textContent = `📁 ${node.name}`;
    wrapper.appendChild(folderBtn);

    const childrenWrap = document.createElement('div');
    childrenWrap.className = 'tree-children';
    (node.children || []).forEach((child) => childrenWrap.appendChild(createTreeNode(child)));
    wrapper.appendChild(childrenWrap);

    folderBtn.addEventListener('click', () => {
      childrenWrap.classList.toggle('hidden');
    });
    return wrapper;
  }

  const fileBtn = document.createElement('button');
  fileBtn.className = 'tree-file';
  fileBtn.dataset.path = node.path;
  fileBtn.textContent = `🐍 ${node.name}`;
  fileBtn.addEventListener('click', () => openFile(node.path));
  wrapper.appendChild(fileBtn);
  return wrapper;
}

function highlightTreeSelection() {
  const active = getActiveTab();
  const buttons = treePanel.querySelectorAll('.tree-file');
  buttons.forEach((btn) => {
    btn.classList.toggle('active', active && active.path && btn.dataset.path === active.path);
  });
}

async function loadTree() {
  const data = await api('/api/files/tree');
  fileTree = data;
  treePanel.innerHTML = '';
  treePanel.appendChild(createTreeNode(fileTree));
  highlightTreeSelection();
}

async function openFile(path) {
  if (!path.endsWith('.py')) return;
  const data = await api(`/api/files/read?path=${encodeURIComponent(path)}`);
  upsertTab(path, data.content);
}

async function saveActiveFile() {
  const tab = getActiveTab();
  if (!tab || !tab.path) return false;

  await api('/api/files/save', {
    method: 'POST',
    body: JSON.stringify({ path: tab.path, content: tab.content }),
  });

  tab.dirty = false;
  renderTabs();

  if (liveMode && tab.content.trim()) {
    runCode(tab.content);
  }
  return true;
}

async function runCode(codeToRun) {
  if (!codeToRun.trim()) {
    output.textContent = '';
    return;
  }
  clearRunPoll();
  const data = await api('/api/run', {
    method: 'POST',
    body: JSON.stringify({ code: codeToRun }),
  });
  currentRunId = data.run_id;
  output.textContent = '';
  setStatus('RUNNING', 'running');
  pollRun(data.run_id);
}

function clearRunPoll() {
  if (runPollTimer) {
    clearInterval(runPollTimer);
    runPollTimer = null;
  }
}

function pollRun(runId) {
  runPollTimer = setInterval(async () => {
    try {
      const data = await api(`/api/run/${runId}`);
      output.textContent = data.output || '';
      output.scrollTop = output.scrollHeight;
      if (data.status !== 'running') {
        clearRunPoll();
        setStatus(data.status.toUpperCase(), data.status === 'finished' ? '' : 'stopped');
      }
    } catch (err) {
      clearRunPoll();
      setStatus('ERROR', 'stopped');
    }
  }, 250);
}

async function stopRun() {
  try {
    await api('/api/stop', {
      method: 'POST',
      body: JSON.stringify({ run_id: currentRunId }),
    });
  } catch (err) {
    // no-op
  }
  clearRunPoll();
  setStatus('STOPPED', 'stopped');
}

function selectedPythonSnippet() {
  const start = editor.selectionStart;
  const end = editor.selectionEnd;
  if (start === end) return '';
  return editor.value.slice(start, end);
}

async function saveSelectionAsNote() {
  const snippet = selectedPythonSnippet();
  if (!snippet.trim()) {
    alert('Select Python code first.');
    return;
  }
  const category = prompt('Category name');
  if (!category) return;
  const title = prompt('Note title') || 'Untitled note';

  await api('/api/notebook/note', {
    method: 'POST',
    body: JSON.stringify({ category, title, code: snippet }),
  });
  await loadNotebook();
}

function renderNotebook() {
  notesContainer.innerHTML = '';
  notebookState.categories.forEach((category) => {
    const categoryEl = document.createElement('section');
    categoryEl.className = 'note-category';
    const shouldShow = expandAll || selectedCategory === category.name || (!selectedCategory && notebookState.categories[0]?.name === category.name);

    categoryEl.innerHTML = `
      <div class="category-head">
        <strong>${category.name}</strong>
        <span>${category.notes.length} notes</span>
      </div>
      <div class="category-notes ${shouldShow ? 'show' : ''}"></div>
    `;

    const notesWrap = categoryEl.querySelector('.category-notes');
    category.notes.forEach((note) => {
      const noteEl = document.createElement('article');
      noteEl.className = 'note-card';
      noteEl.innerHTML = `
        <div class="note-title">${note.title}</div>
        <div class="note-actions">
          <button data-op="run">Run</button>
          <button data-op="insert">Insert</button>
        </div>
      `;

      noteEl.querySelector('[data-op="run"]').addEventListener('click', async () => {
        await runCode(note.code || '');
        setTimeout(async () => {
          if (confirm('Save current output to this note?')) {
            await api('/api/notebook/save-output', {
              method: 'POST',
              body: JSON.stringify({ note_id: note.id, output: output.textContent }),
            });
            await loadNotebook();
          }
        }, 400);
      });

      noteEl.querySelector('[data-op="insert"]').addEventListener('click', () => {
        const tab = getActiveTab();
        editor.setRangeText(`${note.code}\n`, editor.selectionStart, editor.selectionEnd, 'end');
        updateActiveFromEditor();
        if (tab) tab.content = editor.value;
      });

      notesWrap.appendChild(noteEl);
      if (note.output) {
        const out = document.createElement('pre');
        out.style.color = '#87d7ff';
        out.style.fontSize = '12px';
        out.textContent = note.output;
        notesWrap.appendChild(out);
      }
    });

    categoryEl.querySelector('.category-head').addEventListener('click', () => {
      selectedCategory = category.name;
      renderNotebook();
    });

    notesContainer.appendChild(categoryEl);
  });
}

async function loadNotebook() {
  notebookState = await api('/api/notebook');
  renderNotebook();
}

function onEditorContextMenu(e) {
  e.preventDefault();
  contextMenu.style.left = `${e.clientX}px`;
  contextMenu.style.top = `${e.clientY}px`;
  contextMenu.classList.remove('hidden');
}

function hideContextMenu() {
  contextMenu.classList.add('hidden');
}

async function addCategory() {
  const name = prompt('New category name');
  if (!name) return;
  await api('/api/notebook/category', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
  await loadNotebook();
}

async function addNote() {
  const category = prompt('Category name');
  if (!category) return;
  const title = prompt('Note title') || 'Untitled note';
  const code = selectedPythonSnippet() || editor.value;
  await api('/api/notebook/note', {
    method: 'POST',
    body: JSON.stringify({ category, title, code }),
  });
  await loadNotebook();
}

async function init() {
  renderTabs();
  switchTab(activeTabId);
  liveBtn.classList.add('active');

  await Promise.all([loadTree(), loadNotebook()]);

  editor.addEventListener('input', updateActiveFromEditor);
  editor.addEventListener('contextmenu', onEditorContextMenu);

  document.getElementById('run-btn').addEventListener('click', () => runCode(editor.value));
  document.getElementById('stop-btn').addEventListener('click', stopRun);
  document.getElementById('save-btn').addEventListener('click', saveActiveFile);
  liveBtn.addEventListener('click', toggleLiveMode);

  document.getElementById('menu-btn').addEventListener('click', () => {
    menuPopover.classList.toggle('hidden');
  });

  document.getElementById('toggle-tree-btn').addEventListener('click', () => {
    treePanel.classList.toggle('hidden');
  });

  document.querySelectorAll('.bg-mode').forEach((btn) => {
    btn.addEventListener('click', () => {
      const mode = btn.dataset.bg;
      if (mode === 'solid') {
        document.body.style.backgroundImage = '';
      }
      if (mode === 'wallpaper') {
        const saved = localStorage.getItem('pyLiteWallpaper');
        if (saved) document.body.style.backgroundImage = `url('${saved}')`;
      }
    });
  });

  document.getElementById('wallpaper-input').addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const image = String(reader.result);
      localStorage.setItem('pyLiteWallpaper', image);
      document.body.style.backgroundImage = `url('${image}')`;
      document.body.style.backgroundSize = 'cover';
    };
    reader.readAsDataURL(file);
  });

  document.getElementById('notebook-btn').addEventListener('click', () => {
    notebookDrawer.classList.toggle('hidden');
  });

  document.getElementById('add-category-btn').addEventListener('click', addCategory);
  document.getElementById('add-note-btn').addEventListener('click', addNote);
  document.getElementById('expand-all').addEventListener('change', (e) => {
    expandAll = e.target.checked;
    renderNotebook();
  });

  contextMenu.addEventListener('click', async (e) => {
    const action = e.target.dataset.action;
    if (!action) return;
    hideContextMenu();

    if (action === 'run-selection') {
      const selected = selectedPythonSnippet();
      await runCode(selected || editor.value);
      return;
    }
    if (action === 'save-note') {
      await saveSelectionAsNote();
      return;
    }
    if (action === 'stop') {
      await stopRun();
      return;
    }
    if (action === 'toggle-live') {
      toggleLiveMode();
    }
  });

  document.addEventListener('click', (e) => {
    if (!contextMenu.contains(e.target)) hideContextMenu();
    if (!menuPopover.contains(e.target) && e.target.id !== 'menu-btn') menuPopover.classList.add('hidden');
  });

  window.addEventListener('keydown', async (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault();
      await saveActiveFile();
    }
  });

  const savedWallpaper = localStorage.getItem('pyLiteWallpaper');
  if (savedWallpaper) {
    document.body.style.backgroundImage = `url('${savedWallpaper}')`;
    document.body.style.backgroundSize = 'cover';
  }

  setStatus('IDLE');
}

init().catch((err) => {
  output.textContent = `Initialization error: ${err.message}`;
  setStatus('ERROR', 'stopped');
});

/**
 * app.js — Frontend logic for the AI Bottleneck Detection dashboard.
 *
 * • Polls /api/metrics every 2 s to update live gauges
 * • Polls /api/detect  every 5 s to update bottleneck panel
 * • Polls /api/recommend every 10 s to update recommendations
 * • Maintains a 30-sample rolling buffer for Chart.js trend chart
 * • Handles API errors gracefully with toast notifications
 * • "Run Analysis" button triggers all three fetches immediately
 */

'use strict';

// ── Constants ────────────────────────────────────────────────────────────────
const API_BASE       = '';            // same origin as Flask server
const METRICS_INTERVAL   = 2000;     // ms
const DETECT_INTERVAL    = 5000;     // ms
const RECOMMEND_INTERVAL = 10000;    // ms
const MAX_HISTORY        = 30;       // data points in trend chart

// ── State ────────────────────────────────────────────────────────────────────
const history = {
  labels:   [],
  cpu:      [],
  gpu:      [],
  memory:   [],
};

let trendChart   = null;
let isOnline     = false;
let toastTimer   = null;

// ── DOM references ───────────────────────────────────────────────────────────
const statusBadge      = document.getElementById('status-badge');
const cpuValue         = document.getElementById('cpu-value');
const cpuBar           = document.getElementById('cpu-bar');
const cpuMeta          = document.getElementById('cpu-meta');
const gpuValue         = document.getElementById('gpu-value');
const gpuBar           = document.getElementById('gpu-bar');
const gpuMeta          = document.getElementById('gpu-meta');
const memValue         = document.getElementById('mem-value');
const memBar           = document.getElementById('mem-bar');
const memMeta          = document.getElementById('mem-meta');
const pcieValue        = document.getElementById('pcie-value');
const pcieBar          = document.getElementById('pcie-bar');
const bottleneckList   = document.getElementById('bottleneck-list');
const bottleneckCount  = document.getElementById('bottleneck-count');
const recommendList    = document.getElementById('recommend-list');
const recommendCount   = document.getElementById('recommend-count');
const toast            = document.getElementById('toast');

// ── Utility helpers ──────────────────────────────────────────────────────────

/** Format a Unix timestamp as HH:MM:SS */
function fmtTime(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString();
}

/** Push a value onto a rolling history array (max length MAX_HISTORY) */
function pushHistory(arr, val) {
  arr.push(val);
  if (arr.length > MAX_HISTORY) arr.shift();
}

/** Show a brief toast notification */
function showToast(msg, type = 'info') {
  toast.textContent = msg;
  toast.className   = `toast ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.className = 'toast hidden'; }, 3500);
}

/** Set status badge to online / offline */
function setStatus(online) {
  if (online === isOnline) return;
  isOnline = online;
  statusBadge.className = `status-badge ${online ? 'status-online' : 'status-offline'}`;
  statusBadge.innerHTML = `<span class="status-dot"></span>${online ? 'Live' : 'Offline'}`;
}

// ── Chart.js setup ───────────────────────────────────────────────────────────
function initChart() {
  const ctx = document.getElementById('trend-chart').getContext('2d');
  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: history.labels,
      datasets: [
        {
          label: 'CPU %',
          data: history.cpu,
          borderColor: '#58a6ff',
          backgroundColor: 'rgba(88,166,255,.08)',
          tension: 0.35,
          fill: true,
          pointRadius: 2,
          borderWidth: 2,
        },
        {
          label: 'GPU %',
          data: history.gpu,
          borderColor: '#3fb950',
          backgroundColor: 'rgba(63,185,80,.08)',
          tension: 0.35,
          fill: true,
          pointRadius: 2,
          borderWidth: 2,
        },
        {
          label: 'RAM %',
          data: history.memory,
          borderColor: '#d29922',
          backgroundColor: 'rgba(210,153,34,.08)',
          tension: 0.35,
          fill: true,
          pointRadius: 2,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      scales: {
        x: {
          ticks: { color: '#8b949e', maxRotation: 0, maxTicksLimit: 8 },
          grid:  { color: '#21262d' },
        },
        y: {
          min: 0, max: 100,
          ticks: { color: '#8b949e', callback: v => v + '%' },
          grid:  { color: '#21262d' },
        },
      },
      plugins: {
        legend: {
          labels: { color: '#e6edf3', boxWidth: 12, padding: 16 },
        },
        tooltip: {
          backgroundColor: '#1c2230',
          titleColor: '#e6edf3',
          bodyColor: '#8b949e',
          borderColor: '#30363d',
          borderWidth: 1,
        },
      },
    },
  });
}

// ── API callers ──────────────────────────────────────────────────────────────

async function fetchMetrics() {
  try {
    const res  = await fetch(`${API_BASE}/api/metrics`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    if (json.status !== 'ok') throw new Error(json.message || 'Unknown error');

    setStatus(true);
    const d = json.data;

    // CPU
    const cpu = d.cpu_percent ?? 0;
    cpuValue.textContent = `${cpu}%`;
    cpuBar.style.width   = `${cpu}%`;
    cpuMeta.textContent  = `Cores: ${d.cpu_count ?? '--'}`;

    // GPU
    const gpu = d.gpu_load_percent ?? 0;
    gpuValue.textContent = `${gpu}%`;
    gpuBar.style.width   = `${gpu}%`;
    gpuMeta.textContent  = d.gpu_available
      ? `${d.gpu_name} · ${d.gpu_temperature ?? '--'}°C`
      : `Simulated · ${d.gpu_memory_percent ?? '--'}% VRAM`;

    // Memory
    const mem = d.memory_percent ?? 0;
    memValue.textContent = `${mem}%`;
    memBar.style.width   = `${mem}%`;
    memMeta.textContent  = `${d.memory_used_gb ?? '--'} / ${d.memory_total_gb ?? '--'} GB`;

    // PCIe
    const pcie = d.pcie_throughput_gbps ?? 0;
    pcieValue.textContent = `${pcie} GB/s`;
    pcieBar.style.width   = `${Math.min((pcie / 16) * 100, 100)}%`;

    // Update history
    const label = fmtTime(d.timestamp ?? Date.now() / 1000);
    pushHistory(history.labels, label);
    pushHistory(history.cpu,    cpu);
    pushHistory(history.gpu,    gpu);
    pushHistory(history.memory, mem);
    trendChart.update();

  } catch (err) {
    setStatus(false);
    console.error('Metrics fetch failed:', err);
  }
}

async function fetchDetect() {
  try {
    const res  = await fetch(`${API_BASE}/api/detect`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    if (json.status !== 'ok') throw new Error(json.message || 'Unknown error');

    const items = json.data ?? [];
    bottleneckCount.textContent = items.length;

    if (items.length === 0) {
      bottleneckList.innerHTML = '<p class="placeholder-text">No bottlenecks detected.</p>';
      return;
    }

    bottleneckList.innerHTML = items.map(b => {
      const sev = b.severity ?? 'low';
      const badgeClass = sev === 'none' ? 'badge-none' : `badge-${sev}`;
      return `
        <div class="bottleneck-card severity-${sev}">
          <div class="bottleneck-header">
            <span class="bottleneck-type">${escHtml(b.type ?? 'unknown')}</span>
            <span class="severity-badge ${badgeClass}">${sev}</span>
            <span class="bottleneck-confidence">Conf: ${((b.confidence ?? 0) * 100).toFixed(1)}%</span>
          </div>
          <div class="bottleneck-desc">${escHtml(b.description ?? '')}</div>
          <div class="bottleneck-ts">${b.timestamp ? fmtTime(b.timestamp) : ''}</div>
        </div>`;
    }).join('');

  } catch (err) {
    bottleneckList.innerHTML = `<p class="placeholder-text" style="color:#f85149">Error: ${escHtml(err.message)}</p>`;
    showToast('Failed to fetch bottleneck data', 'error');
    console.error('Detect fetch failed:', err);
  }
}

async function fetchRecommend() {
  try {
    const res  = await fetch(`${API_BASE}/api/recommend`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    if (json.status !== 'ok') throw new Error(json.message || 'Unknown error');

    const items = json.data ?? [];
    recommendCount.textContent = items.length;

    if (items.length === 0) {
      recommendList.innerHTML = '<p class="placeholder-text">No recommendations at this time.</p>';
      return;
    }

    recommendList.innerHTML = items.map(r => {
      const pri = r.priority ?? 'low';
      return `
        <div class="rec-item">
          <div class="rec-header">
            <span class="rec-strategy">${escHtml(r.strategy ?? '')}</span>
            <span class="priority-badge priority-${pri}">${pri}</span>
            <span class="impact-label">Impact: ${r.impact ?? '--'}</span>
          </div>
          <div class="rec-details">${escHtml(r.details ?? '')}</div>
        </div>`;
    }).join('');

  } catch (err) {
    recommendList.innerHTML = `<p class="placeholder-text" style="color:#f85149">Error: ${escHtml(err.message)}</p>`;
    showToast('Failed to fetch recommendations', 'error');
    console.error('Recommend fetch failed:', err);
  }
}

/** Simple HTML escaping to avoid XSS from API data */
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Manual analysis trigger ──────────────────────────────────────────────────

async function runAnalysis() {
  showToast('Running analysis…', 'info');
  await Promise.all([fetchMetrics(), fetchDetect(), fetchRecommend()]);
  showToast('Analysis complete ✓', 'success');
}

// ── Initialise & start polling ───────────────────────────────────────────────
initChart();

// Immediate first fetch
fetchMetrics();
fetchDetect();
fetchRecommend();

// Recurring polling
setInterval(fetchMetrics,   METRICS_INTERVAL);
setInterval(fetchDetect,    DETECT_INTERVAL);
setInterval(fetchRecommend, RECOMMEND_INTERVAL);

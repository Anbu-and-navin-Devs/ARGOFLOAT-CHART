/**
 * FloatChart - Ocean Intelligence
 * Modern Web Application
 */

// ========================================
// Configuration
// ========================================
const API_BASE = '';
const HISTORY_KEY = 'floatchat_history';
const MAX_HISTORY = 15;

// State
const state = {
    map: null,
    chart: null,
    markers: [],
    polylines: [],
    currentData: [],
    currentQueryType: null,
    history: [],
    isLoading: false,
    panelWidth: 380
};

// DOM Elements
const $ = (id) => document.getElementById(id);
const el = {
    // Main
    mainContent: $('mainContent'),
    mapContainer: $('mapContainer'),
    mapWrapper: $('mapWrapper'),
    mapInfoBadge: $('mapInfoBadge'),
    fullscreenMap: $('fullscreenMap'),
    openChatBtn: $('openChatBtn'),
    mapExplorerBtn: $('mapExplorerBtn'),
    
    // Results
    resultsPanel: $('resultsPanel'),
    summaryTabBtn: $('summaryTabBtn'),
    chartTabBtn: $('chartTabBtn'),
    tableTabBtn: $('tableTabBtn'),
    summaryTab: $('summaryTab'),
    chartTab: $('chartTab'),
    tableTab: $('tableTab'),
    summaryContent: $('summaryContent'),
    statsGrid: $('statsGrid'),
    sqlToggle: $('sqlToggle'),
    sqlCode: $('sqlCode'),
    chartContainer: $('chartContainer'),
    chartTypeSelect: $('chartTypeSelect'),
    chartXAxis: $('chartXAxis'),
    chartYAxis: $('chartYAxis'),
    dataChart: $('dataChart'),
    tableHead: $('tableHead'),
    tableBody: $('tableBody'),
    exportBtn: $('exportBtn'),
    closeResults: $('closeResults'),
    
    // Chat
    chatPanel: $('chatPanel'),
    resizeHandle: $('resizeHandle'),
    panelToggle: $('panelToggle'),
    chatMessages: $('chatMessages'),
    dataRangeInfo: $('dataRangeInfo'),
    historyToggle: $('historyToggle'),
    historyCount: $('historyCount'),
    historyList: $('historyList'),
    clearHistory: $('clearHistory'),
    queryInput: $('queryInput'),
    sendBtn: $('sendBtn'),
    statusIndicator: $('statusIndicator'),
    
    // Overlays
    loadingOverlay: $('loadingOverlay'),
    toastContainer: $('toastContainer')
};

// Map Explorer State
let mapExplorerActive = false;
// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initEventListeners();
    initResizable();
    loadHistory();
    checkStatus();
});

function initMap() {
    state.map = L.map(el.mapContainer, {
        center: [10, 75],
        zoom: 4,
        zoomControl: true,
        attributionControl: false
    });
    
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19
    }).addTo(state.map);
    
    // Add region boundary (Indian Ocean: lat -20 to 25, lon 50 to 100)
    const bounds = [[-20, 50], [25, 100]];
    L.rectangle(bounds, {
        color: '#3b82f6',
        weight: 1,
        fillOpacity: 0.05,
        dashArray: '5, 5'
    }).addTo(state.map);
    
    // Invalidate size after render
    setTimeout(() => state.map.invalidateSize(), 100);
}

function initEventListeners() {
    // Quick actions
    document.querySelectorAll('.quick-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.dataset.query;
            el.queryInput.value = query;
            sendQuery();
        });
    });
    
    // Send button
    el.sendBtn.addEventListener('click', sendQuery);
    
    // Enter to send
    el.queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendQuery();
        }
    });
    
    // Auto-resize textarea
    el.queryInput.addEventListener('input', () => {
        el.queryInput.style.height = 'auto';
        el.queryInput.style.height = Math.min(el.queryInput.scrollHeight, 120) + 'px';
    });
    
    // Panel toggle (collapse/expand chat)
    el.panelToggle.addEventListener('click', () => {
        const isCollapsed = el.chatPanel.classList.toggle('collapsed');
        el.panelToggle.classList.toggle('rotated');
        el.openChatBtn.classList.toggle('hidden', !isCollapsed);
        // Resize map when panel collapses/expands
        setTimeout(() => state.map.invalidateSize(), 350);
    });
    
    // Open chat button (floating)
    el.openChatBtn.addEventListener('click', () => {
        el.chatPanel.classList.remove('collapsed');
        el.panelToggle.classList.remove('rotated');
        el.openChatBtn.classList.add('hidden');
        setTimeout(() => state.map.invalidateSize(), 350);
    });
    
    // Tab switching
    [el.summaryTabBtn, el.chartTabBtn, el.tableTabBtn].forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
    
    // Close results
    el.closeResults.addEventListener('click', () => {
        el.resultsPanel.classList.add('hidden');
    });
    
    // SQL toggle
    el.sqlToggle.addEventListener('click', () => {
        el.sqlToggle.classList.toggle('open');
        el.sqlCode.classList.toggle('hidden');
    });
    
    // Export
    el.exportBtn.addEventListener('click', exportData);
    
    // Fullscreen map
    el.fullscreenMap.addEventListener('click', toggleFullscreen);
    
    // History toggle
    el.historyToggle.addEventListener('click', () => {
        el.historyList.classList.toggle('hidden');
        el.clearHistory.classList.toggle('hidden');
    });
    
    // Clear history
    el.clearHistory.addEventListener('click', clearHistory);
    
    // Map Explorer toggle
    el.mapExplorerBtn.addEventListener('click', toggleMapExplorer);
    
    // Chart type and axis changes
    el.chartTypeSelect.addEventListener('change', () => updateChart(state.currentData, state.currentQueryType));
    el.chartXAxis.addEventListener('change', () => updateChart(state.currentData, state.currentQueryType));
    el.chartYAxis.addEventListener('change', () => updateChart(state.currentData, state.currentQueryType));
}

function initResizable() {
    let isResizing = false;
    let startX, startWidth;
    
    el.resizeHandle.addEventListener('mousedown', (e) => {
        isResizing = true;
        startX = e.clientX;
        startWidth = el.chatPanel.offsetWidth;
        el.resizeHandle.classList.add('dragging');
        document.body.style.cursor = 'ew-resize';
        document.body.style.userSelect = 'none';
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        const diff = startX - e.clientX;
        const newWidth = Math.min(Math.max(startWidth + diff, 320), 500);
        el.chatPanel.style.width = newWidth + 'px';
        state.panelWidth = newWidth;
    });
    
    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            el.resizeHandle.classList.remove('dragging');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            state.map.invalidateSize();
        }
    });
}

// ========================================
// API Functions
// ========================================
async function checkStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/status`);
        const data = await res.json();
        
        const dot = el.statusIndicator.querySelector('.status-dot');
        const text = el.statusIndicator.querySelector('.status-text');
        
        if (data.status === 'online' && data.database === 'connected') {
            dot.classList.add('online');
            text.textContent = 'Connected';
            
            // Show data range consistently
            if (data.data_range) {
                const start = data.data_range.start;
                const end = data.data_range.end;
                const records = data.records ? data.records.toLocaleString() : '0';
                el.dataRangeInfo.innerHTML = `
                    <div class="data-range-main">📅 ${start} to ${end} • ${records} records</div>
                    <div class="data-range-note">💡 For more data, use the local version</div>
                `;
            }
        } else {
            dot.classList.remove('online');
            text.textContent = 'Disconnected';
        }
    } catch (e) {
        console.error('Status check failed:', e);
        el.statusIndicator.querySelector('.status-text').textContent = 'Offline';
    }
}

async function sendQuery() {
    const question = el.queryInput.value.trim();
    if (!question || state.isLoading) return;
    
    // Add user message
    addMessage(question, 'user');
    el.queryInput.value = '';
    el.queryInput.style.height = 'auto';
    
    // Add to history
    addToHistory(question);
    
    // Show loading
    setLoading(true);
    
    try {
        const params = new URLSearchParams({ question });
        
        const res = await fetch(`${API_BASE}/api/query?${params}`);
        const result = await res.json();
        
        // Add assistant response
        addMessage(result.summary || 'Query completed', 'assistant');
        
        // Display results
        displayResults(result);
        
        if (result.data?.length > 0) {
            showToast('Success', `Found ${result.data.length} records`, 'success');
        } else {
            showToast('No Data', result.data_range || 'No records found', 'warning');
        }
        
    } catch (e) {
        console.error('Query failed:', e);
        addMessage('Sorry, an error occurred. Please try again.', 'assistant');
        showToast('Error', 'Query failed', 'error');
    }
    
    setLoading(false);
}

// ========================================
// Display Functions
// ========================================
function displayResults(result) {
    const { query_type, data, summary, sql_query, data_range } = result;
    state.currentData = data || [];
    state.currentQueryType = query_type;
    
    // Update map
    updateMap(data, query_type);
    
    // Show results panel
    el.resultsPanel.classList.remove('hidden');
    
    // Update summary
    let summaryHtml = `<p>${summary || 'Query completed'}</p>`;
    if (data_range) {
        summaryHtml += `<p style="margin-top: 8px; font-size: 12px; color: var(--text-muted);">📅 ${data_range}</p>`;
    }
    el.summaryContent.innerHTML = summaryHtml;
    
    // Update stats
    updateStats(data, query_type);
    
    // Update SQL
    if (sql_query) {
        el.sqlCode.textContent = sql_query;
    }
    
    // Populate chart axis options based on data
    populateChartAxes(data);
    
    // Update chart
    updateChart(data, query_type);
    
    // Update table
    updateTable(data);
    
    // Switch to summary tab
    switchTab('summary');
}

function populateChartAxes(data) {
    if (!data || data.length === 0) return;
    
    const numericCols = Object.keys(data[0]).filter(k => 
        typeof data[0][k] === 'number' && !k.includes('id')
    );
    
    const allCols = ['auto', ...numericCols];
    
    el.chartXAxis.innerHTML = allCols.map(c => 
        `<option value="${c}">${c === 'auto' ? 'Auto' : c.replace('_', ' ')}</option>`
    ).join('');
    
    el.chartYAxis.innerHTML = allCols.map(c => 
        `<option value="${c}">${c === 'auto' ? 'Auto' : c.replace('_', ' ')}</option>`
    ).join('');
}

function updateStats(data, queryType) {
    if (!data || data.length === 0) {
        el.statsGrid.innerHTML = '';
        return;
    }
    
    const stats = [];
    
    // Record count
    stats.push({ label: 'Records', value: data.length.toLocaleString() });
    
    // Unique floats
    const floats = new Set(data.map(d => d.float_id)).size;
    if (floats > 0) stats.push({ label: 'Floats', value: floats });
    
    // Temperature
    const temps = data.filter(d => d.temperature != null).map(d => d.temperature);
    if (temps.length > 0) {
        const avgTemp = temps.reduce((a, b) => a + b, 0) / temps.length;
        stats.push({ label: 'Avg Temp', value: avgTemp.toFixed(2) + '°C' });
    }
    
    // Salinity
    const sals = data.filter(d => d.salinity != null).map(d => d.salinity);
    if (sals.length > 0) {
        const avgSal = sals.reduce((a, b) => a + b, 0) / sals.length;
        stats.push({ label: 'Avg Salinity', value: avgSal.toFixed(2) + ' PSU' });
    }
    
    el.statsGrid.innerHTML = stats.map(s => `
        <div class="stat-card">
            <div class="stat-label">${s.label}</div>
            <div class="stat-value">${s.value}</div>
        </div>
    `).join('');
}

function updateMap(data, queryType) {
    // Clear existing
    state.markers.forEach(m => m.remove());
    state.polylines.forEach(p => p.remove());
    state.markers = [];
    state.polylines = [];
    
    if (!data || data.length === 0) {
        state.map.setView([10, 75], 4);
        return;
    }
    
    const bounds = L.latLngBounds();
    
    // Trajectory
    if (queryType === 'Trajectory') {
        const path = data.map(d => [d.latitude, d.longitude]);
        const polyline = L.polyline(path, {
            color: '#3b82f6',
            weight: 3,
            opacity: 0.8
        }).addTo(state.map);
        state.polylines.push(polyline);
        
        // Start/end markers
        if (path.length > 0) {
            const startMarker = L.circleMarker(path[0], {
                radius: 8, fillColor: '#22c55e', fillOpacity: 1, color: 'white', weight: 2
            }).bindPopup('Start').addTo(state.map);
            
            const endMarker = L.circleMarker(path[path.length - 1], {
                radius: 8, fillColor: '#ef4444', fillOpacity: 1, color: 'white', weight: 2
            }).bindPopup('End').addTo(state.map);
            
            state.markers.push(startMarker, endMarker);
        }
        
        path.forEach(p => bounds.extend(p));
    } else {
        // Group by float
        const floatGroups = {};
        data.forEach(d => {
            if (d.latitude && d.longitude) {
                const key = d.float_id || 'unknown';
                if (!floatGroups[key]) floatGroups[key] = [];
                floatGroups[key].push(d);
            }
        });
        
        Object.entries(floatGroups).forEach(([floatId, points]) => {
            const latest = points[points.length - 1];
            const marker = L.circleMarker([latest.latitude, latest.longitude], {
                radius: 6,
                fillColor: '#3b82f6',
                fillOpacity: 0.9,
                color: 'white',
                weight: 2
            }).addTo(state.map);
            
            marker.bindPopup(`
                <strong>Float ${floatId}</strong><br>
                Lat: ${latest.latitude?.toFixed(4)}<br>
                Lon: ${latest.longitude?.toFixed(4)}<br>
                ${latest.temperature ? `Temp: ${latest.temperature.toFixed(2)}°C<br>` : ''}
                ${latest.salinity ? `Sal: ${latest.salinity.toFixed(2)} PSU` : ''}
            `);
            
            state.markers.push(marker);
            bounds.extend([latest.latitude, latest.longitude]);
        });
    }
    
    if (bounds.isValid()) {
        state.map.fitBounds(bounds, { padding: [50, 50] });
    }
}

function updateChart(data, queryType) {
    if (state.chart) {
        state.chart.destroy();
        state.chart = null;
    }
    
    if (!data || data.length === 0) return;
    
    const ctx = el.dataChart.getContext('2d');
    const chartType = el.chartTypeSelect.value;
    const xAxis = el.chartXAxis.value;
    const yAxis = el.chartYAxis.value;
    
    // Get numeric columns
    const numericCols = Object.keys(data[0]).filter(k => 
        typeof data[0][k] === 'number' && !k.includes('id')
    );
    
    // Chart configuration based on type
    let config;
    
    if (chartType === 'ts-diagram') {
        // T-S Diagram (Temperature vs Salinity scatter)
        config = createTSDiagram(data);
    } else if (chartType === 'histogram') {
        // Histogram of selected column
        const col = yAxis !== 'auto' ? yAxis : (numericCols.includes('temperature') ? 'temperature' : numericCols[0]);
        config = createHistogram(data, col);
    } else if (chartType === 'scatter') {
        // Scatter plot
        const xCol = xAxis !== 'auto' ? xAxis : 'longitude';
        const yCol = yAxis !== 'auto' ? yAxis : 'latitude';
        config = createScatterPlot(data, xCol, yCol);
    } else if (chartType === 'profile' || (chartType === 'auto' && data[0]?.pressure != null)) {
        // Depth profile
        config = createProfileChart(data);
    } else if (chartType === 'timeseries' || (chartType === 'auto' && data.some(d => d.timestamp))) {
        // Time series
        const col = yAxis !== 'auto' ? yAxis : 'temperature';
        config = createTimeSeriesChart(data, col);
    } else {
        // Default: auto-detect best chart
        config = createAutoChart(data, queryType);
    }
    
    if (config) {
        state.chart = new Chart(ctx, config);
    }
}

function createProfileChart(data) {
    const sorted = [...data].sort((a, b) => (a.pressure || 0) - (b.pressure || 0));
    return {
        type: 'line',
        data: {
            labels: sorted.map(d => d.pressure?.toFixed(0) || ''),
            datasets: [
                {
                    label: 'Temperature (°C)',
                    data: sorted.map(d => d.temperature),
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    label: 'Salinity (PSU)',
                    data: sorted.map(d => d.salinity),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.3,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top', labels: { color: '#94a3b8', font: { size: 10 } } } },
            scales: {
                x: { title: { display: true, text: 'Pressure (dbar)', color: '#94a3b8' }, ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { position: 'left', title: { display: true, text: 'Temp (°C)', color: '#ef4444' }, ticks: { color: '#ef4444' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y1: { position: 'right', title: { display: true, text: 'Salinity', color: '#3b82f6' }, ticks: { color: '#3b82f6' }, grid: { display: false } }
            }
        }
    };
}

function createTimeSeriesChart(data, column) {
    const sorted = [...data].filter(d => d.timestamp && d[column] != null)
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    
    return {
        type: 'line',
        data: {
            labels: sorted.map(d => new Date(d.timestamp).toLocaleDateString()),
            datasets: [{
                label: column.replace('_', ' '),
                data: sorted.map(d => d[column]),
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#94a3b8' } } },
            scales: {
                x: { ticks: { color: '#64748b', maxTicksLimit: 8 }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { title: { display: true, text: column, color: '#94a3b8' }, ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    };
}

function createTSDiagram(data) {
    const points = data.filter(d => d.temperature != null && d.salinity != null)
        .map(d => ({ x: d.salinity, y: d.temperature }));
    
    return {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'T-S Points',
                data: points,
                backgroundColor: 'rgba(59, 130, 246, 0.6)',
                borderColor: '#3b82f6',
                pointRadius: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#94a3b8' } }, title: { display: true, text: 'T-S Diagram', color: '#e2e8f0' } },
            scales: {
                x: { title: { display: true, text: 'Salinity (PSU)', color: '#94a3b8' }, ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { title: { display: true, text: 'Temperature (°C)', color: '#94a3b8' }, ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    };
}

function createScatterPlot(data, xCol, yCol) {
    const points = data.filter(d => d[xCol] != null && d[yCol] != null)
        .map(d => ({ x: d[xCol], y: d[yCol] }));
    
    return {
        type: 'scatter',
        data: {
            datasets: [{
                label: `${yCol} vs ${xCol}`,
                data: points,
                backgroundColor: 'rgba(34, 197, 94, 0.6)',
                borderColor: '#22c55e',
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#94a3b8' } } },
            scales: {
                x: { title: { display: true, text: xCol, color: '#94a3b8' }, ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { title: { display: true, text: yCol, color: '#94a3b8' }, ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    };
}

function createHistogram(data, column) {
    const values = data.filter(d => d[column] != null).map(d => d[column]);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const binCount = 15;
    const binSize = (max - min) / binCount;
    
    const bins = Array(binCount).fill(0);
    const labels = [];
    
    for (let i = 0; i < binCount; i++) {
        const binMin = min + i * binSize;
        labels.push(binMin.toFixed(1));
    }
    
    values.forEach(v => {
        const binIdx = Math.min(Math.floor((v - min) / binSize), binCount - 1);
        bins[binIdx]++;
    });
    
    return {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: `${column} Distribution`,
                data: bins,
                backgroundColor: 'rgba(139, 92, 246, 0.7)',
                borderColor: '#8b5cf6',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#94a3b8' } } },
            scales: {
                x: { title: { display: true, text: column, color: '#94a3b8' }, ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { title: { display: true, text: 'Count', color: '#94a3b8' }, ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    };
}

function createAutoChart(data, queryType) {
    if (data[0]?.pressure != null) return createProfileChart(data);
    if (data.some(d => d.timestamp)) return createTimeSeriesChart(data, 'temperature');
    if (data[0]?.temperature != null && data[0]?.salinity != null) return createTSDiagram(data);
    return null;
}

function updateTable(data) {
    if (!data || data.length === 0) {
        el.tableHead.innerHTML = '';
        el.tableBody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--text-muted);">No data</td></tr>';
        return;
    }
    
    // Get columns
    const columns = Object.keys(data[0]).filter(k => !k.startsWith('_'));
    
    // Header
    el.tableHead.innerHTML = '<tr>' + columns.map(c => `<th>${c}</th>`).join('') + '</tr>';
    
    // Body (limit to 100 rows)
    const rows = data.slice(0, 100);
    el.tableBody.innerHTML = rows.map(row => 
        '<tr>' + columns.map(c => {
            let val = row[c];
            if (val == null) return '<td>-</td>';
            if (typeof val === 'number') val = val.toFixed(4);
            if (typeof val === 'string' && val.includes('T')) {
                val = new Date(val).toLocaleString();
            }
            return `<td>${val}</td>`;
        }).join('') + '</tr>'
    ).join('');
}

function switchTab(tab) {
    // Update buttons
    [el.summaryTabBtn, el.chartTabBtn, el.tableTabBtn].forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    
    // Update content
    [el.summaryTab, el.chartTab, el.tableTab].forEach(content => {
        content.classList.toggle('active', content.id === tab + 'Tab');
    });
}

// ========================================
// Message Functions
// ========================================
function addMessage(text, type) {
    // Remove welcome message
    const welcome = el.chatMessages.querySelector('.welcome-msg');
    if (welcome && type === 'user') {
        welcome.style.display = 'none';
    }
    
    const msg = document.createElement('div');
    msg.className = `message ${type}`;
    msg.innerHTML = `
        <p>${text}</p>
        <span class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
    `;
    
    el.chatMessages.appendChild(msg);
    el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
}

// ========================================
// History Functions
// ========================================
function loadHistory() {
    try {
        state.history = JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
        renderHistory();
    } catch (e) {
        state.history = [];
    }
}

function addToHistory(query) {
    // Remove duplicates
    state.history = state.history.filter(h => h.query !== query);
    
    // Add to front
    state.history.unshift({ query, time: Date.now() });
    
    // Limit
    state.history = state.history.slice(0, MAX_HISTORY);
    
    // Save
    localStorage.setItem(HISTORY_KEY, JSON.stringify(state.history));
    renderHistory();
}

function renderHistory() {
    el.historyCount.textContent = state.history.length;
    
    el.historyList.innerHTML = state.history.map(h => 
        `<div class="history-item" data-query="${h.query}">${h.query}</div>`
    ).join('');
    
    // Click handlers
    el.historyList.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', () => {
            el.queryInput.value = item.dataset.query;
            sendQuery();
        });
    });
}

function clearHistory() {
    state.history = [];
    localStorage.removeItem(HISTORY_KEY);
    renderHistory();
    showToast('History Cleared', '', 'success');
}

// ========================================
// Utility Functions
// ========================================
function setLoading(loading) {
    state.isLoading = loading;
    el.loadingOverlay.classList.toggle('hidden', !loading);
    el.sendBtn.disabled = loading;
}

function showToast(title, message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div>
            <div class="toast-title">${title}</div>
            ${message ? `<div class="toast-message">${message}</div>` : ''}
        </div>
    `;
    
    el.toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function exportData() {
    if (!state.currentData.length) {
        showToast('No Data', 'Nothing to export', 'warning');
        return;
    }
    
    const headers = Object.keys(state.currentData[0]);
    const csv = [
        headers.join(','),
        ...state.currentData.map(row => headers.map(h => JSON.stringify(row[h] ?? '')).join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `floatchart_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    
    showToast('Exported', `${state.currentData.length} records`, 'success');
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        el.mapWrapper.requestFullscreen();
    } else {
        document.exitFullscreen();
    }
}

// ========================================
// Map Explorer (Click to find floats)
// ========================================
function toggleMapExplorer() {
    mapExplorerActive = !mapExplorerActive;
    el.mapExplorerBtn.classList.toggle('active', mapExplorerActive);
    el.mapExplorerBtn.querySelector('span').textContent = mapExplorerActive ? 'Click Map...' : 'Click to Explore';
    
    if (mapExplorerActive) {
        el.mapContainer.style.cursor = 'crosshair';
        state.map.on('click', onMapClick);
        showToast('Map Explorer', 'Click anywhere on the map to find nearby floats', 'info');
    } else {
        el.mapContainer.style.cursor = '';
        state.map.off('click', onMapClick);
    }
}

async function onMapClick(e) {
    const { lat, lng } = e.latlng;
    
    // Add a temporary marker
    const clickMarker = L.circleMarker([lat, lng], {
        radius: 10,
        fillColor: '#f59e0b',
        fillOpacity: 0.8,
        color: 'white',
        weight: 2
    }).addTo(state.map);
    
    clickMarker.bindPopup(`<strong>Searching...</strong><br>Lat: ${lat.toFixed(4)}<br>Lon: ${lng.toFixed(4)}`).openPopup();
    
    // Query for nearby floats
    setLoading(true);
    
    try {
        const question = `Find ARGO floats within 200km of latitude ${lat.toFixed(2)} longitude ${lng.toFixed(2)}`;
        addMessage(`🗺️ Exploring: ${lat.toFixed(4)}, ${lng.toFixed(4)}`, 'user');
        
        const params = new URLSearchParams({ question });
        const res = await fetch(`${API_BASE}/api/query?${params}`);
        const result = await res.json();
        
        // Remove click marker
        clickMarker.remove();
        
        // Display results
        if (result.data?.length > 0) {
            addMessage(result.summary || `Found ${result.data.length} nearby records`, 'assistant');
            displayResults(result);
            showToast('Found', `${result.data.length} records nearby`, 'success');
        } else {
            addMessage(result.summary || 'No floats found in this area', 'assistant');
            showToast('No Data', result.data_range || 'No floats found nearby', 'warning');
        }
        
    } catch (e) {
        clickMarker.remove();
        console.error('Map query failed:', e);
        addMessage('Error searching this location', 'assistant');
        showToast('Error', 'Search failed', 'error');
    }
    
    setLoading(false);
}

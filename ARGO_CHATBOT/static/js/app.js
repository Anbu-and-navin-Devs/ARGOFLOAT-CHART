/**
 * FloatChat - Ocean Intelligence
 * Main Application JavaScript
 */

// ========================================
// Configuration & State
// ========================================

const API_BASE_URL = '';  // Same origin
const HISTORY_KEY = 'floatchat_history';
const MAX_HISTORY_ITEMS = 20;

// Application State
const state = {
    map: null,
    chart: null,
    markers: [],
    polylines: [],
    currentData: [],
    queryHistory: [],
    isLoading: false,
    periods: {},
    selectedYear: null,
    selectedMonth: null
};

// ========================================
// DOM Elements
// ========================================

const elements = {
    // Chat Panel
    chatPanel: document.getElementById('chatPanel'),
    panelToggle: document.getElementById('panelToggle'),
    queryInput: document.getElementById('queryInput'),
    sendBtn: document.getElementById('sendBtn'),
    chatMessages: document.getElementById('chatMessages'),
    historyList: document.getElementById('historyList'),
    clearHistory: document.getElementById('clearHistory'),
    statusIndicator: document.getElementById('statusIndicator'),
    
    // Results Panel
    mapContainer: document.getElementById('mapContainer'),
    mapSection: document.getElementById('mapSection'),
    fullscreenMap: document.getElementById('fullscreenMap'),
    periodYear: document.getElementById('periodYear'),
    periodMonth: document.getElementById('periodMonth'),
    
    // Visualization
    chartContainer: document.getElementById('chartContainer'),
    tableContainer: document.getElementById('tableContainer'),
    chartPlaceholder: document.getElementById('chartPlaceholder'),
    tablePlaceholder: document.getElementById('tablePlaceholder'),
    dataChart: document.getElementById('dataChart'),
    tableHead: document.getElementById('tableHead'),
    tableBody: document.getElementById('tableBody'),
    chartViewBtn: document.getElementById('chartViewBtn'),
    tableViewBtn: document.getElementById('tableViewBtn'),
    exportBtn: document.getElementById('exportBtn'),
    
    // Summary
    summaryContent: document.getElementById('summaryContent'),
    statsGrid: document.getElementById('statsGrid'),
    sqlSection: document.getElementById('sqlSection'),
    sqlToggle: document.getElementById('sqlToggle'),
    sqlCode: document.getElementById('sqlCode'),
    
    // Overlays
    loadingOverlay: document.getElementById('loadingOverlay'),
    toastContainer: document.getElementById('toastContainer')
};

// ========================================
// Initialization
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    initializeMap();
    initializeEventListeners();
    loadQueryHistory();
    checkApiStatus();
    loadAvailablePeriods();
});

function initializeMap() {
    // Initialize Leaflet map centered on Indian Ocean
    state.map = L.map(elements.mapContainer, {
        center: [13, 80],
        zoom: 4,
        zoomControl: true
    });
    
    // Add dark tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(state.map);
    
    // Fix map sizing issues
    setTimeout(() => {
        state.map.invalidateSize();
    }, 100);
}

function initializeEventListeners() {
    // Send button click
    elements.sendBtn.addEventListener('click', handleSendQuery);
    
    // Enter key to send
    elements.queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendQuery();
        }
    });
    
    // Auto-resize textarea
    elements.queryInput.addEventListener('input', autoResizeTextarea);
    
    // Suggestion buttons
    document.querySelectorAll('.suggestion-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.dataset.query;
            elements.queryInput.value = query;
            handleSendQuery();
        });
    });
    
    // Panel toggle
    elements.panelToggle.addEventListener('click', toggleChatPanel);
    
    // Clear history
    elements.clearHistory.addEventListener('click', clearQueryHistory);
    
    // View toggle (chart/table)
    elements.chartViewBtn.addEventListener('click', () => switchView('chart'));
    elements.tableViewBtn.addEventListener('click', () => switchView('table'));
    
    // Export button
    elements.exportBtn.addEventListener('click', exportData);
    
    // Fullscreen map
    elements.fullscreenMap.addEventListener('click', toggleFullscreenMap);
    
    // SQL toggle
    elements.sqlToggle.addEventListener('click', toggleSqlSection);
    
    // Period selectors
    elements.periodYear.addEventListener('change', handlePeriodChange);
    elements.periodMonth.addEventListener('change', handlePeriodChange);
    
    // Window resize for map
    window.addEventListener('resize', () => {
        if (state.map) {
            state.map.invalidateSize();
        }
    });
}

// ========================================
// API Functions
// ========================================

async function checkApiStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/status`);
        const data = await response.json();
        
        const statusDot = elements.statusIndicator.querySelector('.status-dot');
        const statusText = elements.statusIndicator.querySelector('span:last-child');
        
        if (data.status === 'online' && data.database === 'connected') {
            statusDot.classList.add('online');
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.remove('online');
            statusText.textContent = 'Disconnected';
        }
    } catch (error) {
        console.error('Status check failed:', error);
        const statusDot = elements.statusIndicator.querySelector('.status-dot');
        const statusText = elements.statusIndicator.querySelector('span:last-child');
        statusDot.classList.remove('online');
        statusText.textContent = 'Offline';
    }
}

async function loadAvailablePeriods() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/available_periods`);
        const data = await response.json();
        
        if (data.periods) {
            state.periods = data.periods;
            populatePeriodSelectors();
        }
    } catch (error) {
        console.error('Failed to load periods:', error);
    }
}

function populatePeriodSelectors() {
    const years = Object.keys(state.periods).sort((a, b) => b - a);
    
    elements.periodYear.innerHTML = '<option value="">All Years</option>';
    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        elements.periodYear.appendChild(option);
    });
}

function handlePeriodChange() {
    const year = elements.periodYear.value;
    state.selectedYear = year || null;
    
    // Update month options based on selected year
    elements.periodMonth.innerHTML = '<option value="">All Months</option>';
    
    if (year && state.periods[year]) {
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        state.periods[year].forEach(month => {
            const option = document.createElement('option');
            option.value = month;
            option.textContent = monthNames[month - 1];
            elements.periodMonth.appendChild(option);
        });
    }
    
    state.selectedMonth = elements.periodMonth.value || null;
}

async function sendQuery(query) {
    showLoading(true);
    
    try {
        const params = new URLSearchParams({ question: query });
        if (state.selectedYear) params.append('year', state.selectedYear);
        if (state.selectedMonth) params.append('month', state.selectedMonth);
        
        const response = await fetch(`${API_BASE_URL}/api/query?${params}`);
        const data = await response.json();
        
        if (response.ok) {
            return data;
        } else {
            throw new Error(data.error || 'Query failed');
        }
    } catch (error) {
        console.error('Query error:', error);
        throw error;
    } finally {
        showLoading(false);
    }
}

// ========================================
// Query Handling
// ========================================

async function handleSendQuery() {
    const query = elements.queryInput.value.trim();
    
    if (!query || state.isLoading) return;
    
    // Add user message to chat
    addMessage(query, 'user');
    elements.queryInput.value = '';
    autoResizeTextarea();
    
    // Save to history
    addToHistory(query);
    
    try {
        const result = await sendQuery(query);
        
        // Process and display results
        displayResults(result);
        
        // Add assistant response
        addMessage(result.summary || 'Query completed successfully.', 'assistant');
        
    } catch (error) {
        addMessage(`Sorry, there was an error: ${error.message}`, 'assistant', true);
        showToast('Error', error.message, 'error');
    }
}

function displayResults(result) {
    const { query_type, data, summary, sql_query, data_range } = result;
    
    state.currentData = data || [];
    
    // Update map
    updateMap(data, query_type);
    
    // Update visualization
    updateVisualization(data, query_type);
    
    // Update summary with data range info
    const fullSummary = data_range ? `${summary}\n\n📅 ${data_range}` : summary;
    updateSummary(fullSummary, query_type, data);
    
    // Update SQL
    if (sql_query) {
        elements.sqlCode.textContent = sql_query;
    }
    
    // Show success toast
    if (data && data.length > 0) {
        showToast('Success', `Found ${data.length} records`, 'success');
    } else {
        showToast('No Data', data_range || 'No records found', 'warning');
    }
}

// ========================================
// Map Functions
// ========================================

function updateMap(data, queryType) {
    // Clear existing markers and polylines
    state.markers.forEach(marker => marker.remove());
    state.polylines.forEach(polyline => polyline.remove());
    state.markers = [];
    state.polylines = [];
    
    if (!data || data.length === 0) {
        state.map.setView([13, 80], 4);
        return;
    }
    
    // Create custom marker icon
    const floatIcon = L.divIcon({
        className: 'float-marker-icon',
        iconSize: [14, 14]
    });
    
    const bounds = L.latLngBounds();
    
    // Group data by float_id for trajectories
    if (queryType === 'Trajectory') {
        const floatGroups = {};
        data.forEach(point => {
            const fid = point.float_id;
            if (!floatGroups[fid]) floatGroups[fid] = [];
            floatGroups[fid].push(point);
        });
        
        Object.entries(floatGroups).forEach(([floatId, points]) => {
            // Sort by timestamp
            points.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
            
            // Create polyline
            const latLngs = points.map(p => [p.latitude, p.longitude]);
            const polyline = L.polyline(latLngs, {
                color: '#2E8BFF',
                weight: 3,
                opacity: 0.8
            }).addTo(state.map);
            state.polylines.push(polyline);
            
            // Add markers at start and end
            if (points.length > 0) {
                const startMarker = L.marker([points[0].latitude, points[0].longitude], { icon: floatIcon })
                    .bindPopup(createPopupContent(points[0], 'Start'))
                    .addTo(state.map);
                state.markers.push(startMarker);
                bounds.extend([points[0].latitude, points[0].longitude]);
                
                if (points.length > 1) {
                    const endPoint = points[points.length - 1];
                    const endMarker = L.marker([endPoint.latitude, endPoint.longitude], { icon: floatIcon })
                        .bindPopup(createPopupContent(endPoint, 'End'))
                        .addTo(state.map);
                    state.markers.push(endMarker);
                    bounds.extend([endPoint.latitude, endPoint.longitude]);
                }
            }
        });
    } else {
        // Add markers for each data point (limit to 100 for performance)
        const displayData = data.slice(0, 100);
        displayData.forEach((point, index) => {
            if (point.latitude && point.longitude) {
                const marker = L.marker([point.latitude, point.longitude], { icon: floatIcon })
                    .bindPopup(createPopupContent(point))
                    .addTo(state.map);
                state.markers.push(marker);
                bounds.extend([point.latitude, point.longitude]);
            }
        });
    }
    
    // Fit map to bounds
    if (state.markers.length > 0 || state.polylines.length > 0) {
        state.map.fitBounds(bounds, { padding: [50, 50] });
    }
}

function createPopupContent(point, label = '') {
    let content = `<div style="font-size: 13px;">`;
    
    if (label) {
        content += `<strong>${label}</strong><br>`;
    }
    
    if (point.float_id) {
        content += `<strong>Float ID:</strong> ${point.float_id}<br>`;
    }
    if (point.timestamp) {
        content += `<strong>Time:</strong> ${formatTimestamp(point.timestamp)}<br>`;
    }
    if (point.latitude !== undefined) {
        content += `<strong>Lat:</strong> ${point.latitude.toFixed(4)}<br>`;
    }
    if (point.longitude !== undefined) {
        content += `<strong>Lon:</strong> ${point.longitude.toFixed(4)}<br>`;
    }
    if (point.distance_km !== undefined) {
        content += `<strong>Distance:</strong> ${point.distance_km.toFixed(2)} km<br>`;
    }
    if (point.temperature !== undefined && point.temperature !== null) {
        content += `<strong>Temp:</strong> ${point.temperature.toFixed(2)} °C<br>`;
    }
    if (point.salinity !== undefined && point.salinity !== null) {
        content += `<strong>Salinity:</strong> ${point.salinity.toFixed(2)} PSU<br>`;
    }
    
    content += `</div>`;
    return content;
}

function toggleFullscreenMap() {
    elements.mapSection.classList.toggle('fullscreen');
    setTimeout(() => {
        state.map.invalidateSize();
    }, 300);
}

// ========================================
// Visualization Functions
// ========================================

function updateVisualization(data, queryType) {
    if (!data || data.length === 0) {
        elements.chartPlaceholder.classList.remove('hidden');
        elements.tablePlaceholder.classList.remove('hidden');
        return;
    }
    
    elements.chartPlaceholder.classList.add('hidden');
    elements.tablePlaceholder.classList.add('hidden');
    
    // Update chart
    updateChart(data, queryType);
    
    // Update table
    updateTable(data);
}

function updateChart(data, queryType) {
    // Destroy existing chart
    if (state.chart) {
        state.chart.destroy();
    }
    
    const ctx = elements.dataChart.getContext('2d');
    
    // Determine chart type and configuration based on query type
    let chartConfig;
    
    if (queryType === 'Profile') {
        chartConfig = createProfileChart(data);
    } else if (queryType === 'Time-Series') {
        chartConfig = createTimeSeriesChart(data);
    } else if (queryType === 'Trajectory') {
        chartConfig = createTrajectoryChart(data);
    } else {
        chartConfig = createDefaultChart(data);
    }
    
    state.chart = new Chart(ctx, chartConfig);
}

function createProfileChart(data) {
    const sensorColumns = ['temperature', 'salinity', 'dissolved_oxygen', 'chlorophyll'];
    const datasets = [];
    const colors = ['#2E8BFF', '#6C5CE7', '#2E7D32', '#FFB020'];
    
    sensorColumns.forEach((col, index) => {
        if (data[0] && data[0][col] !== undefined) {
            datasets.push({
                label: formatColumnName(col),
                data: data.map(d => ({ x: d[col], y: d.pressure || 0 })),
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + '40',
                borderWidth: 2,
                pointRadius: 3,
                fill: false
            });
        }
    });
    
    return {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            scales: {
                y: {
                    reverse: true,
                    title: { display: true, text: 'Pressure (dbar)', color: '#8A98A8' },
                    grid: { color: '#2E3843' },
                    ticks: { color: '#8A98A8' }
                },
                x: {
                    title: { display: true, text: 'Value', color: '#8A98A8' },
                    grid: { color: '#2E3843' },
                    ticks: { color: '#8A98A8' }
                }
            },
            plugins: {
                legend: { labels: { color: '#E6EDF3' } },
                title: { display: true, text: 'Depth Profile', color: '#E6EDF3' }
            }
        }
    };
}

function createTimeSeriesChart(data) {
    const sensorColumns = ['temperature', 'salinity', 'dissolved_oxygen', 'chlorophyll'];
    const datasets = [];
    const colors = ['#2E8BFF', '#6C5CE7', '#2E7D32', '#FFB020'];
    
    const sortedData = [...data].sort((a, b) => new Date(a.day || a.timestamp) - new Date(b.day || b.timestamp));
    const labels = sortedData.map(d => formatTimestamp(d.day || d.timestamp, true));
    
    sensorColumns.forEach((col, index) => {
        if (data[0] && data[0][col] !== undefined) {
            datasets.push({
                label: formatColumnName(col),
                data: sortedData.map(d => d[col]),
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + '40',
                borderWidth: 2,
                pointRadius: 2,
                fill: true,
                tension: 0.3
            });
        }
    });
    
    return {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: { color: '#2E3843' },
                    ticks: { color: '#8A98A8' }
                },
                x: {
                    grid: { color: '#2E3843' },
                    ticks: { color: '#8A98A8', maxRotation: 45 }
                }
            },
            plugins: {
                legend: { labels: { color: '#E6EDF3' } },
                title: { display: true, text: 'Time Series', color: '#E6EDF3' }
            }
        }
    };
}

function createTrajectoryChart(data) {
    // For trajectory, show position over time or distance
    const sortedData = [...data].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    
    return {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Float Trajectory',
                data: sortedData.map(d => ({ x: d.longitude, y: d.latitude })),
                borderColor: '#2E8BFF',
                backgroundColor: '#2E8BFF',
                pointRadius: 4,
                showLine: true,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    title: { display: true, text: 'Latitude', color: '#8A98A8' },
                    grid: { color: '#2E3843' },
                    ticks: { color: '#8A98A8' }
                },
                x: {
                    title: { display: true, text: 'Longitude', color: '#8A98A8' },
                    grid: { color: '#2E3843' },
                    ticks: { color: '#8A98A8' }
                }
            },
            plugins: {
                legend: { labels: { color: '#E6EDF3' } },
                title: { display: true, text: 'Trajectory (Lat/Lon)', color: '#E6EDF3' }
            }
        }
    };
}

function createDefaultChart(data) {
    // Find numeric columns for bar chart
    const numericColumns = Object.keys(data[0] || {}).filter(key => {
        return typeof data[0][key] === 'number' && 
               !['latitude', 'longitude', 'float_id', 'pressure'].includes(key);
    });
    
    if (numericColumns.length === 0) {
        return createCountChart(data);
    }
    
    const labels = data.slice(0, 20).map((d, i) => d.float_id || `Record ${i + 1}`);
    const datasets = [];
    const colors = ['#2E8BFF', '#6C5CE7', '#2E7D32', '#FFB020'];
    
    numericColumns.slice(0, 4).forEach((col, index) => {
        datasets.push({
            label: formatColumnName(col),
            data: data.slice(0, 20).map(d => d[col]),
            backgroundColor: colors[index % colors.length] + '80',
            borderColor: colors[index % colors.length],
            borderWidth: 1
        });
    });
    
    return {
        type: 'bar',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: { color: '#2E3843' },
                    ticks: { color: '#8A98A8' }
                },
                x: {
                    grid: { color: '#2E3843' },
                    ticks: { color: '#8A98A8' }
                }
            },
            plugins: {
                legend: { labels: { color: '#E6EDF3' } }
            }
        }
    };
}

function createCountChart(data) {
    return {
        type: 'doughnut',
        data: {
            labels: ['Records Found'],
            datasets: [{
                data: [data.length],
                backgroundColor: ['#2E8BFF'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#E6EDF3' } },
                title: {
                    display: true,
                    text: `Total Records: ${data.length}`,
                    color: '#E6EDF3',
                    font: { size: 16 }
                }
            }
        }
    };
}

function updateTable(data) {
    if (!data || data.length === 0) {
        elements.tableHead.innerHTML = '';
        elements.tableBody.innerHTML = '';
        return;
    }
    
    // Get columns
    const columns = Object.keys(data[0]);
    
    // Create header
    elements.tableHead.innerHTML = `
        <tr>
            ${columns.map(col => `<th>${formatColumnName(col)}</th>`).join('')}
        </tr>
    `;
    
    // Create body (limit to 100 rows)
    elements.tableBody.innerHTML = data.slice(0, 100).map(row => `
        <tr>
            ${columns.map(col => `<td>${formatCellValue(row[col], col)}</td>`).join('')}
        </tr>
    `).join('');
}

function switchView(view) {
    if (view === 'chart') {
        elements.chartContainer.classList.remove('hidden');
        elements.tableContainer.classList.add('hidden');
        elements.chartViewBtn.classList.add('active');
        elements.tableViewBtn.classList.remove('active');
    } else {
        elements.chartContainer.classList.add('hidden');
        elements.tableContainer.classList.remove('hidden');
        elements.chartViewBtn.classList.remove('active');
        elements.tableViewBtn.classList.add('active');
    }
}

// ========================================
// Summary Functions
// ========================================

function updateSummary(summary, queryType, data) {
    // Update summary text
    const isError = queryType === 'Error';
    elements.summaryContent.innerHTML = `
        <p class="summary-text ${isError ? 'error' : ''}">${summary || 'No summary available.'}</p>
    `;
    
    // Update stats cards
    updateStatsCards(data, queryType);
}

function updateStatsCards(data, queryType) {
    elements.statsGrid.innerHTML = '';
    
    if (!data || data.length === 0) return;
    
    // Add record count
    addStatCard('Records', data.length, '');
    
    // Calculate stats for numeric columns
    const numericColumns = ['temperature', 'salinity', 'dissolved_oxygen', 'chlorophyll', 'distance_km'];
    
    numericColumns.forEach(col => {
        const values = data.map(d => d[col]).filter(v => v !== null && v !== undefined && !isNaN(v));
        
        if (values.length > 0) {
            const avg = values.reduce((a, b) => a + b, 0) / values.length;
            const unit = getUnit(col);
            addStatCard(`Avg ${formatColumnName(col)}`, avg.toFixed(2), unit);
        }
    });
    
    // Add unique floats count
    const uniqueFloats = new Set(data.map(d => d.float_id).filter(Boolean)).size;
    if (uniqueFloats > 0) {
        addStatCard('Unique Floats', uniqueFloats, '');
    }
}

function addStatCard(label, value, unit) {
    const card = document.createElement('div');
    card.className = 'stat-card';
    card.innerHTML = `
        <div class="stat-label">${label}</div>
        <div class="stat-value">${value}<span class="stat-unit">${unit}</span></div>
    `;
    elements.statsGrid.appendChild(card);
}

function toggleSqlSection() {
    elements.sqlSection.classList.toggle('collapsed');
}

// ========================================
// Chat Functions
// ========================================

function addMessage(text, type, isError = false) {
    // Remove welcome message if present
    const welcome = elements.chatMessages.querySelector('.welcome-message');
    if (welcome) welcome.remove();
    
    const message = document.createElement('div');
    message.className = `message ${type}`;
    
    const avatar = type === 'user' ? '👤' : '🌊';
    
    message.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content ${isError ? 'error' : ''}">${text}</div>
    `;
    
    elements.chatMessages.appendChild(message);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function toggleChatPanel() {
    elements.chatPanel.classList.toggle('collapsed');
    
    // Update toggle icon direction
    const icon = elements.panelToggle.querySelector('svg');
    if (elements.chatPanel.classList.contains('collapsed')) {
        icon.style.transform = 'rotate(180deg)';
    } else {
        icon.style.transform = 'rotate(0deg)';
    }
    
    // Resize map after panel toggle
    setTimeout(() => {
        if (state.map) state.map.invalidateSize();
    }, 300);
}

function autoResizeTextarea() {
    const textarea = elements.queryInput;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

// ========================================
// History Functions
// ========================================

function loadQueryHistory() {
    try {
        const saved = localStorage.getItem(HISTORY_KEY);
        state.queryHistory = saved ? JSON.parse(saved) : [];
        renderHistory();
    } catch (error) {
        console.error('Failed to load history:', error);
        state.queryHistory = [];
    }
}

function addToHistory(query) {
    // Remove duplicate if exists
    state.queryHistory = state.queryHistory.filter(h => h.query !== query);
    
    // Add to beginning
    state.queryHistory.unshift({
        query,
        timestamp: new Date().toISOString()
    });
    
    // Limit history size
    if (state.queryHistory.length > MAX_HISTORY_ITEMS) {
        state.queryHistory = state.queryHistory.slice(0, MAX_HISTORY_ITEMS);
    }
    
    // Save and render
    saveHistory();
    renderHistory();
}

function saveHistory() {
    try {
        localStorage.setItem(HISTORY_KEY, JSON.stringify(state.queryHistory));
    } catch (error) {
        console.error('Failed to save history:', error);
    }
}

function renderHistory() {
    elements.historyList.innerHTML = state.queryHistory.slice(0, 10).map(item => `
        <div class="history-item" onclick="useHistoryQuery('${escapeHtml(item.query)}')">
            <span class="query-text">${escapeHtml(item.query)}</span>
            <span class="query-time">${formatRelativeTime(item.timestamp)}</span>
        </div>
    `).join('');
}

function useHistoryQuery(query) {
    elements.queryInput.value = query;
    elements.queryInput.focus();
}

function clearQueryHistory() {
    state.queryHistory = [];
    saveHistory();
    renderHistory();
    showToast('History Cleared', 'Your query history has been cleared.', 'success');
}

// ========================================
// Export Functions
// ========================================

function exportData() {
    if (!state.currentData || state.currentData.length === 0) {
        showToast('No Data', 'There is no data to export.', 'warning');
        return;
    }
    
    // Convert to CSV
    const columns = Object.keys(state.currentData[0]);
    const header = columns.join(',');
    const rows = state.currentData.map(row => 
        columns.map(col => {
            let val = row[col];
            if (val === null || val === undefined) return '';
            if (typeof val === 'string' && val.includes(',')) return `"${val}"`;
            return val;
        }).join(',')
    );
    
    const csv = [header, ...rows].join('\n');
    
    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `floatchat_export_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast('Export Complete', `Exported ${state.currentData.length} records to CSV.`, 'success');
}

// ========================================
// UI Utility Functions
// ========================================

function showLoading(show) {
    state.isLoading = show;
    elements.loadingOverlay.classList.toggle('hidden', !show);
    elements.sendBtn.disabled = show;
}

function showToast(title, message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        </button>
    `;
    
    elements.toastContainer.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

// ========================================
// Formatting Utilities
// ========================================

function formatColumnName(col) {
    return col
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

function formatCellValue(value, column) {
    if (value === null || value === undefined) return '-';
    
    if (column === 'timestamp' || column === 'day') {
        return formatTimestamp(value);
    }
    
    if (typeof value === 'number') {
        if (column === 'latitude' || column === 'longitude') {
            return value.toFixed(4);
        }
        return value.toFixed(2);
    }
    
    return value;
}

function formatTimestamp(ts, short = false) {
    if (!ts) return '-';
    
    const date = new Date(ts);
    if (isNaN(date.getTime())) return ts;
    
    if (short) {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
    
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatRelativeTime(timestamp) {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return then.toLocaleDateString();
}

function getUnit(column) {
    const units = {
        temperature: '°C',
        salinity: 'PSU',
        dissolved_oxygen: 'μmol/kg',
        chlorophyll: 'mg/m³',
        pressure: 'dbar',
        distance_km: 'km'
    };
    return units[column] || '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make useHistoryQuery available globally
window.useHistoryQuery = useHistoryQuery;

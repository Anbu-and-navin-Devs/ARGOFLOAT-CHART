/**
 * FloatChart - Ocean data visualization
 * Main application script
 */

'use strict';

// ========================================
// Configuration
// ========================================
const CONFIG = {
    VERSION: '1.0.0',
    API_BASE: '',
    HISTORY_KEY: 'floatchart_history',
    THEME_KEY: 'floatchart_theme',
    SETTINGS_KEY: 'floatchart_settings',
    CONVERSATION_KEY: 'floatchart_conversation',
    MAX_HISTORY: 25,
    MAX_CONVERSATION: 20,
    ANIMATION_DURATION: 300,
    TOAST_DURATION: 4000,
    DEBOUNCE_DELAY: 200,
    TYPING_SPEED: 15,
    MAP_DEFAULT_CENTER: [10, 75],
    MAP_DEFAULT_ZOOM: 4,
    STREAM_ENABLED: true
};

// Keyboard Shortcuts
const SHORTCUTS = {
    'Ctrl+Enter': 'sendQuery',
    'Ctrl+/': 'focusInput',
    'Ctrl+K': 'toggleSuggestions',
    'Ctrl+D': 'toggleTheme',
    'Ctrl+E': 'exportData',
    'Ctrl+M': 'toggleMap',
    'Escape': 'closeModals'
};

// ========================================
// Application State
// ========================================
const state = {
    // Core
    map: null,
    chart: null,
    
    // Data
    markers: [],
    polylines: [],
    currentData: [],
    currentQueryType: null,
    conversationHistory: [],
    
    // UI
    history: [],
    isLoading: false,
    isStreaming: false,
    panelWidth: 420,
    currentTheme: 'dark',
    showSuggestions: false,
    
    // Voice
    isVoiceActive: false,
    recognition: null,
    audioContext: null,
    analyser: null,
    
    // PWA
    deferredPrompt: null,
    isOnline: navigator.onLine,
    
    // Performance
    lastQueryTime: 0,
    queryCount: 0
};

// ========================================
// Smart Query Suggestions with Categories
// ========================================
const QUERY_SUGGESTIONS = {
    '🌡️ Temperature': [
        "What's the average temperature in Arabian Sea?",
        "Show temperature distribution in Bay of Bengal",
        "Find warmest waters near Indian coast in 2024",
        "Temperature profile for float 2902269",
        "Compare monsoon vs winter temperatures"
    ],
    '🧪 Salinity': [
        "Analyze salinity patterns in Indian Ocean",
        "Find low salinity regions (freshwater influence)",
        "Salinity gradient near Ganges river mouth",
        "Deep water salinity below 1000m"
    ],
    '📍 Location': [
        "Find floats near Chennai (13°N, 80°E)",
        "Show all active floats in Arabian Sea",
        "Data from Bay of Bengal this month",
        "Nearest floats to Mumbai within 500km"
    ],
    '🛤️ Trajectory': [
        "Track trajectory of float 2902115",
        "Where did float 2901234 travel in 2024?",
        "Show float movement patterns"
    ],
    '⬇️ Depth Profile': [
        "Vertical profile to 2000m depth",
        "Temperature vs pressure profile",
        "Mixed layer depth analysis"
    ],
    '📊 Statistics': [
        "How many active floats are there?",
        "Summary statistics for all data",
        "Data coverage for 2024",
        "Count records by region"
    ]
};

// ========================================
// DOM Elements Cache with Safety
// ========================================
const $ = (id) => document.getElementById(id);
const $$ = (selector) => document.querySelectorAll(selector);
const $one = (selector) => document.querySelector(selector);

const el = {};

function cacheElements() {
    const ids = [
        'mainContent', 'mapContainer', 'mapWrapper', 'mapInfoBadge', 'fullscreenMap',
        'openChatBtn', 'dashboardBtn', 'resultsPanel', 'summaryTabBtn', 'chartTabBtn',
        'tableTabBtn', 'summaryTab', 'chartTab', 'tableTab', 'summaryContent', 'statsGrid',
        'sqlToggle', 'sqlCode', 'chartContainer', 'chartTypeSelect', 'chartXAxis',
        'chartYAxis', 'dataChart', 'tableHead', 'tableBody', 'exportBtn', 'shareBtn',
        'closeResults', 'chatPanel', 'resizeHandle', 'panelToggle', 'chatMessages',
        'dataRangeInfo', 'historyToggle', 'historyCount', 'historyList', 'clearHistory',
        'queryInput', 'voiceBtn', 'sendBtn', 'statusIndicator', 'suggestionsDropdown',
        'themeToggle', 'loadingOverlay', 'toastContainer', 'shareModal', 'pwaPrompt'
    ];
    
    ids.forEach(id => {
        el[id] = $(id);
    });
}

// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', async () => {
    console.log(`🌊 FloatChart v${CONFIG.VERSION} initializing...`);
    
    cacheElements();
    
    // Initialize all systems
    await Promise.all([
        initTheme(),
        initMap(),
        loadHistory(),
        loadConversation(),
        loadSettings()
    ]);
    
    initEventListeners();
    initKeyboardShortcuts();
    initShortcutsModal();
    initTourHandlers();
    initResizable();
    initVoiceRecognition();
    initSuggestions();
    initPWA();
    initPerformanceMonitor();
    initOnboardingTour();
    
    // Check API status
    await checkStatus();
    
    // Show welcome animation
    showWelcomeAnimation();
    
    console.log(`✅ FloatChart v${CONFIG.VERSION} ready!`);
});

// ========================================
// Welcome Animation
// ========================================
function showWelcomeAnimation() {
    const welcome = $one('.welcome-msg');
    if (welcome) {
        welcome.style.opacity = '0';
        welcome.style.transform = 'translateY(20px)';
        
        requestAnimationFrame(() => {
            welcome.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
            welcome.style.opacity = '1';
            welcome.style.transform = 'translateY(0)';
        });
    }
}

// ========================================
// Theme Management (Enhanced)
// ========================================
async function initTheme() {
    const savedTheme = localStorage.getItem(CONFIG.THEME_KEY);
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    state.currentTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
    applyTheme(state.currentTheme, false);
    
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem(CONFIG.THEME_KEY)) {
            applyTheme(e.matches ? 'dark' : 'light', true);
        }
    });
}

function applyTheme(theme, animate = true) {
    state.currentTheme = theme;
    
    if (animate) {
        document.body.style.transition = 'background-color 0.3s, color 0.3s';
    }
    
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(CONFIG.THEME_KEY, theme);
    
    // Update theme toggle icons
    if (el.themeToggle) {
        const sunIcon = el.themeToggle.querySelector('.sun-icon');
        const moonIcon = el.themeToggle.querySelector('.moon-icon');
        if (sunIcon && moonIcon) {
            sunIcon.style.display = theme === 'dark' ? 'block' : 'none';
            moonIcon.style.display = theme === 'light' ? 'block' : 'none';
        }
    }
    
    // Update map tiles
    updateMapTiles();
    
    // Update chart theme
    if (state.chart) {
        updateChartTheme();
    }
}

function toggleTheme() {
    const newTheme = state.currentTheme === 'dark' ? 'light' : 'dark';
    applyTheme(newTheme, true);
    
    // Haptic feedback on mobile
    if (navigator.vibrate) {
        navigator.vibrate(10);
    }
    
    showToast('Theme Changed', `Switched to ${newTheme} mode`, 'success');
}

function updateMapTiles() {
    if (!state.map) return;
    
    state.map.eachLayer(layer => {
        if (layer instanceof L.TileLayer) {
            state.map.removeLayer(layer);
        }
    });
    
    const tileUrl = state.currentTheme === 'dark' 
        ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
        : 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
    
    L.tileLayer(tileUrl, { maxZoom: 19 }).addTo(state.map);
}

// ========================================
// Map Initialization (Enhanced)
// ========================================
async function initMap() {
    if (!el.mapContainer) return;
    
    state.map = L.map(el.mapContainer, {
        center: CONFIG.MAP_DEFAULT_CENTER,
        zoom: CONFIG.MAP_DEFAULT_ZOOM,
        zoomControl: true,
        attributionControl: false,
        fadeAnimation: true,
        zoomAnimation: true
    });
    
    updateMapTiles();
    
    // Custom attribution
    L.control.attribution({
        prefix: '<a href="https://leafletjs.com" target="_blank">Leaflet</a> | © OpenStreetMap'
    }).addTo(state.map);
    
    // Add scale control
    L.control.scale({
        imperial: false,
        position: 'bottomleft'
    }).addTo(state.map);
    
    // Invalidate size after render
    setTimeout(() => state.map.invalidateSize(), 100);
}

// ========================================
// Event Listeners (Enhanced)
// ========================================
function initEventListeners() {
    // Theme toggle
    el.themeToggle?.addEventListener('click', toggleTheme);
    
    // Quick actions with animation
    $$('.quick-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            // Ripple effect
            createRipple(e, btn);
            
            const query = btn.dataset.query;
            el.queryInput.value = query;
            hideSuggestions();
            sendQuery();
        });
    });
    
    // Send button with loading state
    el.sendBtn?.addEventListener('click', () => {
        if (!state.isLoading) {
            sendQuery();
        }
    });
    
    // Voice button
    el.voiceBtn?.addEventListener('click', toggleVoiceInput);
    
    // Input events
    el.queryInput?.addEventListener('keydown', handleInputKeydown);
    el.queryInput?.addEventListener('focus', handleInputFocus);
    el.queryInput?.addEventListener('input', debounce(handleInputChange, 150));
    el.queryInput?.addEventListener('blur', () => {
        setTimeout(hideSuggestions, 200);
    });
    
    // Panel toggle
    el.panelToggle?.addEventListener('click', toggleChatPanel);
    
    // Open chat button
    el.openChatBtn?.addEventListener('click', openChatPanel);
    
    // Tab switching with animation
    [el.summaryTabBtn, el.chartTabBtn, el.tableTabBtn].forEach(btn => {
        btn?.addEventListener('click', (e) => {
            createRipple(e, btn);
            switchTab(btn.dataset.tab);
        });
    });
    
    // Close results
    el.closeResults?.addEventListener('click', closeResultsPanel);
    
    // SQL toggle
    el.sqlToggle?.addEventListener('click', toggleSQL);
    
    // Export & Share
    el.exportBtn?.addEventListener('click', showExportOptions);
    el.shareBtn?.addEventListener('click', showShareModal);
    
    // Fullscreen
    el.fullscreenMap?.addEventListener('click', toggleFullscreen);
    
    // History
    el.historyToggle?.addEventListener('click', toggleHistory);
    el.clearHistory?.addEventListener('click', clearHistory);
    
    // Chart controls
    el.chartTypeSelect?.addEventListener('change', handleChartTypeChange);
    el.chartXAxis?.addEventListener('change', updateChartFromControls);
    el.chartYAxis?.addEventListener('change', updateChartFromControls);
    
    // Window events
    window.addEventListener('resize', debounce(handleResize, 150));
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    // Share modal
    el.shareModal?.addEventListener('click', handleShareModalClick);
    $$('.share-option').forEach(btn => {
        btn.addEventListener('click', () => handleShareOption(btn.dataset.type));
    });
    
    // PWA prompt
    initPWAPromptListeners();
    
    // Initial responsive check
    handleResize();
}

// ========================================
// Keyboard Shortcuts
// ========================================
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Check if we're in an input field (except for global shortcuts)
        const isInputActive = document.activeElement.tagName === 'INPUT' || 
                              document.activeElement.tagName === 'TEXTAREA';
        
        // Handle ? key for shortcuts help (when not in input)
        if (e.key === '?' && !isInputActive) {
            e.preventDefault();
            toggleShortcutsModal();
            return;
        }
        
        const key = [];
        if (e.ctrlKey || e.metaKey) key.push('Ctrl');
        if (e.shiftKey) key.push('Shift');
        if (e.altKey) key.push('Alt');
        key.push(e.key === ' ' ? 'Space' : e.key);
        
        const shortcut = key.join('+');
        const action = SHORTCUTS[shortcut];
        
        if (action) {
            e.preventDefault();
            executeShortcut(action);
        }
        
        // Handle Ctrl+K for command palette
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            toggleCommandPalette();
        }
        
        // Handle Ctrl+Shift+D for dashboard
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
            e.preventDefault();
            window.location.href = '/dashboard';
        }
    });
}

function executeShortcut(action) {
    switch (action) {
        case 'sendQuery':
            if (el.queryInput?.value.trim()) sendQuery();
            break;
        case 'focusInput':
            el.queryInput?.focus();
            break;
        case 'toggleSuggestions':
            state.showSuggestions ? hideSuggestions() : showSuggestions();
            break;
        case 'toggleTheme':
            toggleTheme();
            break;
        case 'exportData':
            if (state.currentData.length) showExportOptions();
            break;
        case 'toggleMap':
            toggleFullscreen();
            break;
        case 'closeModals':
            closeAllModals();
            break;
    }
}

// ========================================
// Command Palette
// ========================================
const COMMANDS = [
    { id: 'query-temp', icon: '🌡️', title: 'Temperature Query', description: 'Search for temperature data', action: () => { el.queryInput.value = 'average temperature in '; el.queryInput.focus(); } },
    { id: 'query-sal', icon: '🧪', title: 'Salinity Query', description: 'Search for salinity data', action: () => { el.queryInput.value = 'salinity in '; el.queryInput.focus(); } },
    { id: 'query-float', icon: '📍', title: 'Find Float', description: 'Search for a specific float', action: () => { el.queryInput.value = 'trajectory of float '; el.queryInput.focus(); } },
    { id: 'toggle-theme', icon: '🎨', title: 'Toggle Theme', description: 'Switch between dark and light mode', shortcut: ['Ctrl', 'D'], action: toggleTheme },
    { id: 'open-dashboard', icon: '📊', title: 'Open Dashboard', description: 'View analytics dashboard', shortcut: ['Ctrl', 'Shift', 'D'], action: () => window.location.href = '/dashboard' },
    { id: 'open-map', icon: '🗺️', title: 'Interactive Map', description: 'Open full map explorer', action: () => window.location.href = '/map' },
    { id: 'export-csv', icon: '📄', title: 'Export CSV', description: 'Export current data as CSV', shortcut: ['Ctrl', 'E'], action: () => exportData('csv') },
    { id: 'export-json', icon: '📋', title: 'Export JSON', description: 'Export current data as JSON', action: () => exportData('json') },
    { id: 'clear-history', icon: '🗑️', title: 'Clear History', description: 'Clear all query history', action: clearHistory },
    { id: 'fullscreen', icon: '⛶', title: 'Fullscreen Map', description: 'Toggle fullscreen mode', shortcut: ['Ctrl', 'M'], action: toggleFullscreen },
    { id: 'help', icon: '❓', title: 'Keyboard Shortcuts', description: 'View all keyboard shortcuts', shortcut: ['?'], action: toggleShortcutsModal },
];

let commandPaletteSelectedIndex = 0;
let filteredCommands = [...COMMANDS];

function toggleCommandPalette() {
    const overlay = document.getElementById('commandPaletteOverlay');
    const palette = document.getElementById('commandPalette');
    
    if (!overlay || !palette) return;
    
    const isVisible = !palette.classList.contains('hidden');
    
    if (isVisible) {
        closeCommandPalette();
    } else {
        openCommandPalette();
    }
}

function openCommandPalette() {
    const overlay = document.getElementById('commandPaletteOverlay');
    const palette = document.getElementById('commandPalette');
    const input = document.getElementById('commandInput');
    
    overlay?.classList.remove('hidden');
    palette?.classList.remove('hidden');
    
    filteredCommands = [...COMMANDS];
    commandPaletteSelectedIndex = 0;
    renderCommandResults();
    
    if (input) {
        input.value = '';
        input.focus();
        input.addEventListener('input', handleCommandInput);
        input.addEventListener('keydown', handleCommandKeydown);
    }
    
    overlay?.addEventListener('click', closeCommandPalette);
}

function closeCommandPalette() {
    const overlay = document.getElementById('commandPaletteOverlay');
    const palette = document.getElementById('commandPalette');
    
    overlay?.classList.add('hidden');
    palette?.classList.add('hidden');
}

function handleCommandInput(e) {
    const query = e.target.value.toLowerCase().trim();
    
    if (query === '') {
        filteredCommands = [...COMMANDS];
    } else {
        filteredCommands = COMMANDS.filter(cmd => 
            cmd.title.toLowerCase().includes(query) ||
            cmd.description.toLowerCase().includes(query)
        );
    }
    
    commandPaletteSelectedIndex = 0;
    renderCommandResults();
}

function handleCommandKeydown(e) {
    if (e.key === 'ArrowDown') {
        e.preventDefault();
        commandPaletteSelectedIndex = Math.min(commandPaletteSelectedIndex + 1, filteredCommands.length - 1);
        renderCommandResults();
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        commandPaletteSelectedIndex = Math.max(commandPaletteSelectedIndex - 1, 0);
        renderCommandResults();
    } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredCommands[commandPaletteSelectedIndex]) {
            executeCommand(filteredCommands[commandPaletteSelectedIndex]);
        }
    } else if (e.key === 'Escape') {
        closeCommandPalette();
    }
}

function renderCommandResults() {
    const container = document.getElementById('commandResults');
    if (!container) return;
    
    if (filteredCommands.length === 0) {
        container.innerHTML = '<div class="command-item" style="opacity: 0.5; pointer-events: none;"><span>No commands found</span></div>';
        return;
    }
    
    container.innerHTML = filteredCommands.map((cmd, index) => `
        <div class="command-item ${index === commandPaletteSelectedIndex ? 'selected' : ''}" data-index="${index}">
            <div class="command-item-icon">${cmd.icon}</div>
            <div class="command-item-content">
                <div class="command-item-title">${cmd.title}</div>
                <div class="command-item-description">${cmd.description}</div>
            </div>
            ${cmd.shortcut ? `<div class="command-item-shortcut">${cmd.shortcut.map(k => `<kbd>${k}</kbd>`).join('')}</div>` : ''}
        </div>
    `).join('');
    
    // Add click handlers
    container.querySelectorAll('.command-item').forEach(item => {
        item.addEventListener('click', () => {
            const index = parseInt(item.dataset.index);
            if (filteredCommands[index]) {
                executeCommand(filteredCommands[index]);
            }
        });
    });
}

function executeCommand(cmd) {
    closeCommandPalette();
    if (cmd.action) {
        setTimeout(cmd.action, 100);
    }
}

// ========================================
// Shortcuts Modal
// ========================================
function toggleShortcutsModal() {
    const modal = document.getElementById('shortcutsModal');
    if (!modal) return;
    
    modal.classList.toggle('hidden');
}

// Initialize shortcuts modal handlers once
function initShortcutsModal() {
    const modal = document.getElementById('shortcutsModal');
    const closeBtn = document.getElementById('closeShortcutsModal');
    
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal?.classList.add('hidden');
        });
    }
    
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    }
}

// ========================================
// Input Handlers
// ========================================
function handleInputKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!state.isLoading) {
            sendQuery();
        }
    } else if (e.key === 'ArrowDown' && state.showSuggestions) {
        e.preventDefault();
        focusNextSuggestion();
    } else if (e.key === 'ArrowUp' && state.showSuggestions) {
        e.preventDefault();
        focusPrevSuggestion();
    } else if (e.key === 'Escape') {
        hideSuggestions();
    }
}

function handleInputFocus() {
    if (el.queryInput.value.length === 0) {
        showSuggestions();
    }
}

function handleInputChange() {
    autoResizeInput();
    filterSuggestions(el.queryInput.value);
}

function autoResizeInput() {
    if (!el.queryInput) return;
    el.queryInput.style.height = 'auto';
    el.queryInput.style.height = Math.min(el.queryInput.scrollHeight, 120) + 'px';
}

// ========================================
// Voice Recognition (Enhanced with Waveform)
// ========================================
function initVoiceRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.log('Voice recognition not supported');
        el.voiceBtn?.style.setProperty('display', 'none');
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    state.recognition = new SpeechRecognition();
    state.recognition.continuous = false;
    state.recognition.interimResults = true;
    state.recognition.lang = 'en-US';
    
    state.recognition.onstart = handleVoiceStart;
    state.recognition.onresult = handleVoiceResult;
    state.recognition.onend = handleVoiceEnd;
    state.recognition.onerror = handleVoiceError;
}

function toggleVoiceInput() {
    if (!state.recognition) {
        showToast('Not Supported', 'Voice input is not supported in this browser', 'warning');
        return;
    }
    
    if (state.isVoiceActive) {
        state.recognition.stop();
    } else {
        state.recognition.start();
    }
}

function handleVoiceStart() {
    state.isVoiceActive = true;
    el.voiceBtn?.classList.add('active', 'listening');
    el.queryInput.placeholder = '🎤 Listening... Speak now';
    el.queryInput.classList.add('voice-active');
    
    // Haptic feedback
    if (navigator.vibrate) {
        navigator.vibrate([50, 30, 50]);
    }
}

function handleVoiceResult(event) {
    let finalTranscript = '';
    let interimTranscript = '';
    
    for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
            finalTranscript += transcript;
        } else {
            interimTranscript += transcript;
        }
    }
    
    el.queryInput.value = finalTranscript || interimTranscript;
    autoResizeInput();
}

function handleVoiceEnd() {
    state.isVoiceActive = false;
    el.voiceBtn?.classList.remove('active', 'listening');
    el.queryInput.placeholder = 'Ask about ocean data...';
    el.queryInput.classList.remove('voice-active');
    
    if (el.queryInput.value.trim().length > 0) {
        setTimeout(sendQuery, 500);
    }
}

function handleVoiceError(event) {
    console.error('Voice recognition error:', event.error);
    state.isVoiceActive = false;
    el.voiceBtn?.classList.remove('active', 'listening');
    
    const messages = {
        'not-allowed': 'Microphone access denied. Please enable it in settings.',
        'no-speech': 'No speech detected. Please try again.',
        'network': 'Network error. Check your connection.',
        'aborted': 'Voice input cancelled.'
    };
    
    if (event.error !== 'aborted') {
        showToast('Voice Error', messages[event.error] || 'Could not recognize speech', 'error');
    }
}

// ========================================
// Suggestions System (Enhanced with Fuzzy Search)
// ========================================
function initSuggestions() {
    if (!el.suggestionsDropdown) return;
    
    el.suggestionsDropdown.addEventListener('click', (e) => {
        const item = e.target.closest('.suggestion-item');
        if (item) {
            el.queryInput.value = item.dataset.query;
            hideSuggestions();
            sendQuery();
        }
    });
}

function showSuggestions() {
    if (!el.suggestionsDropdown) return;
    
    state.showSuggestions = true;
    el.suggestionsDropdown.classList.add('show');
    renderSuggestions();
}

function hideSuggestions() {
    if (!el.suggestionsDropdown) return;
    
    state.showSuggestions = false;
    el.suggestionsDropdown.classList.remove('show');
}

function filterSuggestions(query) {
    if (!query || query.length === 0) {
        if (document.activeElement === el.queryInput) {
            showSuggestions();
        }
        return;
    }
    
    const lowerQuery = query.toLowerCase();
    const filteredSuggestions = {};
    
    Object.entries(QUERY_SUGGESTIONS).forEach(([category, suggestions]) => {
        const filtered = suggestions.filter(s => 
            fuzzyMatch(s.toLowerCase(), lowerQuery)
        );
        if (filtered.length > 0) {
            filteredSuggestions[category] = filtered;
        }
    });
    
    if (Object.keys(filteredSuggestions).length > 0) {
        renderSuggestions(filteredSuggestions);
        el.suggestionsDropdown.classList.add('show');
    } else {
        hideSuggestions();
    }
}

function fuzzyMatch(str, pattern) {
    // Simple fuzzy matching
    let patternIdx = 0;
    for (let i = 0; i < str.length && patternIdx < pattern.length; i++) {
        if (str[i] === pattern[patternIdx]) {
            patternIdx++;
        }
    }
    return patternIdx === pattern.length || str.includes(pattern);
}

function renderSuggestions(suggestions = QUERY_SUGGESTIONS) {
    if (!el.suggestionsDropdown) return;
    
    let html = '';
    
    Object.entries(suggestions).forEach(([category, items]) => {
        html += `<div class="suggestion-category">${category}</div>`;
        items.slice(0, 4).forEach((item, idx) => {
            html += `<div class="suggestion-item" data-query="${escapeHtml(item)}" tabindex="0">${escapeHtml(item)}</div>`;
        });
    });
    
    el.suggestionsDropdown.innerHTML = html;
}

function focusNextSuggestion() {
    const items = el.suggestionsDropdown?.querySelectorAll('.suggestion-item');
    if (!items?.length) return;
    
    const current = el.suggestionsDropdown.querySelector('.suggestion-item:focus');
    const currentIdx = current ? Array.from(items).indexOf(current) : -1;
    const nextIdx = (currentIdx + 1) % items.length;
    items[nextIdx].focus();
}

function focusPrevSuggestion() {
    const items = el.suggestionsDropdown?.querySelectorAll('.suggestion-item');
    if (!items?.length) return;
    
    const current = el.suggestionsDropdown.querySelector('.suggestion-item:focus');
    const currentIdx = current ? Array.from(items).indexOf(current) : 0;
    const prevIdx = (currentIdx - 1 + items.length) % items.length;
    items[prevIdx].focus();
}

// ========================================
// PWA Support (Enhanced)
// ========================================
function initPWA() {
    // Register service worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => {
                console.log('✅ Service Worker registered:', registration.scope);
                
                // Check for updates
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            showToast('Update Available', 'Refresh to get the latest version', 'info');
                        }
                    });
                });
            })
            .catch(error => {
                console.log('❌ Service Worker registration failed:', error);
            });
    }
    
    // Listen for install prompt
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        state.deferredPrompt = e;
        
        // Show install prompt after delay
        setTimeout(() => {
            if (state.deferredPrompt && el.pwaPrompt) {
                el.pwaPrompt.classList.add('show');
            }
        }, 60000); // 1 minute
    });
    
    // Track installation
    window.addEventListener('appinstalled', () => {
        console.log('✅ PWA installed!');
        state.deferredPrompt = null;
        el.pwaPrompt?.classList.remove('show');
        showToast('Installed!', 'FloatChart Pro has been installed', 'success');
    });
}

function initPWAPromptListeners() {
    if (!el.pwaPrompt) return;
    
    const installBtn = el.pwaPrompt.querySelector('.pwa-install-btn');
    const dismissBtn = el.pwaPrompt.querySelector('.pwa-dismiss-btn');
    
    installBtn?.addEventListener('click', installPWA);
    dismissBtn?.addEventListener('click', dismissPWAPrompt);
}

function installPWA() {
    if (!state.deferredPrompt) return;
    
    state.deferredPrompt.prompt();
    state.deferredPrompt.userChoice.then(choice => {
        console.log('PWA install choice:', choice.outcome);
        state.deferredPrompt = null;
    });
}

function dismissPWAPrompt() {
    el.pwaPrompt?.classList.remove('show');
}

// ========================================
// Performance Monitor
// ========================================
function initPerformanceMonitor() {
    // Track page load time
    window.addEventListener('load', () => {
        const timing = performance.timing;
        const loadTime = timing.loadEventEnd - timing.navigationStart;
        console.log(`📊 Page load time: ${loadTime}ms`);
        
        // Update perf stats display
        const perfLoadTime = document.getElementById('perfLoadTime');
        if (perfLoadTime) {
            perfLoadTime.textContent = `${loadTime}ms`;
            if (loadTime > 3000) perfLoadTime.classList.add('danger');
            else if (loadTime > 1500) perfLoadTime.classList.add('warning');
        }
    });
    
    // Monitor FPS
    let lastFrameTime = performance.now();
    let frameCount = 0;
    let fps = 60;
    
    function measureFPS() {
        frameCount++;
        const now = performance.now();
        
        if (now - lastFrameTime >= 1000) {
            fps = Math.round(frameCount * 1000 / (now - lastFrameTime));
            frameCount = 0;
            lastFrameTime = now;
            
            const perfFPS = document.getElementById('perfFPS');
            if (perfFPS) {
                perfFPS.textContent = `${fps}`;
                perfFPS.classList.remove('warning', 'danger');
                if (fps < 30) perfFPS.classList.add('danger');
                else if (fps < 50) perfFPS.classList.add('warning');
            }
        }
        
        requestAnimationFrame(measureFPS);
    }
    
    requestAnimationFrame(measureFPS);
    
    // Monitor memory (if available)
    if (performance.memory) {
        setInterval(() => {
            const perfMemory = document.getElementById('perfMemory');
            if (perfMemory) {
                const used = Math.round(performance.memory.usedJSHeapSize / 1048576);
                perfMemory.textContent = `${used}MB`;
                if (used > 200) perfMemory.classList.add('danger');
                else if (used > 100) perfMemory.classList.add('warning');
            }
        }, 2000);
    }
    
    // Debug mode toggle (Ctrl+Shift+P)
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'P') {
            e.preventDefault();
            const perfStats = document.getElementById('perfStats');
            if (perfStats) {
                perfStats.classList.toggle('hidden');
                showToast('Debug Mode', perfStats.classList.contains('hidden') ? 'Performance stats hidden' : 'Performance stats visible', 'info');
            }
        }
    });
}

// ========================================
// Onboarding Tour
// ========================================
const TOUR_STEPS = [
    {
        target: '.brand',
        title: 'Welcome to FloatChart Pro! 🌊',
        text: 'Your AI-powered ocean intelligence platform for analyzing ARGO float data worldwide.',
        position: 'bottom'
    },
    {
        target: '.input-container',
        title: 'Ask Natural Questions',
        text: 'Type questions like "average temperature in Bay of Bengal" or "find floats near Chennai".',
        position: 'top'
    },
    {
        target: '.quick-actions',
        title: 'Quick Actions',
        text: 'Use these shortcuts for common queries. Click any button to start exploring!',
        position: 'bottom'
    },
    {
        target: '.voice-btn',
        title: 'Voice Input',
        text: 'Click the microphone to speak your query. Works great on mobile!',
        position: 'left'
    },
    {
        target: '.theme-toggle',
        title: 'Theme Toggle',
        text: 'Switch between dark and light modes for comfortable viewing.',
        position: 'bottom'
    }
];

let currentTourStep = 0;

function initOnboardingTour() {
    // Check if user has seen the tour
    const tourCompleted = localStorage.getItem('floatchart_tour_completed');
    if (tourCompleted) return;
    
    // Show notification banner first
    const banner = document.getElementById('notificationBanner');
    if (banner) {
        setTimeout(() => {
            banner.classList.remove('hidden');
            banner.innerHTML = `
                <div class="notification-banner-content">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/><path d="M12 16v-4m0-4h.01"/>
                    </svg>
                    <span>New here? Take a quick tour to learn the basics!</span>
                </div>
                <div class="notification-banner-actions">
                    <button class="notification-btn primary" id="startTourBtn">Start Tour</button>
                    <button class="notification-btn secondary" id="skipTourBtn">×</button>
                </div>
            `;
            
            document.getElementById('startTourBtn')?.addEventListener('click', () => {
                banner.classList.add('hidden');
                startTour();
            });
            
            document.getElementById('skipTourBtn')?.addEventListener('click', () => {
                banner.classList.add('hidden');
                localStorage.setItem('floatchart_tour_completed', 'skipped');
            });
        }, 2000);
    }
}

function startTour() {
    currentTourStep = 0;
    showTourStep(currentTourStep);
}

function showTourStep(stepIndex) {
    const tooltip = document.getElementById('tourTooltip');
    if (!tooltip || stepIndex >= TOUR_STEPS.length) {
        endTour();
        return;
    }
    
    const step = TOUR_STEPS[stepIndex];
    const target = document.querySelector(step.target);
    
    if (!target) {
        // Skip to next step if target not found
        showTourStep(stepIndex + 1);
        return;
    }
    
    // Update tooltip content
    document.getElementById('tourTitle').textContent = step.title;
    document.getElementById('tourText').textContent = step.text;
    document.getElementById('tourProgress').textContent = `${stepIndex + 1} of ${TOUR_STEPS.length}`;
    
    const isLastStep = stepIndex === TOUR_STEPS.length - 1;
    document.getElementById('tourNext').textContent = isLastStep ? 'Finish' : 'Next';
    
    // Position tooltip
    const rect = target.getBoundingClientRect();
    const arrow = tooltip.querySelector('.tour-arrow');
    
    // Remove all position classes
    arrow.className = 'tour-arrow';
    
    tooltip.classList.remove('hidden');
    
    // Position based on step.position
    switch (step.position) {
        case 'bottom':
            tooltip.style.top = (rect.bottom + 15) + 'px';
            tooltip.style.left = (rect.left + rect.width / 2 - 160) + 'px';
            arrow.classList.add('top');
            break;
        case 'top':
            tooltip.style.top = (rect.top - tooltip.offsetHeight - 15) + 'px';
            tooltip.style.left = (rect.left + rect.width / 2 - 160) + 'px';
            arrow.classList.add('bottom');
            break;
        case 'left':
            tooltip.style.top = (rect.top + rect.height / 2 - tooltip.offsetHeight / 2) + 'px';
            tooltip.style.left = (rect.left - tooltip.offsetWidth - 15) + 'px';
            arrow.classList.add('right');
            break;
        case 'right':
            tooltip.style.top = (rect.top + rect.height / 2 - tooltip.offsetHeight / 2) + 'px';
            tooltip.style.left = (rect.right + 15) + 'px';
            arrow.classList.add('left');
            break;
    }
    
    // Highlight target
    target.style.position = target.style.position || 'relative';
    target.style.zIndex = '10005';
    target.style.boxShadow = '0 0 0 4px var(--accent-primary), 0 0 20px var(--accent-glow)';
    target.style.borderRadius = '8px';
}

// Initialize tour button handlers once
function initTourHandlers() {
    const skipBtn = document.getElementById('tourSkip');
    const nextBtn = document.getElementById('tourNext');
    
    if (skipBtn) {
        skipBtn.addEventListener('click', endTour);
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            // Remove highlight from current target
            const currentStep = TOUR_STEPS[currentTourStep];
            if (currentStep) {
                const target = document.querySelector(currentStep.target);
                if (target) {
                    target.style.zIndex = '';
                    target.style.boxShadow = '';
                }
            }
            
            currentTourStep++;
            showTourStep(currentTourStep);
        });
    }
}

function endTour() {
    const tooltip = document.getElementById('tourTooltip');
    tooltip?.classList.add('hidden');
    
    // Remove any highlights
    TOUR_STEPS.forEach(step => {
        const target = document.querySelector(step.target);
        if (target) {
            target.style.zIndex = '';
            target.style.boxShadow = '';
        }
    });
    
    localStorage.setItem('floatchart_tour_completed', 'true');
    showToast('Tour Complete!', 'Press ? anytime to see keyboard shortcuts', 'success');
}

// ========================================
// API Functions (Enhanced with Streaming)
// ========================================
async function checkStatus() {
    try {
        const res = await fetch(`${CONFIG.API_BASE}/api/status`);
        const data = await res.json();
        
        const dot = el.statusIndicator?.querySelector('.status-dot');
        const text = el.statusIndicator?.querySelector('.status-text');
        
        if (data.status === 'online' && data.database === 'connected') {
            dot?.classList.add('online');
            if (text) text.textContent = 'Connected';
            
            if (data.data_range && el.dataRangeInfo) {
                const { start, end } = data.data_range;
                const records = data.records?.toLocaleString() || '0';
                const floats = data.unique_floats?.toLocaleString() || '0';
                
                el.dataRangeInfo.innerHTML = `
                    <div class="data-range-main">📅 <strong>${start}</strong> to <strong>${end}</strong></div>
                    <div class="data-range-stats">🌊 ${records} records • ${floats} ARGO floats</div>
                    <div class="data-range-note">🔍 Indian Ocean, Bay of Bengal, Arabian Sea & more</div>
                `;
            }
        } else {
            dot?.classList.remove('online');
            if (text) text.textContent = 'Disconnected';
        }
    } catch (e) {
        console.error('Status check failed:', e);
        const text = el.statusIndicator?.querySelector('.status-text');
        if (text) text.textContent = 'Offline';
    }
}

async function sendQuery() {
    const question = el.queryInput?.value.trim();
    if (!question || state.isLoading) return;
    
    hideSuggestions();
    addMessage(question, 'user');
    el.queryInput.value = '';
    el.queryInput.style.height = 'auto';
    addToHistory(question);
    
    state.conversationHistory.push({ role: 'user', content: question });
    setLoading(true);
    
    const startTime = performance.now();
    
    if (CONFIG.STREAM_ENABLED) {
        await sendQueryStreaming(question);
    } else {
        await sendQueryNormal(question);
    }
    
    state.lastQueryTime = performance.now() - startTime;
    state.queryCount++;
    
    console.log(`⏱️ Query processed in ${state.lastQueryTime.toFixed(0)}ms`);
}

async function sendQueryStreaming(question) {
    const typingId = addTypingIndicator();
    let fullSummary = '';
    let messageEl = null;
    
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/query/stream?question=${encodeURIComponent(question)}`);
        
        if (!response.ok) {
            throw new Error('Stream request failed');
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        state.isStreaming = true;
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        switch (data.type) {
                            case 'start':
                                removeTypingIndicator(typingId);
                                messageEl = createStreamingMessage();
                                break;
                                
                            case 'chunk':
                                if (messageEl) {
                                    fullSummary += data.content;
                                    updateStreamingMessage(messageEl, fullSummary);
                                }
                                break;
                                
                            case 'data':
                                displayResults({
                                    query_type: data.query_type || 'General',
                                    data: data.data,
                                    summary: fullSummary,
                                    sql_query: data.sql_query
                                });
                                break;
                                
                            case 'done':
                                finalizeStreamingMessage(messageEl, fullSummary);
                                state.conversationHistory.push({ role: 'assistant', content: fullSummary });
                                if (state.conversationHistory.length > CONFIG.MAX_CONVERSATION) {
                                    state.conversationHistory = state.conversationHistory.slice(-CONFIG.MAX_CONVERSATION);
                                }
                                saveConversation();
                                break;
                                
                            case 'error':
                                removeTypingIndicator(typingId);
                                addMessage(`Error: ${data.message}`, 'assistant');
                                showToast('Error', data.message, 'error');
                                break;
                        }
                    } catch (parseError) {
                        // Ignore parse errors for partial data
                    }
                }
            }
        }
        
    } catch (e) {
        console.error('Streaming error:', e);
        removeTypingIndicator(typingId);
        // Fall back to normal query
        await sendQueryNormal(question);
    } finally {
        state.isStreaming = false;
        setLoading(false);
    }
}

async function sendQueryNormal(question) {
    const typingId = addTypingIndicator();
    
    try {
        const params = new URLSearchParams({ question });
        const res = await fetch(`${CONFIG.API_BASE}/api/query?${params}`);
        const result = await res.json();
        
        removeTypingIndicator(typingId);
        
        const summary = result.summary || 'Query completed';
        addMessage(summary, 'assistant');
        
        state.conversationHistory.push({ role: 'assistant', content: summary });
        if (state.conversationHistory.length > CONFIG.MAX_CONVERSATION) {
            state.conversationHistory = state.conversationHistory.slice(-CONFIG.MAX_CONVERSATION);
        }
        saveConversation();
        
        displayResults(result);
        
        if (result.data?.length > 0) {
            showToast('Success', `Found ${result.data.length} records`, 'success');
        } else {
            showToast('No Data', result.data_range || 'No records found', 'warning');
        }
        
    } catch (e) {
        console.error('Query failed:', e);
        removeTypingIndicator(typingId);
        addMessage('Sorry, an error occurred. Please try again.', 'assistant');
        showToast('Error', 'Query failed', 'error');
    } finally {
        setLoading(false);
    }
}

// ========================================
// Streaming Message Helpers
// ========================================
function createStreamingMessage() {
    const msg = document.createElement('div');
    msg.className = 'message assistant streaming';
    msg.innerHTML = `
        <div class="message-content"></div>
        <span class="message-time">${formatTime()}</span>
    `;
    el.chatMessages?.appendChild(msg);
    el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
    return msg;
}

function updateStreamingMessage(msgEl, content) {
    const contentEl = msgEl.querySelector('.message-content');
    if (contentEl) {
        contentEl.innerHTML = formatMarkdown(content) + '<span class="cursor">▋</span>';
        el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
    }
}

function finalizeStreamingMessage(msgEl, content) {
    if (!msgEl) return;
    msgEl.classList.remove('streaming');
    const contentEl = msgEl.querySelector('.message-content');
    if (contentEl) {
        contentEl.innerHTML = formatMarkdown(content);
    }
}

// ========================================
// Display Functions (Enhanced)
// ========================================
function displayResults(result) {
    const { query_type, data, summary, sql_query, data_range } = result;
    state.currentData = data || [];
    state.currentQueryType = query_type;
    
    updateMap(data, query_type);
    
    // Show results panel with animation
    if (el.resultsPanel) {
        el.resultsPanel.classList.remove('hidden');
        el.resultsPanel.style.animation = 'slideUp 0.3s ease';
    }
    
    // Update summary
    if (el.summaryContent) {
        let summaryHtml = `<div class="summary-text">${formatMarkdown(summary || 'Query completed')}</div>`;
        if (data_range) {
            summaryHtml += `<p class="data-range-note">📅 ${data_range}</p>`;
        }
        el.summaryContent.innerHTML = summaryHtml;
    }
    
    updateStats(data, query_type);
    
    if (sql_query && el.sqlCode) {
        el.sqlCode.textContent = sql_query;
    }
    
    populateChartAxes(data);
    updateChart(data, query_type);
    updateTable(data);
    switchTab('summary');
}

function formatMarkdown(text) {
    if (!text) return '';
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/^(.*)$/gm, '<p>$1</p>');
}

function populateChartAxes(data) {
    if (!data || data.length === 0) return;
    
    const numericCols = Object.keys(data[0]).filter(k => 
        typeof data[0][k] === 'number' && !k.includes('id')
    );
    
    const allCols = ['auto', ...numericCols];
    
    const options = allCols.map(c => 
        `<option value="${c}">${c === 'auto' ? '🔄 Auto' : capitalizeFirst(c.replace('_', ' '))}</option>`
    ).join('');
    
    if (el.chartXAxis) el.chartXAxis.innerHTML = options;
    if (el.chartYAxis) el.chartYAxis.innerHTML = options;
}

function updateStats(data, queryType) {
    if (!el.statsGrid) return;
    
    if (!data || data.length === 0) {
        el.statsGrid.innerHTML = `
            <div class="stat-card empty">
                <div class="stat-icon">📭</div>
                <div class="stat-label">No Data</div>
                <div class="stat-value">—</div>
            </div>`;
        return;
    }
    
    const stats = [];
    
    // Records
    stats.push({ 
        label: 'Records', 
        value: data.length.toLocaleString(), 
        icon: '📊',
        color: 'blue',
        trend: state.currentData.length > 100 ? 'Large dataset' : 'Standard'
    });
    
    // Floats
    const floatIds = [...new Set(data.map(d => d.float_id).filter(Boolean))];
    if (floatIds.length > 0) {
        stats.push({ 
            label: 'Unique Floats', 
            value: floatIds.length.toLocaleString(), 
            icon: '🔵',
            color: 'cyan'
        });
    }
    
    // Temperature
    const temps = data.filter(d => d.temperature != null).map(d => d.temperature);
    if (temps.length > 0) {
        const avg = temps.reduce((a, b) => a + b, 0) / temps.length;
        const min = Math.min(...temps);
        const max = Math.max(...temps);
        stats.push({ 
            label: 'Temperature', 
            value: `${avg.toFixed(1)}°C`, 
            subtext: `Range: ${min.toFixed(1)} - ${max.toFixed(1)}°C`,
            icon: '🌡️',
            color: avg > 25 ? 'red' : 'blue'
        });
    }
    
    // Salinity
    const sals = data.filter(d => d.salinity != null).map(d => d.salinity);
    if (sals.length > 0) {
        const avg = sals.reduce((a, b) => a + b, 0) / sals.length;
        stats.push({ 
            label: 'Salinity', 
            value: `${avg.toFixed(2)} PSU`, 
            icon: '🧪',
            color: 'purple'
        });
    }
    
    // Distance
    const distances = data.filter(d => d.distance_km != null).map(d => d.distance_km);
    if (distances.length > 0) {
        const min = Math.min(...distances);
        const max = Math.max(...distances);
        stats.push({ 
            label: 'Distance', 
            value: `${min.toFixed(0)} - ${max.toFixed(0)} km`, 
            icon: '📍',
            color: 'green'
        });
    }
    
    // Depth
    const pressures = data.filter(d => d.pressure != null).map(d => d.pressure);
    if (pressures.length > 0 && queryType === 'Profile') {
        stats.push({ 
            label: 'Max Depth', 
            value: `${Math.max(...pressures).toFixed(0)} dbar`, 
            icon: '⬇️',
            color: 'blue'
        });
    }
    
    // Time period
    const timestamps = data.filter(d => d.timestamp).map(d => new Date(d.timestamp));
    if (timestamps.length > 1) {
        const min = new Date(Math.min(...timestamps));
        const max = new Date(Math.max(...timestamps));
        stats.push({ 
            label: 'Period', 
            value: `${formatShortDate(min)} - ${formatShortDate(max)}`,
            icon: '📅',
            color: 'cyan'
        });
    }
    
    el.statsGrid.innerHTML = stats.map(s => `
        <div class="stat-card" data-color="${s.color || 'blue'}">
            <div class="stat-icon">${s.icon}</div>
            <div class="stat-label">${s.label}</div>
            <div class="stat-value">${s.value}</div>
            ${s.subtext ? `<div class="stat-subtext">${s.subtext}</div>` : ''}
        </div>
    `).join('');
}

// ========================================
// Map Visualization (Enhanced)
// ========================================
function updateMap(data, queryType) {
    if (!state.map) return;
    
    // Clear existing
    state.markers.forEach(m => m.remove());
    state.polylines.forEach(p => p.remove());
    state.markers = [];
    state.polylines = [];
    
    if (!data || data.length === 0) {
        state.map.setView(CONFIG.MAP_DEFAULT_CENTER, CONFIG.MAP_DEFAULT_ZOOM);
        return;
    }
    
    const bounds = L.latLngBounds();
    
    if (queryType === 'Trajectory') {
        renderTrajectory(data, bounds);
    } else {
        renderFloatMarkers(data, bounds);
    }
    
    if (bounds.isValid()) {
        state.map.fitBounds(bounds, { padding: [50, 50], maxZoom: 10 });
    }
}

function renderTrajectory(data, bounds) {
    const sorted = [...data].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    const path = sorted.map(d => [d.latitude, d.longitude]);
    
    if (path.length === 0) return;
    
    // Gradient polyline
    const polyline = L.polyline(path, {
        color: '#3b82f6',
        weight: 4,
        opacity: 0.9,
        smoothFactor: 1.5,
        lineCap: 'round',
        lineJoin: 'round'
    }).addTo(state.map);
    state.polylines.push(polyline);
    
    // Start marker
    const startMarker = createEnhancedMarker(
        path[0], 
        '#22c55e', 
        12, 
        createPopup('🟢 Start', sorted[0])
    );
    state.markers.push(startMarker);
    
    // End marker
    if (path.length > 1) {
        const endMarker = createEnhancedMarker(
            path[path.length - 1], 
            '#ef4444', 
            12, 
            createPopup('🔴 End', sorted[sorted.length - 1])
        );
        state.markers.push(endMarker);
    }
    
    path.forEach(p => bounds.extend(p));
}

function renderFloatMarkers(data, bounds) {
    const floatGroups = {};
    data.forEach(d => {
        if (d.latitude && d.longitude) {
            const key = d.float_id || 'unknown';
            if (!floatGroups[key]) floatGroups[key] = [];
            floatGroups[key].push(d);
        }
    });
    
    const hasDistance = data.some(d => d.distance_km != null);
    const distances = hasDistance ? data.filter(d => d.distance_km != null).map(d => d.distance_km) : [];
    const minDist = distances.length ? Math.min(...distances) : 0;
    const maxDist = distances.length ? Math.max(...distances) : 1;
    
    Object.entries(floatGroups).forEach(([floatId, points]) => {
        const latest = points[points.length - 1];
        
        let fillColor = '#3b82f6';
        if (hasDistance && latest.distance_km != null) {
            const ratio = (latest.distance_km - minDist) / (maxDist - minDist + 0.1);
            fillColor = ratio < 0.3 ? '#22c55e' : ratio < 0.6 ? '#f59e0b' : '#ef4444';
        }
        
        const marker = createEnhancedMarker(
            [latest.latitude, latest.longitude],
            fillColor,
            8,
            createPopup(`🔵 Float ${floatId}`, latest)
        );
        
        state.markers.push(marker);
        bounds.extend([latest.latitude, latest.longitude]);
    });
}

function createEnhancedMarker(coords, color, radius, popupContent) {
    const marker = L.circleMarker(coords, {
        radius: radius,
        fillColor: color,
        fillOpacity: 0.9,
        color: 'white',
        weight: 2,
        className: 'animated-marker'
    }).addTo(state.map);
    
    marker.bindPopup(popupContent, {
        className: 'custom-popup',
        maxWidth: 300
    });
    
    // Hover effect
    marker.on('mouseover', function() {
        this.setStyle({ radius: radius * 1.3 });
    });
    marker.on('mouseout', function() {
        this.setStyle({ radius: radius });
    });
    
    return marker;
}

function createPopup(title, data) {
    return `
        <div class="map-popup">
            <div class="popup-title">${title}</div>
            ${data.float_id ? `<div class="popup-row"><span>Float ID:</span><strong>${data.float_id}</strong></div>` : ''}
            <div class="popup-row"><span>Position:</span>${formatCoords(data)}</div>
            ${data.distance_km != null ? `<div class="popup-row"><span>Distance:</span>${data.distance_km.toFixed(1)} km</div>` : ''}
            ${data.timestamp ? `<div class="popup-row"><span>Date:</span>${formatDate(data.timestamp)}</div>` : ''}
            ${data.temperature != null ? `<div class="popup-row"><span>Temp:</span>${data.temperature.toFixed(1)}°C</div>` : ''}
            ${data.salinity != null ? `<div class="popup-row"><span>Salinity:</span>${data.salinity.toFixed(2)} PSU</div>` : ''}
        </div>
    `;
}

// ========================================
// Chart Visualization (Enhanced)
// ========================================
function handleChartTypeChange() {
    updateChart(state.currentData, state.currentQueryType);
}

function updateChartFromControls() {
    updateChart(state.currentData, state.currentQueryType);
}

function updateChart(data, queryType) {
    if (state.chart) {
        state.chart.destroy();
        state.chart = null;
    }
    
    if (!data || data.length === 0 || !el.dataChart) return;
    
    const ctx = el.dataChart.getContext('2d');
    const chartType = el.chartTypeSelect?.value || 'auto';
    const xAxis = el.chartXAxis?.value || 'auto';
    const yAxis = el.chartYAxis?.value || 'auto';
    
    let config;
    
    switch (chartType) {
        case 'ts-diagram':
            config = createTSDiagram(data);
            break;
        case 'histogram':
            config = createHistogram(data, yAxis !== 'auto' ? yAxis : 'temperature');
            break;
        case 'scatter':
            config = createScatterPlot(data, xAxis !== 'auto' ? xAxis : 'longitude', yAxis !== 'auto' ? yAxis : 'latitude');
            break;
        case 'profile':
            config = createProfileChart(data);
            break;
        case 'timeseries':
            config = createTimeSeriesChart(data, yAxis !== 'auto' ? yAxis : 'temperature');
            break;
        default:
            config = createAutoChart(data, queryType);
    }
    
    if (config) {
        applyChartTheme(config);
        state.chart = new Chart(ctx, config);
    }
}

function applyChartTheme(config) {
    const isDark = state.currentTheme === 'dark';
    const textColor = isDark ? '#94a3b8' : '#475569';
    const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
    
    if (config.options?.plugins?.legend?.labels) {
        config.options.plugins.legend.labels.color = textColor;
    }
    
    if (config.options?.plugins?.title) {
        config.options.plugins.title.color = textColor;
    }
    
    if (config.options?.scales) {
        Object.values(config.options.scales).forEach(scale => {
            if (scale.ticks) scale.ticks.color = textColor;
            if (scale.grid) scale.grid.color = gridColor;
            if (scale.title) scale.title.color = textColor;
        });
    }
}

function updateChartTheme() {
    if (state.chart) {
        applyChartTheme(state.chart.config);
        state.chart.update();
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
                    tension: 0.4,
                    yAxisID: 'y',
                    pointRadius: 2,
                    pointHoverRadius: 6
                },
                {
                    label: 'Salinity (PSU)',
                    data: sorted.map(d => d.salinity),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y1',
                    pointRadius: 2,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top', labels: { usePointStyle: true, font: { size: 11 } } },
                tooltip: { backgroundColor: 'rgba(0,0,0,0.8)', padding: 12 }
            },
            scales: {
                x: { title: { display: true, text: 'Pressure (dbar)' } },
                y: { position: 'left', title: { display: true, text: 'Temperature (°C)' } },
                y1: { position: 'right', title: { display: true, text: 'Salinity (PSU)' }, grid: { display: false } }
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
            labels: sorted.map(d => formatShortDate(new Date(d.timestamp))),
            datasets: [{
                label: capitalizeFirst(column.replace('_', ' ')),
                data: sorted.map(d => d[column]),
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 2,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { usePointStyle: true } },
                tooltip: { backgroundColor: 'rgba(0,0,0,0.8)', padding: 12 }
            },
            scales: {
                x: { ticks: { maxTicksLimit: 8 } },
                y: { title: { display: true, text: capitalizeFirst(column) } }
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
                pointRadius: 4,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { usePointStyle: true } },
                title: { display: true, text: 'Temperature-Salinity Diagram', font: { size: 14 } },
                tooltip: { backgroundColor: 'rgba(0,0,0,0.8)', padding: 12 }
            },
            scales: {
                x: { title: { display: true, text: 'Salinity (PSU)' } },
                y: { title: { display: true, text: 'Temperature (°C)' } }
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
                label: `${capitalizeFirst(yCol)} vs ${capitalizeFirst(xCol)}`,
                data: points,
                backgroundColor: 'rgba(34, 197, 94, 0.6)',
                borderColor: '#22c55e',
                pointRadius: 4,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { usePointStyle: true } } },
            scales: {
                x: { title: { display: true, text: xCol } },
                y: { title: { display: true, text: yCol } }
            }
        }
    };
}

function createHistogram(data, column) {
    const values = data.filter(d => d[column] != null).map(d => d[column]);
    if (values.length === 0) return null;
    
    const min = Math.min(...values);
    const max = Math.max(...values);
    const binCount = Math.min(20, Math.ceil(Math.sqrt(values.length)));
    const binSize = (max - min) / binCount || 1;
    
    const bins = Array(binCount).fill(0);
    const labels = [];
    
    for (let i = 0; i < binCount; i++) {
        labels.push((min + i * binSize).toFixed(1));
        
    }
    
    values.forEach(v => {
        const binIdx = Math.min(Math.floor((v - min) / binSize), binCount - 1);
        if (binIdx >= 0) bins[binIdx]++;
    });
    
    return {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: `${capitalizeFirst(column)} Distribution`,
                data: bins,
                backgroundColor: 'rgba(139, 92, 246, 0.7)',
                borderColor: '#8b5cf6',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { usePointStyle: true } } },
            scales: {
                x: { title: { display: true, text: column } },
                y: { title: { display: true, text: 'Frequency' } }
            }
        }
    };
}

function createAutoChart(data, queryType) {
    if (data[0]?.pressure != null && data.length > 5) return createProfileChart(data);
    if (data.some(d => d.timestamp) && data.length > 3) return createTimeSeriesChart(data, 'temperature');
    if (data[0]?.temperature != null && data[0]?.salinity != null) return createTSDiagram(data);
    const numCol = Object.keys(data[0]).find(k => typeof data[0][k] === 'number' && !k.includes('id'));
    return numCol ? createHistogram(data, numCol) : null;
}

// ========================================
// Table Display (Enhanced)
// ========================================
function updateTable(data) {
    if (!el.tableHead || !el.tableBody) return;
    
    if (!data || data.length === 0) {
        el.tableHead.innerHTML = '';
        el.tableBody.innerHTML = '<tr><td colspan="10" class="empty-table">📭 No data available</td></tr>';
        return;
    }
    
    const columns = Object.keys(data[0]).filter(k => !k.startsWith('_'));
    
    // Header
    el.tableHead.innerHTML = '<tr>' + columns.map(c => 
        `<th>${capitalizeFirst(c.replace('_', ' '))}</th>`
    ).join('') + '</tr>';
    
    // Body (virtualized for performance)
    const maxRows = 100;
    const rows = data.slice(0, maxRows);
    
    el.tableBody.innerHTML = rows.map((row, idx) => 
        `<tr class="table-row" style="animation-delay: ${idx * 10}ms">` + 
        columns.map(c => {
            let val = row[c];
            if (val == null) return '<td class="null-value">—</td>';
            if (typeof val === 'number') val = val.toFixed(4);
            if (typeof val === 'string' && val.includes('T')) {
                val = new Date(val).toLocaleString();
            }
            return `<td>${val}</td>`;
        }).join('') + '</tr>'
    ).join('');
    
    if (data.length > maxRows) {
        el.tableBody.innerHTML += `<tr><td colspan="${columns.length}" class="table-more">+ ${data.length - maxRows} more rows...</td></tr>`;
    }
}

function switchTab(tab) {
    [el.summaryTabBtn, el.chartTabBtn, el.tableTabBtn].forEach(btn => {
        btn?.classList.toggle('active', btn?.dataset.tab === tab);
    });
    
    [el.summaryTab, el.chartTab, el.tableTab].forEach(content => {
        content?.classList.toggle('active', content?.id === tab + 'Tab');
    });
}

// ========================================
// Chat Messages (Enhanced)
// ========================================
function addMessage(text, type) {
    const welcome = el.chatMessages?.querySelector('.welcome-msg');
    if (welcome && type === 'user') {
        welcome.style.display = 'none';
    }
    
    const msg = document.createElement('div');
    msg.className = `message ${type}`;
    msg.innerHTML = `
        <div class="message-content">${type === 'assistant' ? formatMarkdown(text) : escapeHtml(text)}</div>
        <span class="message-time">${formatTime()}</span>
    `;
    
    // Animation
    msg.style.opacity = '0';
    msg.style.transform = 'translateY(10px)';
    
    el.chatMessages?.appendChild(msg);
    
    requestAnimationFrame(() => {
        msg.style.transition = 'all 0.3s ease';
        msg.style.opacity = '1';
        msg.style.transform = 'translateY(0)';
    });
    
    el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
}

function addTypingIndicator() {
    const id = 'typing-' + Date.now();
    const indicator = document.createElement('div');
    indicator.id = id;
    indicator.className = 'message assistant typing';
    indicator.innerHTML = `
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>
    `;
    el.chatMessages?.appendChild(indicator);
    el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    document.getElementById(id)?.remove();
}

// ========================================
// History & Settings Management
// ========================================
function loadHistory() {
    try {
        state.history = JSON.parse(localStorage.getItem(CONFIG.HISTORY_KEY)) || [];
        renderHistory();
    } catch (e) {
        state.history = [];
    }
}

function addToHistory(query) {
    state.history = state.history.filter(h => h.query !== query);
    state.history.unshift({ query, time: Date.now() });
    state.history = state.history.slice(0, CONFIG.MAX_HISTORY);
    localStorage.setItem(CONFIG.HISTORY_KEY, JSON.stringify(state.history));
    renderHistory();
}

function renderHistory() {
    if (el.historyCount) {
        el.historyCount.textContent = state.history.length;
    }
    
    if (el.historyList) {
        el.historyList.innerHTML = state.history.map(h => 
            `<div class="history-item" data-query="${escapeHtml(h.query)}">${escapeHtml(h.query)}</div>`
        ).join('');
        
        el.historyList.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', () => {
                el.queryInput.value = item.dataset.query;
                sendQuery();
            });
        });
    }
}

function clearHistory() {
    state.history = [];
    state.conversationHistory = [];
    localStorage.removeItem(CONFIG.HISTORY_KEY);
    localStorage.removeItem(CONFIG.CONVERSATION_KEY);
    renderHistory();
    showToast('Cleared', 'History has been cleared', 'success');
}

function toggleHistory() {
    el.historyList?.classList.toggle('hidden');
    el.clearHistory?.classList.toggle('hidden');
}

function loadConversation() {
    try {
        state.conversationHistory = JSON.parse(localStorage.getItem(CONFIG.CONVERSATION_KEY)) || [];
    } catch (e) {
        state.conversationHistory = [];
    }
}

function saveConversation() {
    localStorage.setItem(CONFIG.CONVERSATION_KEY, JSON.stringify(state.conversationHistory));
}

function loadSettings() {
    try {
        const settings = JSON.parse(localStorage.getItem(CONFIG.SETTINGS_KEY)) || {};
        if (settings.panelWidth) state.panelWidth = settings.panelWidth;
    } catch (e) {}
}

// ========================================
// UI Controls
// ========================================
function toggleChatPanel() {
    const isCollapsed = el.chatPanel?.classList.toggle('collapsed');
    el.panelToggle?.classList.toggle('rotated');
    el.openChatBtn?.classList.toggle('hidden', !isCollapsed);
    setTimeout(() => state.map?.invalidateSize(), CONFIG.ANIMATION_DURATION);
}

function openChatPanel() {
    el.chatPanel?.classList.remove('collapsed');
    el.panelToggle?.classList.remove('rotated');
    el.openChatBtn?.classList.add('hidden');
    setTimeout(() => state.map?.invalidateSize(), CONFIG.ANIMATION_DURATION);
}

function closeResultsPanel() {
    if (el.resultsPanel) {
        el.resultsPanel.style.animation = 'slideDown 0.3s ease';
        setTimeout(() => {
            el.resultsPanel.classList.add('hidden');
        }, 300);
    }
}

function toggleSQL() {
    el.sqlToggle?.classList.toggle('open');
    el.sqlCode?.classList.toggle('hidden');
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        el.mapWrapper?.requestFullscreen();
    } else {
        document.exitFullscreen();
    }
}

function closeAllModals() {
    el.shareModal?.classList.remove('show');
    el.pwaPrompt?.classList.remove('show');
    hideSuggestions();
    closeCommandPalette();
    document.getElementById('shortcutsModal')?.classList.add('hidden');
}

// ========================================
// Resizable Panel
// ========================================
function initResizable() {
    if (!el.resizeHandle) return;
    
    let isResizing = false;
    let startX, startWidth;
    
    el.resizeHandle.addEventListener('mousedown', (e) => {
        isResizing = true;
        startX = e.clientX;
        startWidth = el.chatPanel?.offsetWidth || 400;
        el.resizeHandle.classList.add('dragging');
        document.body.style.cursor = 'ew-resize';
        document.body.style.userSelect = 'none';
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        const diff = startX - e.clientX;
        const newWidth = Math.min(Math.max(startWidth + diff, 320), 600);
        if (el.chatPanel) el.chatPanel.style.width = newWidth + 'px';
        state.panelWidth = newWidth;
    });
    
    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            el.resizeHandle.classList.remove('dragging');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            state.map?.invalidateSize();
            localStorage.setItem(CONFIG.SETTINGS_KEY, JSON.stringify({ panelWidth: state.panelWidth }));
        }
    });
}

function handleResize() {
    const isMobile = window.innerWidth <= 768;
    
    state.map?.invalidateSize();
    
    if (isMobile && el.chatPanel) {
        el.chatPanel.style.width = '';
    } else if (el.chatPanel) {
        el.chatPanel.style.width = state.panelWidth + 'px';
    }
}

// ========================================
// Network Status
// ========================================
function handleOnline() {
    state.isOnline = true;
    showToast('Back Online', 'Connection restored', 'success');
    checkStatus();
}

function handleOffline() {
    state.isOnline = false;
    showToast('Offline', 'You are currently offline', 'warning');
}

// ========================================
// Export & Share (Enhanced)
// ========================================
function showExportOptions() {
    if (!state.currentData.length) {
        showToast('No Data', 'Nothing to export', 'warning');
        return;
    }
    exportAsCSV();
}

function exportAsCSV() {
    const headers = Object.keys(state.currentData[0]);
    const csv = [
        headers.join(','),
        ...state.currentData.map(row => 
            headers.map(h => JSON.stringify(row[h] ?? '')).join(',')
        )
    ].join('\n');
    
    downloadFile(csv, `floatchart_${getDateString()}.csv`, 'text/csv');
    showToast('Exported', `${state.currentData.length} records saved as CSV`, 'success');
}

function exportAsJSON() {
    const json = JSON.stringify(state.currentData, null, 2);
    downloadFile(json, `floatchart_${getDateString()}.json`, 'application/json');
    showToast('Exported', 'Data saved as JSON', 'success');
}

function downloadFile(content, filename, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

function showShareModal() {
    el.shareModal?.classList.add('show');
}

function handleShareModalClick(e) {
    if (e.target === el.shareModal || e.target.classList.contains('modal-close')) {
        el.shareModal?.classList.remove('show');
    }
}

function handleShareOption(type) {
    switch (type) {
        case 'link':
            navigator.clipboard.writeText(window.location.href).then(() => {
                showToast('Copied', 'Link copied to clipboard', 'success');
            });
            break;
        case 'png':
            if (state.chart) {
                const url = state.chart.toBase64Image();
                const a = document.createElement('a');
                a.href = url;
                a.download = `floatchart_${getDateString()}.png`;
                a.click();
                showToast('Exported', 'Chart saved as PNG', 'success');
            }
            break;
        case 'json':
            exportAsJSON();
            break;
        case 'embed':
            const embed = `<iframe src="${window.location.href}" width="800" height="600" frameborder="0"></iframe>`;
            navigator.clipboard.writeText(embed).then(() => {
                showToast('Copied', 'Embed code copied', 'success');
            });
            break;
    }
    el.shareModal?.classList.remove('show');
}

// ========================================
// Utility Functions
// ========================================
function setLoading(loading) {
    state.isLoading = loading;
    el.loadingOverlay?.classList.toggle('hidden', !loading);
    if (el.sendBtn) el.sendBtn.disabled = loading;
}

function showToast(title, message, type = 'info') {
    const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            ${message ? `<div class="toast-message">${message}</div>` : ''}
        </div>
    `;
    
    el.toastContainer?.appendChild(toast);
    
    requestAnimationFrame(() => toast.classList.add('show'));
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, CONFIG.TOAST_DURATION);
}

function createRipple(e, element) {
    const rect = element.getBoundingClientRect();
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.left = (e.clientX - rect.left) + 'px';
    ripple.style.top = (e.clientY - rect.top) + 'px';
    element.appendChild(ripple);
    setTimeout(() => ripple.remove(), 600);
}

function debounce(fn, delay) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), delay);
    };
}

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
    });
}

function formatShortDate(date) {
    return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
}

function formatCoords(data) {
    return `${data.latitude?.toFixed(3)}°N, ${data.longitude?.toFixed(3)}°E`;
}

function getDateString() {
    return new Date().toISOString().split('T')[0];
}

// ========================================
// Error Handling
// ========================================
window.onerror = (msg, url, line, col, error) => {
    console.error('Global error:', { msg, url, line, col, error });
    return false;
};

window.onunhandledrejection = (event) => {
    console.error('Unhandled promise rejection:', event.reason);
};

// ========================================
// Exports
// ========================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { state, CONFIG, sendQuery, updateMap, updateChart };
}

console.log(`🌊 FloatChart Pro v${CONFIG.VERSION} loaded`);

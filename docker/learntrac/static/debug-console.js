// Debug Console JavaScript
let ws = null;
let currentSession = null;
let sessions = new Map();
let eventLog = [];

// Initialize WebSocket connection
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/debug`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('Debug WebSocket connected');
        document.getElementById('ws-status').classList.add('connected');
        requestStats();
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        document.getElementById('ws-status').classList.remove('connected');
        // Attempt to reconnect after 3 seconds
        setTimeout(initWebSocket, 3000);
    };
}

// Handle incoming WebSocket messages
function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'initial_state':
            handleInitialState(data);
            break;
        case 'debug_event':
            handleDebugEvent(data.event);
            break;
        case 'session_events':
            handleSessionEvents(data);
            break;
        case 'stats':
            handleStats(data.data);
            break;
    }
}

// Handle initial state
function handleInitialState(data) {
    data.active_sessions.forEach(sessionId => {
        sessions.set(sessionId, {
            id: sessionId,
            startTime: new Date(),
            events: []
        });
    });
    updateSessionsList();
}

// Handle debug events
function handleDebugEvent(event) {
    // Add to event log
    eventLog.push(event);
    if (eventLog.length > 1000) {
        eventLog = eventLog.slice(-1000);
    }
    
    // Update session data
    if (!sessions.has(event.session_id)) {
        sessions.set(event.session_id, {
            id: event.session_id,
            startTime: new Date(event.timestamp),
            events: []
        });
        updateSessionsList();
    }
    
    const session = sessions.get(event.session_id);
    session.events.push(event);
    
    // Update UI if this is the current session
    if (currentSession === event.session_id) {
        updatePipelineView(event);
        addEventToLog(event);
    }
    
    // Update session count
    document.getElementById('session-count').textContent = 
        `${sessions.size} active sessions`;
}

// Update pipeline visualization based on event
function updatePipelineView(event) {
    const stage = event.stage;
    const data = event.data;
    
    // Reset all stages
    document.querySelectorAll('.stage').forEach(s => {
        s.classList.remove('active', 'error');
    });
    
    // Update specific stage
    switch (stage) {
        case 'audio_capture':
            updateAudioCaptureStage(data);
            break;
        case 'stt_processing':
            updateSTTStage(data);
            break;
        case 'llm_processing':
            updateLLMStage(data);
            break;
        case 'tts_generation':
            updateTTSStage(data);
            break;
    }
    
    // Mark stage as active or error
    const stageElement = document.getElementById(`stage-${stage.replace('_', '-')}`);
    if (stageElement) {
        if (data.action === 'error') {
            stageElement.classList.add('error');
        } else if (data.action.includes('started')) {
            stageElement.classList.add('active');
        } else if (data.action.includes('completed')) {
            stageElement.classList.add('completed');
        }
        
        // Update timestamp
        const timeElement = stageElement.querySelector('.stage-time');
        if (timeElement) {
            timeElement.textContent = new Date(event.timestamp).toLocaleTimeString();
        }
    }
}

// Update Audio Capture stage
function updateAudioCaptureStage(data) {
    if (data.audio_level !== undefined) {
        const level = Math.round(data.audio_level * 100);
        document.getElementById('audio-level').textContent = level;
        updateAudioVisualizer('audio-viz', data.audio_level);
    }
    
    if (data.chunk_number !== undefined) {
        document.getElementById('chunk-count').textContent = data.chunk_number;
    }
}

// Update STT stage
function updateSTTStage(data) {
    if (data.transcription) {
        document.getElementById('transcription').textContent = data.transcription;
        document.getElementById('word-count').textContent = 
            data.transcription.split(' ').length;
    }
    
    if (data.confidence !== undefined) {
        const confidence = Math.round(data.confidence * 100);
        document.getElementById('confidence').style.width = `${confidence}%`;
        document.getElementById('confidence-value').textContent = `${confidence}%`;
    }
    
    if (data.processing_time !== undefined) {
        document.getElementById('stt-time').textContent = 
            `${Math.round(data.processing_time * 1000)}ms`;
    }
}

// Update LLM stage
function updateLLMStage(data) {
    if (data.output_text) {
        document.getElementById('llm-response').textContent = data.output_text;
    }
    
    if (data.tokens_used) {
        document.getElementById('token-count').textContent = data.tokens_used.total;
    }
    
    if (data.processing_time !== undefined) {
        document.getElementById('llm-time').textContent = 
            `${Math.round(data.processing_time * 1000)}ms`;
    }
}

// Update TTS stage
function updateTTSStage(data) {
    if (data.text) {
        document.getElementById('tts-text').textContent = data.text;
    }
    
    if (data.duration !== undefined) {
        document.getElementById('audio-duration').textContent = 
            `${data.duration.toFixed(1)}s`;
    }
    
    if (data.processing_time !== undefined) {
        document.getElementById('tts-time').textContent = 
            `${Math.round(data.processing_time * 1000)}ms`;
    }
    
    if (data.action === 'tts_completed') {
        updateAudioVisualizer('tts-viz', 0.8);
    }
}

// Update audio visualizer
function updateAudioVisualizer(elementId, level) {
    const viz = document.getElementById(elementId);
    if (!viz.children.length) {
        // Create bars
        for (let i = 0; i < 30; i++) {
            const bar = document.createElement('div');
            bar.className = 'audio-bar';
            viz.appendChild(bar);
        }
    }
    
    // Update bars based on level
    const bars = viz.querySelectorAll('.audio-bar');
    bars.forEach((bar, i) => {
        const height = Math.random() * level * 40 + 10;
        bar.style.height = `${height}px`;
    });
}

// Update sessions list
function updateSessionsList() {
    const list = document.getElementById('sessions-list');
    list.innerHTML = '';
    
    sessions.forEach((session, sessionId) => {
        const item = document.createElement('div');
        item.className = 'session-item';
        if (sessionId === currentSession) {
            item.classList.add('active');
        }
        
        const duration = Math.round((Date.now() - session.startTime) / 1000);
        item.innerHTML = `
            <div>Session: ${sessionId.substring(0, 8)}...</div>
            <div style="font-size: 12px; color: #888;">
                Duration: ${duration}s | Events: ${session.events.length}
            </div>
        `;
        
        item.onclick = () => selectSession(sessionId);
        list.appendChild(item);
    });
}

// Select a session
function selectSession(sessionId) {
    currentSession = sessionId;
    updateSessionsList();
    
    // Clear current view
    clearPipelineView();
    document.getElementById('event-log').innerHTML = '';
    
    // Request full session events
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            command: 'get_session_events',
            session_id: sessionId
        }));
    }
}

// Add event to log
function addEventToLog(event) {
    const log = document.getElementById('event-log');
    const entry = document.createElement('div');
    entry.className = 'event-entry';
    
    const time = new Date(event.timestamp).toLocaleTimeString();
    const action = event.data.action || 'unknown';
    
    entry.innerHTML = `
        <span class="timestamp">${time}</span>
        <span class="event-stage">[${event.stage}]</span>
        <span class="event-action">${action}</span>
    `;
    
    log.insertBefore(entry, log.firstChild);
    
    // Limit log entries
    while (log.children.length > 100) {
        log.removeChild(log.lastChild);
    }
}

// Clear pipeline view
function clearPipelineView() {
    document.getElementById('transcription').textContent = '';
    document.getElementById('llm-response').textContent = '';
    document.getElementById('tts-text').textContent = '';
    document.getElementById('confidence').style.width = '0%';
    document.getElementById('confidence-value').textContent = '0%';
    
    // Reset metrics
    document.querySelectorAll('.metric-value').forEach(el => {
        if (el.id !== 'session-count') {
            el.textContent = '0';
        }
    });
}

// Request stats
function requestStats() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ command: 'get_stats' }));
    }
}

// Handle stats
function handleStats(stats) {
    console.log('Stats:', stats);
}

// Clear events
function clearEvents() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ command: 'clear_events' }));
        eventLog = [];
        document.getElementById('event-log').innerHTML = '';
    }
}

// Export logs
function exportLogs() {
    const data = {
        sessions: Array.from(sessions.values()),
        events: eventLog,
        exported: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], 
        { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `debug-logs-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// Disconnect
function disconnect() {
    if (ws) {
        ws.close();
    }
}

// Auto-update sessions list every 5 seconds
setInterval(updateSessionsList, 5000);

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    initWebSocket();
    
    // Create initial audio visualizer bars
    updateAudioVisualizer('audio-viz', 0);
    updateAudioVisualizer('tts-viz', 0);
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (ws) {
        ws.close();
    }
});
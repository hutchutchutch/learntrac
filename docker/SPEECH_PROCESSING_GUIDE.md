# Speech Processing & Debug Console Guide

This guide explains the comprehensive speech processing system with visual debugging capabilities added to LearnTrac.

## Overview

The speech processing system provides:
- **Real-time speech-to-text (STT)** conversion
- **Language model (LLM)** processing 
- **Text-to-speech (TTS)** generation
- **Visual debug console** for monitoring the entire pipeline
- **WebSocket-based** streaming for low latency

## Architecture

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│  Web Client     │ ←---------------→   │  FastAPI Server  │
│  (Browser)      │                     │                  │
└─────────────────┘                     └──────────────────┘
                                               │
                                               ▼
                                        ┌──────────────────┐
                                        │ Speech Pipeline  │
                                        ├──────────────────┤
                                        │ 1. Audio Capture │
                                        │ 2. STT Process   │
                                        │ 3. LLM Process   │
                                        │ 4. TTS Generate  │
                                        │ 5. Audio Output  │
                                        └──────────────────┘
                                               │
                                               ▼
                                        ┌──────────────────┐
                                        │  Debug Console   │
                                        │  (Visual Logs)   │
                                        └──────────────────┘
```

## Components

### 1. Speech Processing Module (`speech_processing.py`)

Core components:
- **SpeechDebugger**: Centralized event logging and subscriber management
- **SpeechProcessor**: Main pipeline orchestrator
- **DebugEvent**: Structured logging events with timestamps and session tracking

Key features:
- Comprehensive event logging at each stage
- Real-time metrics (processing time, confidence, tokens)
- Audio level analysis
- Error tracking and recovery

### 2. WebSocket Handlers (`websocket_handlers.py`)

Two WebSocket endpoints:
- `/ws/audio` - For audio streaming from clients
- `/ws/debug` - For debug console connections

Features:
- Connection management
- Bidirectional communication
- Event broadcasting to debug consoles
- Session tracking

### 3. Visual Debug Console (`debug-console.html`)

Interactive web interface showing:
- **Pipeline visualization** with stage indicators
- **Real-time metrics** for each processing stage
- **Audio level meters** with waveform visualization
- **Event log** with filtering and search
- **Session management** for multiple concurrent streams

### 4. Speech Client Interface (`speech-client.html`)

User-facing interface with:
- **One-click recording** with visual feedback
- **Audio level visualization**
- **Live transcription display**
- **AI response display**
- **Audio playback** of TTS responses

## Usage

### Starting the System

1. **Run the API with speech features:**
```bash
cd docker/learntrac
docker build -t learntrac/api:speech .
docker run -p 8001:8001 learntrac/api:speech
```

2. **Access the interfaces:**
- Speech Client: http://localhost:8001/static/speech-client.html
- Debug Console: http://localhost:8001/debug-console

### Using the Speech Client

1. Open the speech client in your browser
2. Click "Start Recording" (grant microphone permission)
3. Speak your query
4. Click "Stop Recording"
5. View transcription and AI response
6. Click "Play Response" to hear TTS output

### Using the Debug Console

1. Open the debug console in a separate tab
2. Monitor real-time events as you use the speech client
3. Click on sessions to view detailed event logs
4. Use controls to:
   - Clear events
   - Export logs
   - View performance metrics

## Debug Console Features

### Pipeline Stages Visualization

Each stage shows:
- **Status indicator** (idle/active/completed/error)
- **Processing metrics** (time, confidence, tokens)
- **Visual elements** (audio levels, progress bars)
- **Content preview** (transcriptions, responses)

### Event Log

Detailed logging includes:
- Timestamps for each event
- Stage identification
- Action descriptions
- Error tracking
- Performance metrics

### Session Management

- View all active sessions
- Switch between sessions
- See session duration and event count
- Export session data

## Integration with AWS Services

### Speech-to-Text Options

1. **Amazon Transcribe**
```python
# Configure in speech_processing.py
self.stt_config = {
    "provider": "aws_transcribe",
    "language": "en-US",
    "region": "us-east-2"
}
```

2. **Google Speech-to-Text**
```python
self.stt_config = {
    "provider": "google_speech",
    "language": "en-US"
}
```

### Text-to-Speech Options

1. **Amazon Polly**
```python
self.tts_config = {
    "provider": "aws_polly",
    "voice": "Joanna",
    "engine": "neural"
}
```

2. **Google Text-to-Speech**
```python
self.tts_config = {
    "provider": "google_tts",
    "voice": "en-US-Wavenet-D"
}
```

### Language Model Integration

Can integrate with:
- OpenAI GPT models
- AWS Bedrock (Claude, etc.)
- Google Vertex AI
- Local models via Ollama

## Performance Optimization

### Audio Streaming
- Chunk size: 4KB for optimal latency
- Sample rate: 16kHz for quality/bandwidth balance
- Encoding: PCM16 for compatibility

### Processing Pipeline
- Asynchronous processing for non-blocking operation
- Parallel STT/TTS when possible
- Connection pooling for external services
- Caching for repeated queries

### Debug Console
- Event batching to reduce WebSocket traffic
- Automatic log rotation (1000 events max)
- Lazy loading for session data
- Efficient DOM updates

## Monitoring & Debugging

### Key Metrics to Monitor

1. **Audio Quality**
   - Audio level consistency
   - Silence detection
   - Noise levels

2. **STT Performance**
   - Transcription confidence
   - Processing latency
   - Word error rate

3. **LLM Performance**
   - Response time
   - Token usage
   - Relevance scores

4. **TTS Quality**
   - Generation time
   - Audio duration accuracy
   - Voice consistency

### Common Issues & Solutions

1. **No audio input detected**
   - Check microphone permissions
   - Verify audio levels in debug console
   - Test with different browsers

2. **High latency**
   - Check network connection
   - Monitor processing times in debug console
   - Consider chunking strategy

3. **Poor transcription quality**
   - Verify audio quality metrics
   - Check language/accent settings
   - Consider noise reduction

## Security Considerations

1. **Audio Privacy**
   - Audio streams are not stored by default
   - Session data expires after 24 hours
   - Use HTTPS in production

2. **Authentication**
   - Integrate with Cognito for user auth
   - Implement rate limiting
   - Validate audio formats

3. **Data Protection**
   - Encrypt audio in transit
   - Sanitize debug logs
   - Implement access controls

## Next Steps

1. **Production Deployment**
   - Configure real STT/TTS services
   - Set up CloudWatch monitoring
   - Implement auto-scaling

2. **Feature Enhancements**
   - Add voice activity detection
   - Implement noise cancellation
   - Support multiple languages
   - Add conversation history

3. **Integration**
   - Connect to course content
   - Link with user profiles
   - Add to mobile apps
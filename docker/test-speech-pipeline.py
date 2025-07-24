#!/usr/bin/env python3
"""
Test script for speech processing pipeline
Demonstrates the flow through all stages with debug logging
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'learntrac/src'))

from speech_processing import SpeechDebugger, SpeechProcessor, ProcessingStage, DebugEvent
import json
from datetime import datetime

async def simulate_speech_pipeline():
    """Simulate a complete speech processing flow"""
    print("🎤 Speech Processing Pipeline Test")
    print("=" * 50)
    
    # Initialize components
    debugger = SpeechDebugger()
    processor = SpeechProcessor(debugger)
    session_id = "test-session-001"
    
    # Subscribe to debug events
    event_queue = debugger.subscribe()
    
    # Start event printer task
    async def print_events():
        while True:
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                stage = event['stage']
                action = event['data'].get('action', 'unknown')
                print(f"\n[{stage}] {action}")
                
                # Print key data based on stage
                if stage == 'stt_processing' and 'transcription' in event['data']:
                    print(f"  📝 Transcription: {event['data']['transcription']}")
                    print(f"  🎯 Confidence: {event['data']['confidence']:.2%}")
                elif stage == 'llm_processing' and 'output_text' in event['data']:
                    print(f"  🤖 Response: {event['data']['output_text']}")
                    print(f"  📊 Tokens: {event['data']['tokens_used']['total']}")
                elif stage == 'tts_generation' and 'duration' in event['data']:
                    print(f"  🔊 Duration: {event['data']['duration']:.1f}s")
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error: {e}")
                break
    
    event_task = asyncio.create_task(print_events())
    
    print("\n📊 Starting Pipeline Simulation...")
    
    # Stage 1: Audio Capture
    print("\n1️⃣ Audio Capture Stage")
    await debugger.log_event(DebugEvent(
        stage=ProcessingStage.AUDIO_CAPTURE,
        data={
            "action": "stream_started",
            "sample_rate": 16000,
            "encoding": "pcm16"
        },
        session_id=session_id
    ))
    
    # Simulate audio chunks
    for i in range(3):
        await asyncio.sleep(0.5)
        await debugger.log_event(DebugEvent(
            stage=ProcessingStage.AUDIO_CAPTURE,
            data={
                "action": "chunk_received",
                "chunk_number": i + 1,
                "chunk_size": 4096,
                "audio_level": 0.3 + (i * 0.1)
            },
            session_id=session_id
        ))
    
    # Stage 2: STT Processing
    print("\n2️⃣ Speech-to-Text Stage")
    mock_audio = b"mock_audio_data"
    transcription = await processor._process_stt(mock_audio, session_id)
    
    # Stage 3: LLM Processing
    print("\n3️⃣ Language Model Stage")
    if transcription:
        response = await processor._process_llm(transcription, session_id)
        
        # Stage 4: TTS Generation
        print("\n4️⃣ Text-to-Speech Stage")
        audio_output = await processor._generate_tts(response, session_id)
        
        # Stage 5: Audio Output
        print("\n5️⃣ Audio Output Stage")
        await debugger.log_event(DebugEvent(
            stage=ProcessingStage.AUDIO_OUTPUT,
            data={
                "action": "playback_started",
                "size": len(audio_output) if audio_output else 0
            },
            session_id=session_id
        ))
    
    # Wait for events to be printed
    await asyncio.sleep(1)
    
    # Summary
    print("\n" + "=" * 50)
    print("📈 Pipeline Summary:")
    print(f"  Total Events: {len(debugger.events)}")
    print(f"  Session ID: {session_id}")
    print(f"  Active Sessions: {len(debugger.active_sessions)}")
    
    # Get session events
    session_events = debugger.get_session_events(session_id)
    print(f"  Session Events: {len(session_events)}")
    
    # Calculate total processing time
    if session_events:
        start_time = datetime.fromisoformat(session_events[0]['timestamp'])
        end_time = datetime.fromisoformat(session_events[-1]['timestamp'])
        total_time = (end_time - start_time).total_seconds()
        print(f"  Total Time: {total_time:.2f}s")
    
    # Cleanup
    event_task.cancel()
    debugger.unsubscribe(event_queue)
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(simulate_speech_pipeline())
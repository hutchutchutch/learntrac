"""
Speech processing module with comprehensive debugging and visual logging
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class ProcessingStage(Enum):
    """Stages of speech processing pipeline"""
    AUDIO_CAPTURE = "audio_capture"
    STT_PROCESSING = "stt_processing"
    LLM_PROCESSING = "llm_processing"
    TTS_GENERATION = "tts_generation"
    AUDIO_OUTPUT = "audio_output"

class DebugEvent:
    """Debug event for visual console logging"""
    def __init__(self, stage: ProcessingStage, data: Dict[str, Any], 
                 session_id: str, timestamp: Optional[datetime] = None):
        self.id = str(uuid.uuid4())
        self.stage = stage
        self.data = data
        self.session_id = session_id
        self.timestamp = timestamp or datetime.utcnow()
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "stage": self.stage.value,
            "data": self.data,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat()
        }

class SpeechDebugger:
    """Centralized debugger for speech processing pipeline"""
    
    def __init__(self):
        self.events: List[DebugEvent] = []
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.subscribers: List[asyncio.Queue] = []
        
    async def log_event(self, event: DebugEvent):
        """Log a debug event and notify subscribers"""
        self.events.append(event)
        
        # Limit event history
        if len(self.events) > 1000:
            self.events = self.events[-1000:]
            
        # Update session data
        if event.session_id not in self.active_sessions:
            self.active_sessions[event.session_id] = {
                "start_time": event.timestamp,
                "events": []
            }
        self.active_sessions[event.session_id]["events"].append(event.id)
        
        # Notify all subscribers
        event_data = event.to_dict()
        for queue in self.subscribers:
            try:
                await queue.put(event_data)
            except asyncio.QueueFull:
                logger.warning(f"Queue full for subscriber, skipping event {event.id}")
                
    def subscribe(self) -> asyncio.Queue:
        """Subscribe to debug events"""
        queue = asyncio.Queue(maxsize=100)
        self.subscribers.append(queue)
        return queue
        
    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from debug events"""
        if queue in self.subscribers:
            self.subscribers.remove(queue)
            
    def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all events for a session"""
        if session_id not in self.active_sessions:
            return []
            
        event_ids = self.active_sessions[session_id]["events"]
        return [
            event.to_dict() 
            for event in self.events 
            if event.id in event_ids
        ]

class SpeechProcessor:
    """Main speech processing pipeline with debugging"""
    
    def __init__(self, debugger: SpeechDebugger):
        self.debugger = debugger
        self.stt_config = {
            "provider": "aws_transcribe",  # or "google_speech", "azure_speech"
            "language": "en-US",
            "sample_rate": 16000,
            "encoding": "pcm16"
        }
        self.tts_config = {
            "provider": "aws_polly",  # or "google_tts", "azure_tts"
            "voice": "Joanna",
            "language": "en-US",
            "sample_rate": 16000
        }
        
    async def process_audio_stream(self, audio_stream: asyncio.StreamReader, 
                                   session_id: str) -> None:
        """Process incoming audio stream with comprehensive debugging"""
        
        # Log audio capture start
        await self.debugger.log_event(DebugEvent(
            stage=ProcessingStage.AUDIO_CAPTURE,
            data={
                "action": "stream_started",
                "config": self.stt_config,
                "session_info": {
                    "sample_rate": self.stt_config["sample_rate"],
                    "encoding": self.stt_config["encoding"]
                }
            },
            session_id=session_id
        ))
        
        try:
            # Process audio chunks
            chunk_count = 0
            while True:
                chunk = await audio_stream.read(4096)  # Read 4KB chunks
                if not chunk:
                    break
                    
                chunk_count += 1
                
                # Log audio chunk received
                await self.debugger.log_event(DebugEvent(
                    stage=ProcessingStage.AUDIO_CAPTURE,
                    data={
                        "action": "chunk_received",
                        "chunk_number": chunk_count,
                        "chunk_size": len(chunk),
                        "audio_level": self._calculate_audio_level(chunk)
                    },
                    session_id=session_id
                ))
                
                # Process STT
                transcription = await self._process_stt(chunk, session_id)
                
                if transcription:
                    # Process with LLM
                    llm_response = await self._process_llm(transcription, session_id)
                    
                    # Generate TTS
                    audio_output = await self._generate_tts(llm_response, session_id)
                    
                    # Log final output
                    await self.debugger.log_event(DebugEvent(
                        stage=ProcessingStage.AUDIO_OUTPUT,
                        data={
                            "action": "audio_generated",
                            "text": llm_response,
                            "audio_size": len(audio_output) if audio_output else 0,
                            "duration_estimate": self._estimate_duration(llm_response)
                        },
                        session_id=session_id
                    ))
                    
        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
            await self.debugger.log_event(DebugEvent(
                stage=ProcessingStage.AUDIO_CAPTURE,
                data={
                    "action": "error",
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                session_id=session_id
            ))
            
    async def _process_stt(self, audio_chunk: bytes, session_id: str) -> Optional[str]:
        """Process speech-to-text with debugging"""
        start_time = datetime.utcnow()
        
        # Log STT start
        await self.debugger.log_event(DebugEvent(
            stage=ProcessingStage.STT_PROCESSING,
            data={
                "action": "stt_started",
                "provider": self.stt_config["provider"],
                "chunk_size": len(audio_chunk)
            },
            session_id=session_id
        ))
        
        # Simulate STT processing (replace with actual STT service)
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # For demo purposes, return mock transcription
        transcription = "Hello, how can I help you today?"
        confidence = 0.95
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log STT result
        await self.debugger.log_event(DebugEvent(
            stage=ProcessingStage.STT_PROCESSING,
            data={
                "action": "stt_completed",
                "transcription": transcription,
                "confidence": confidence,
                "processing_time": processing_time,
                "alternatives": [
                    {"text": "Hello, how can I help you today?", "confidence": 0.95},
                    {"text": "Hello, how can I help you to day?", "confidence": 0.85}
                ]
            },
            session_id=session_id
        ))
        
        return transcription
        
    async def _process_llm(self, text: str, session_id: str) -> str:
        """Process text with language model with debugging"""
        start_time = datetime.utcnow()
        
        # Log LLM processing start
        await self.debugger.log_event(DebugEvent(
            stage=ProcessingStage.LLM_PROCESSING,
            data={
                "action": "llm_started",
                "input_text": text,
                "input_length": len(text),
                "model": "gpt-4",  # or actual model being used
                "temperature": 0.7,
                "max_tokens": 150
            },
            session_id=session_id
        ))
        
        # Simulate LLM processing (replace with actual LLM call)
        await asyncio.sleep(0.5)
        
        # Mock LLM response
        response = "I'm here to help! What would you like to know about the LearnTrac system?"
        tokens_used = {"prompt": 15, "completion": 20, "total": 35}
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log LLM result
        await self.debugger.log_event(DebugEvent(
            stage=ProcessingStage.LLM_PROCESSING,
            data={
                "action": "llm_completed",
                "output_text": response,
                "output_length": len(response),
                "tokens_used": tokens_used,
                "processing_time": processing_time,
                "finish_reason": "stop"
            },
            session_id=session_id
        ))
        
        return response
        
    async def _generate_tts(self, text: str, session_id: str) -> Optional[bytes]:
        """Generate text-to-speech with debugging"""
        start_time = datetime.utcnow()
        
        # Log TTS generation start
        await self.debugger.log_event(DebugEvent(
            stage=ProcessingStage.TTS_GENERATION,
            data={
                "action": "tts_started",
                "text": text,
                "text_length": len(text),
                "voice": self.tts_config["voice"],
                "provider": self.tts_config["provider"]
            },
            session_id=session_id
        ))
        
        # Simulate TTS generation (replace with actual TTS service)
        await asyncio.sleep(0.3)
        
        # Mock audio data
        audio_data = b"mock_audio_data" * 1000  # Simulate audio bytes
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log TTS result
        await self.debugger.log_event(DebugEvent(
            stage=ProcessingStage.TTS_GENERATION,
            data={
                "action": "tts_completed",
                "audio_size": len(audio_data),
                "duration": self._estimate_duration(text),
                "processing_time": processing_time,
                "audio_format": "pcm16",
                "sample_rate": self.tts_config["sample_rate"]
            },
            session_id=session_id
        ))
        
        return audio_data
        
    def _calculate_audio_level(self, audio_chunk: bytes) -> float:
        """Calculate audio level for visualization"""
        # Simple RMS calculation (implement proper audio level calculation)
        import struct
        if len(audio_chunk) < 2:
            return 0.0
            
        # Assuming 16-bit PCM
        samples = struct.unpack(f"{len(audio_chunk)//2}h", audio_chunk)
        rms = (sum(s**2 for s in samples) / len(samples)) ** 0.5
        return min(1.0, rms / 32768.0)  # Normalize to 0-1
        
    def _estimate_duration(self, text: str) -> float:
        """Estimate speech duration based on text length"""
        # Rough estimate: 150 words per minute
        words = len(text.split())
        return words / 150 * 60  # seconds

# Global debugger instance
speech_debugger = SpeechDebugger()
speech_processor = SpeechProcessor(speech_debugger)
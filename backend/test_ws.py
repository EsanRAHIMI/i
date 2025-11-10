#!/usr/bin/env python3
"""
Minimal WebSocket test server - مستقل از FastAPI اصلی
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "WebSocket Test Server Running", "status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.websocket("/api/v1/voice/stream/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Minimal WebSocket endpoint for testing"""
    await websocket.accept()
    logger.info(f"✅ WebSocket connected: {session_id}")
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "session_started",
            "data": {"session_id": session_id, "message": "Connected successfully!"},
            "timestamp": time.time()
        })
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            logger.info(f"📩 Received: {data}")
            
            message_type = data.get("type")
            
            if message_type == "voice_start":
                await websocket.send_json({
                    "type": "session_started",
                    "data": {"status": "listening"},
                    "timestamp": time.time()
                })
                
            elif message_type == "voice_data":
                await websocket.send_json({
                    "type": "transcript_partial",
                    "data": {"text": "Listening..."},
                    "timestamp": time.time()
                })
                
            elif message_type == "voice_end":
                await websocket.send_json({
                    "type": "transcript_final",
                    "data": {"text": "Test transcription completed", "confidence": 0.95},
                    "timestamp": time.time()
                })
                await websocket.send_json({
                    "type": "agent_response",
                    "data": {"text": "I heard you!", "audio_url": None},
                    "timestamp": time.time()
                })
            else:
                await websocket.send_json({
                    "type": "echo",
                    "data": data,
                    "timestamp": time.time()
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting WebSocket Test Server")
    print("=" * 60)
    print("📍 URL: http://localhost:8000")
    print("🔌 WebSocket: ws://localhost:8000/api/v1/voice/stream/test")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
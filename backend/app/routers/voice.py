import json
import io
import wave
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.whisper_service import get_whisper_service
from app.services.rag_service import query_rag
from app.services.router_service import get_router_service
from app.services.vision_service import get_vision_service
from app.services.llm_service import get_llm_service

router = APIRouter(tags=["voice"])


@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for voice streaming.

    Protocol:
    1. Client sends audio chunks as binary data (WAV format)
    2. Client sends JSON {"type": "end"} when done recording
    3. Server responds with transcription and RAG results
    """
    await websocket.accept()
    audio_buffer = io.BytesIO()
    whisper_service = get_whisper_service()

    try:
        while True:
            message = await websocket.receive()

            # Check for disconnect
            if message.get("type") == "websocket.disconnect":
                break

            if "text" in message:
                # JSON control message
                data = json.loads(message["text"])

                if data.get("type") == "end":
                    # Process accumulated audio
                    audio_data = audio_buffer.getvalue()

                    if len(audio_data) > 0:
                        try:
                            # Send processing status
                            await websocket.send_json({
                                "type": "status",
                                "data": {"message": "Transcribing audio..."}
                            })

                            # Transcribe
                            result = whisper_service.transcribe_wav_bytes(audio_data)
                            transcription = result["text"]

                            # Send transcription
                            await websocket.send_json({
                                "type": "transcription",
                                "data": {
                                    "text": transcription,
                                    "language": result.get("language", "en")
                                }
                            })

                            if transcription.strip():
                                # Route the query using FunctionGemma
                                await websocket.send_json({
                                    "type": "status",
                                    "data": {"message": "Routing query..."}
                                })

                                router_service = get_router_service()
                                decision = await router_service.route(transcription)

                                if decision.action == "analyze_screen":
                                    # Request screenshot from frontend
                                    await websocket.send_json({
                                        "type": "request_screenshot",
                                        "data": {"question": decision.question}
                                    })
                                    # Screenshot will be handled in a separate message

                                elif decision.action == "query_documents":
                                    # Query documents (RAG)
                                    await websocket.send_json({
                                        "type": "status",
                                        "data": {"message": "Searching documents..."}
                                    })

                                    rag_result = await query_rag(decision.question)

                                    await websocket.send_json({
                                        "type": "rag_result",
                                        "data": rag_result
                                    })

                                else:
                                    # General chat - respond directly without RAG
                                    await websocket.send_json({
                                        "type": "status",
                                        "data": {"message": "Thinking..."}
                                    })

                                    llm = get_llm_service()
                                    response = await llm.generate(
                                        decision.question,
                                        context="You are a helpful voice assistant. Respond naturally and conversationally."
                                    )

                                    await websocket.send_json({
                                        "type": "chat_result",
                                        "data": {
                                            "query": decision.question,
                                            "answer": response
                                        }
                                    })
                            else:
                                await websocket.send_json({
                                    "type": "error",
                                    "data": {"message": "No speech detected"}
                                })

                        except Exception as e:
                            await websocket.send_json({
                                "type": "error",
                                "data": {"message": f"Processing error: {str(e)}"}
                            })

                    # Reset buffer for next recording
                    audio_buffer = io.BytesIO()

                elif data.get("type") == "reset":
                    # Reset buffer
                    audio_buffer = io.BytesIO()
                    await websocket.send_json({
                        "type": "status",
                        "data": {"message": "Buffer reset"}
                    })

                elif data.get("type") == "screenshot":
                    # Handle screenshot from frontend
                    image_base64 = data.get("image", "")
                    question = data.get("question", "What do you see in this image?")

                    if image_base64:
                        await websocket.send_json({
                            "type": "status",
                            "data": {"message": "Analyzing screen..."}
                        })

                        try:
                            vision_service = get_vision_service()
                            analysis = await vision_service.analyze(image_base64, question)

                            await websocket.send_json({
                                "type": "vision_result",
                                "data": {
                                    "question": question,
                                    "answer": analysis
                                }
                            })
                        except Exception as e:
                            await websocket.send_json({
                                "type": "error",
                                "data": {"message": f"Vision analysis error: {str(e)}"}
                            })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "No screenshot received"}
                        })

            elif "bytes" in message:
                # Binary audio data
                audio_buffer.write(message["bytes"])

    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": str(e)}
            })
        except:
            pass


@router.websocket("/ws/voice/stream")
async def voice_stream_websocket(websocket: WebSocket):
    """
    Alternative WebSocket for real-time streaming transcription.
    Processes audio in smaller chunks for faster feedback.
    """
    await websocket.accept()
    whisper_service = get_whisper_service()

    try:
        while True:
            message = await websocket.receive()

            # Check for disconnect
            if message.get("type") == "websocket.disconnect":
                break

            if "bytes" in message:
                audio_data = message["bytes"]

                if len(audio_data) > 0:
                    try:
                        # Transcribe chunk
                        result = whisper_service.transcribe_wav_bytes(audio_data)

                        await websocket.send_json({
                            "type": "transcription",
                            "data": {
                                "text": result["text"],
                                "partial": True
                            }
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": str(e)}
                        })

            elif "text" in message:
                data = json.loads(message["text"])

                if data.get("type") == "query":
                    # Explicit RAG query
                    query_text = data.get("text", "")
                    if query_text:
                        rag_result = await query_rag(query_text)
                        await websocket.send_json({
                            "type": "rag_result",
                            "data": rag_result
                        })

    except WebSocketDisconnect:
        print("Stream WebSocket client disconnected")

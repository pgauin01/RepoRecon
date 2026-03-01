import asyncio
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types

from tools import scout_github_issues, analyze_issue_code

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

app = FastAPI(title="RepoRecon Audio Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=GEMINI_API_KEY)

# CORRECTED: Must be the 2.0-flash model
GEMINI_MODEL = "gemini-2.5-flash-native-audio-latest"

AVAILABLE_TOOLS = {
    "scout_github_issues": scout_github_issues,
    "analyze_issue_code": analyze_issue_code,
}

LIVE_CONFIG = types.LiveConnectConfig(
    response_modalities=[types.Modality.AUDIO], 
    tools=[scout_github_issues, analyze_issue_code], # SDK handles execution automatically!
    system_instruction=types.Content(
        parts=[
            types.Part.from_text(
                text="You are RepoRecon. When the user asks to look at a repository, immediately use the scout_github_issues tool. When they pick an issue, use analyze_issue_code. Speak concisely."
            )
        ]
    ),
)


@app.get("/")
async def root():
    return {"status": "ok", "message": "RepoRecon backend is running"}


@app.websocket("/ws")
async def websocket_gemini(websocket: WebSocket):
    await websocket.accept()
    print(f"[WS] Client connected: {websocket.client}")

    session_shutdown_reason = "not established"

    try:
        async with client.aio.live.connect(
            model=GEMINI_MODEL, config=LIVE_CONFIG
        ) as session:
            print("[WS] Gemini Live session opened! Ready for voice.")

            shutdown_reason = "unknown"
            shutdown_lock = asyncio.Lock()
            receive_task = None
            send_task = None

            async def initiate_shutdown(reason: str, *, error: Exception | None = None):
                nonlocal shutdown_reason, session_shutdown_reason
                async with shutdown_lock:
                    if shutdown_reason != "unknown":
                        return
                    shutdown_reason = reason
                    session_shutdown_reason = reason
                    if error is not None:
                        print(f"[WS] Shutdown initiated by {reason}: {error}")
                    else:
                        print(f"[WS] Shutdown initiated by {reason}")

                    sibling_tasks = [task for task in (receive_task, send_task) if task is not None]
                    for task in sibling_tasks:
                        if task is not asyncio.current_task() and not task.done():
                            task.cancel()

            async def receive_from_client():
                turn_open = False

                async def finalize_turn(source: str):
                    nonlocal turn_open
                    if not turn_open:
                        print(f"[TURN] Ignoring end-turn from {source}; no active utterance")
                        return

                    print(f"[TURN] Finalizing utterance from {source} (end_of_turn=True)")
                    await session.send(end_of_turn=True)
                    turn_open = False

                try:
                    while True:
                        message = await websocket.receive()
                        message_type = message.get("type")

                        if message_type == "websocket.disconnect":
                            await finalize_turn("client websocket close event")
                            await initiate_shutdown("client websocket close")
                            break

                        if message_type != "websocket.receive":
                            print(f"[WS] Ignoring unsupported websocket event type: {message_type}")
                            continue

                        data = message.get("bytes")
                        text = message.get("text")

                        if data is not None:
                            if not turn_open:
                                turn_open = True
                                print("[TURN] New utterance started (first audio chunk)")

                            await session.send(
                                # Gemini Live works best with 16kHz for low latency
                                input={"data": data, "mime_type": "audio/pcm;rate=24000"},
                                end_of_turn=False,
                            )
                            continue

                        if text is None:
                            print("[WS] Received empty websocket frame; ignoring")
                            continue

                        try:
                            payload = json.loads(text)
                        except json.JSONDecodeError:
                            print(f"[WS] Ignoring non-JSON text frame: {text[:120]}")
                            continue

                        if payload.get("type") == "end_turn":
                            await finalize_turn("client control message")
                        else:
                            print(f"[WS] Ignoring unknown control payload: {payload}")
                except WebSocketDisconnect:
                    await finalize_turn("client disconnect")
                    await initiate_shutdown("client websocket close")
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    await initiate_shutdown("client receive fatal error", error=e)

            async def send_to_client():
                try:
                    async for response in session.receive():
                        response_fields = []
                        if getattr(response, "server_content", None) is not None:
                            response_fields.append("server_content")
                        if getattr(response, "tool_call", None) is not None:
                            response_fields.append("tool_call")
                        if getattr(response, "tool_call_cancellation", None) is not None:
                            response_fields.append("tool_call_cancellation")
                        if getattr(response, "go_away", None) is not None:
                            response_fields.append("go_away")
                        if getattr(response, "session_resumption_update", None) is not None:
                            response_fields.append("session_resumption_update")
                        if getattr(response, "input_transcription", None) is not None:
                            response_fields.append("input_transcription")
                        if getattr(response, "output_transcription", None) is not None:
                            response_fields.append("output_transcription")
                        if getattr(response, "usage_metadata", None) is not None:
                            response_fields.append("usage_metadata")

                        print(
                            f"[GeminiEvent] message_type={type(response).__name__} "
                            f"fields={response_fields or ['<none>']}"
                        )

                        tool_call = getattr(response, "tool_call", None)
                        if tool_call is not None:
                            calls = getattr(tool_call, "function_calls", None) or []
                            function_responses = []
                            for call in calls:
                                name = getattr(call, "name", "<unknown>")
                                call_id = getattr(call, "id", "<none>")
                                args = getattr(call, "args", {})
                                print(
                                    "[ToolEvent] "
                                    f"kind=request name={name} "
                                    f"id={call_id} "
                                    f"args={args}"
                                )
                                
                                ui_event = {
                                    "type": "tool_execution",
                                    "function": name,
                                    "arguments": args
                                }
                                await websocket.send_text(json.dumps(ui_event))

                                # Execute the tool
                                if name in AVAILABLE_TOOLS:
                                    func = AVAILABLE_TOOLS[name]
                                    try:
                                        # Use asyncio.to_thread to run standard functions async
                                        result = await asyncio.to_thread(func, **args)
                                        function_responses.append(types.FunctionResponse(
                                            name=name,
                                            id=call_id,
                                            response={"result": result}
                                        ))
                                    except Exception as e:
                                        print(f"[ToolError] Exception in {name}: {e}")
                                        function_responses.append(types.FunctionResponse(
                                            name=name,
                                            id=call_id,
                                            response={"error": str(e)}
                                        ))
                                else:
                                    print(f"[ToolError] Unknown tool requested: {name}")
                                    function_responses.append(types.FunctionResponse(
                                        name=name,
                                        id=call_id,
                                        response={"error": f"Unknown tool: {name}"}
                                    ))

                            if function_responses:
                                print(f"[ToolEvent] Sending {len(function_responses)} tool responses back to Gemini")
                                await session.send_tool_response(function_responses=function_responses)

                        tool_cancel = getattr(response, "tool_call_cancellation", None)
                        if tool_cancel is not None:
                            print(
                                "[ToolEvent] "
                                f"kind=cancel ids={getattr(tool_cancel, 'ids', [])}"
                            )

                        input_tx = getattr(response, "input_transcription", None)
                        if input_tx is not None and getattr(input_tx, "text", None):
                            print(f"[GeminiEvent] input_transcription={input_tx.text}")

                        output_tx = getattr(response, "output_transcription", None)
                        if output_tx is not None and getattr(output_tx, "text", None):
                            print(f"[GeminiEvent] output_transcription={output_tx.text}")

                        go_away = getattr(response, "go_away", None)
                        if go_away is not None:
                            print(f"[ControlEvent] go_away={go_away}")

                        session_resume = getattr(response, "session_resumption_update", None)
                        if session_resume is not None:
                            print(f"[ControlEvent] session_resumption_update={session_resume}")

                        usage_metadata = getattr(response, "usage_metadata", None)
                        if usage_metadata is not None:
                            print(f"[GeminiEvent] usage_metadata={usage_metadata}")

                        server_content = getattr(response, "server_content", None)
                        if server_content is not None:
                            model_turn = server_content.model_turn
                            if model_turn is not None:
                                for part in model_turn.parts:
                                    if getattr(part, "text", None):
                                        print(f"[GeminiEvent] text_part={part.text}")

                                    function_call = getattr(part, "function_call", None)
                                    if function_call is not None:
                                        print(
                                            "[ToolEvent] "
                                            f"kind=part_function_call name={getattr(function_call, 'name', '<unknown>')} "
                                            f"id={getattr(function_call, 'id', '<none>')} "
                                            f"args={getattr(function_call, 'args', {})}"
                                        )

                                    function_response = getattr(part, "function_response", None)
                                    if function_response is not None:
                                        print(
                                            "[ToolEvent] "
                                            f"kind=part_function_response name={getattr(function_response, 'name', '<unknown>')} "
                                            f"response={getattr(function_response, 'response', {})}"
                                        )

                                    if part.inline_data and part.inline_data.data:
                                        audio_bytes = part.inline_data.data
                                        # print(f"[Gemini→WS] Speaking...") # Uncomment to see audio packets
                                        await websocket.send_bytes(audio_bytes)
                    await initiate_shutdown("Gemini stream close")
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    await initiate_shutdown("Gemini API fatal error", error=e)

            receive_task = asyncio.create_task(receive_from_client(), name="receive_from_client")
            send_task = asyncio.create_task(send_to_client(), name="send_to_client")

            await asyncio.gather(receive_task, send_task, return_exceptions=True)

            if shutdown_reason == "unknown":
                shutdown_reason = "internal task completion"
                session_shutdown_reason = shutdown_reason
                print("[WS] Shutdown reason unresolved; tasks ended unexpectedly")


    except WebSocketDisconnect:
        print(f"[WS] Client disconnected: {websocket.client}")
    except Exception as e:
        print(f"[WS] Session error: {e}")
    finally:
        print(f"[WS] Gemini Live session closed (reason: {session_shutdown_reason})")

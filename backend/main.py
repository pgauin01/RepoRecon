import asyncio
import os

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types

from tools import scout_github_issues, analyze_issue_code

load_dotenv()

TOOL_FUNCTIONS = {
    "scout_github_issues": scout_github_issues,
    "analyze_issue_code": analyze_issue_code,
}

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

app = FastAPI(title="RepoRecon Audio Bridge")

# Allow the Vite dev server to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialise the Gemini client once at startup
client = genai.Client(api_key=GEMINI_API_KEY)

# CORRECTED: Use the official Live API model
GEMINI_MODEL = "gemini-2.5-flash-native-audio-latest"

LIVE_CONFIG = types.LiveConnectConfig(
    response_modalities=[types.Modality.AUDIO], # Force audio only
    tools=[scout_github_issues, analyze_issue_code],
    system_instruction=types.Content(
        parts=[
            # CORRECTED: Use .from_text() for safe SDK execution
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

    try:
        async with client.aio.live.connect(
            model=GEMINI_MODEL, config=LIVE_CONFIG
        ) as session:
            print("[WS] Gemini Live session opened! Ready for voice.")

            async def receive_from_client():
                """Read PCM audio chunks from the browser and forward to Gemini."""
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        # print(f"[WS→Gemini] {len(data)} bytes") # Commented out to avoid terminal spam
                        
                        await session.send(
                            # Gemini Live works best with 16kHz for low latency
                            input={"data": data, "mime_type": "audio/pcm;rate=16000"},
                            end_of_turn=False,
                        )
                except WebSocketDisconnect:
                    print("[WS] Client disconnected — stopping receive task")

            async def send_to_client():
                """Stream Gemini responses back to the browser and handle tool calls."""
                try:
                    async for response in session.receive():
                        # 1. Handle Tool Calls from Gemini
                        if response.tool_call:
                            for fc in response.tool_call.function_calls:
                                name = fc.name
                                args = fc.args
                                call_id = fc.id
                                
                                print(f"[Tool Call] Gemini requested: {name} ({args})")
                                
                                if name in TOOL_FUNCTIONS:
                                    try:
                                        # Execute the actual python function
                                        result = TOOL_FUNCTIONS[name](**args)
                                        
                                        # Send the result back to Gemini so it can generate a verbal response
                                        await session.send(
                                            input=types.LiveClientToolResponse(
                                                function_responses=[
                                                    types.FunctionResponse(
                                                        name=name,
                                                        id=call_id,
                                                        response={"result": result}
                                                    )
                                                ]
                                            )
                                        )
                                        print(f"[Tool Response] Sent result for {name} to Gemini")
                                    except Exception as err:
                                        print(f"[Tool Error] Failed to execute {name}: {err}")
                                else:
                                    print(f"[Tool Warning] Unknown tool: {name}")

                        # 2. Handle Audio Content to stream to user
                        if (
                            response.server_content
                            and response.server_content.model_turn
                        ):
                            for part in response.server_content.model_turn.parts:
                                if (
                                    part.inline_data
                                    and part.inline_data.data
                                ):
                                    audio_bytes = part.inline_data.data
                                    print(f"[Gemini→WS] Speaking... sent {len(audio_bytes)} bytes")
                                    await websocket.send_bytes(audio_bytes)
                except Exception as e:
                    print(f"[send_to_client] Error: {e}")

            receive_task = asyncio.create_task(receive_from_client())
            send_task = asyncio.create_task(send_to_client())

            done, pending = await asyncio.wait(
                [receive_task, send_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

    except WebSocketDisconnect:
        print(f"[WS] Client disconnected: {websocket.client}")
    except Exception as e:
        print(f"[WS] Session error: {e}")
    finally:
        print("[WS] Gemini Live session closed")
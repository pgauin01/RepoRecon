import asyncio
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

    try:
        async with client.aio.live.connect(
            model=GEMINI_MODEL, config=LIVE_CONFIG
        ) as session:
            print("[WS] Gemini Live session opened! Ready for voice.")

            async def receive_from_client():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        await session.send(
                            # Gemini Live works best with 16kHz for low latency
                            input={"data": data, "mime_type": "audio/pcm;rate=24000"},
                            end_of_turn=False,
                        )
                except WebSocketDisconnect:
                    print("[WS] Client disconnected")

            async def send_to_client():
                try:
                    async for response in session.receive():
                        # We only need to forward audio! The SDK executes the tools invisibly.
                        server_content = response.server_content
                        if server_content is not None:
                            model_turn = server_content.model_turn
                            if model_turn is not None:
                                for part in model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        audio_bytes = part.inline_data.data
                                        # print(f"[Gemini→WS] Speaking...") # Uncomment to see audio packets
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
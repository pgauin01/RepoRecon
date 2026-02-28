# ARCHITECTURE.md: RepoRecon (Live Agent Edition)

## 1. Project Overview

**Tagline:** A voice-native, vision-enabled tactical overwatch agent that scouts open-source bugs and pair-programs the fix with you in real-time.
**Target Hackathon Category:** Gemini Live Agent Challenge - Live Agents 🗣️ (Google)
**Core Mechanic:** A real-time, interruptible voice AI that uses tools (LangGraph + GitHub API) to fetch, analyze, and present open-source "good first issues" and their respective codebases.

## 2. Technical Stack

- **Frontend:** React 18, TypeScript, Vite, TailwindCSS.
- **Backend:** Python 3.11+, FastAPI, Uvicorn (ASGI server for WebSockets).
- **AI SDK:** `google-genai` (Official Google GenAI SDK).
- **Model:** `gemini-2.0-flash` (via the Multimodal Live API).
- **Agent Orchestration:** LangGraph (State management) + PyGithub.
- **Deployment:** Docker + Google Cloud Run (with WebSockets enabled).

## 3. System Architecture & Data Flow

### The Pipeline

1.  **Frontend Capture:** React UI captures microphone input using the Web Audio API (`AudioContext` / `AudioWorklet`), converts it to raw 16-bit PCM audio (16kHz or 24kHz), and streams it over a WebSocket.
2.  **Backend Bridge:** FastAPI receives the binary PCM stream and forwards it to the Gemini Multimodal Live API using `client.aio.live.connect()`.
3.  **Agent Logic (Tool Calling):** When the user asks a GitHub-related question (e.g., "Find me an issue in FastAPI"), Gemini pauses its audio, emits a tool call to FastAPI, which triggers the corresponding Python/LangGraph function (`search_github_issues`).
4.  **Response:** The Python function returns a string/JSON to Gemini. Gemini synthesizes a voice response and streams PCM audio bytes back to FastAPI.
5.  **Playback:** FastAPI forwards the audio bytes to the React frontend, which queues and plays them through the `AudioContext` destination.

## 4. Component Breakdown

### A. Frontend (`/frontend`)

- **Framework:** React + Vite (`npm create vite@latest frontend -- --template react-ts`).
- **Core Hook (`useLiveVoice.ts`):** \* Manages WebSocket connection to `ws://localhost:8000/ws`.
  - _Critical Audio Spec:_ Browser `MediaRecorder` outputs WebM/Opus. The Gemini Live API expects raw PCM. The frontend must either use an `AudioWorklet` to capture raw PCM directly from the mic, or the backend must transcode WebM to PCM before sending. (AI Assistant: Implement the raw PCM capture on the frontend to save backend processing overhead).
  - Handles playback of incoming Float32/Int16 array buffers from the server.
- **UI (`App.tsx`):** A clean, dark-mode "tactical dashboard" with a visual connection status indicator and a "Hold to Speak" (Push-to-Talk) button.

### B. Backend (`/backend`)

- **Framework:** FastAPI (`pip install fastapi uvicorn websockets google-genai pygithub langgraph`).
- **Entrypoint (`main.py`):**
  - Hosts the `/ws` WebSocket endpoint.
  - Initializes the `genai.Client()` and sets up the `LiveConnectConfig`.
  - Manages two asynchronous tasks: `receive_from_client` (routing React audio -> Gemini) and `send_to_client` (routing Gemini audio -> React).
- **Agent Tools (`tools.py`):** Python functions decorated with accurate docstrings and type hints so Gemini can use them.
  1.  `search_github_issues(repo_url: str) -> str`: Uses PyGithub to fetch issues labeled "good first issue" or "help wanted". Evaluates them and returns a summary.
  2.  `fetch_and_analyze_code(repo_url: str, issue_number: int) -> str`: Fetches specific `.py` files related to the chosen issue and generates a fix diff.

## 5. Hackathon Compliance Checklist

- [x] **Category Alignment:** Real-time, interruptible voice interaction (Live Agents).
- [x] **Required Model:** Uses Gemini (via Multimodal Live API).
- [x] **Required SDK:** Uses the official `google-genai` SDK.
- [x] **Cloud Requirement:** Deployed on Google Cloud Run.
- [x] **Beyond Text-In/Out:** Audio stream in, audio stream out + tool execution UI updates.

## 6. Vibe Coding Milestones (For AI Assistant Prompts)

- **Phase 1:** Scaffold the `/backend` folder. Create a dummy FastAPI WebSocket endpoint that echoes audio back.
- **Phase 2:** Scaffold the `/frontend` folder. Implement mic capture, raw PCM conversion, and WebSocket transmission to the dummy backend. Test playback loop.
- **Phase 3:** Update `/backend/main.py`. Remove the dummy echo and connect FastAPI to `gemini-2.0-flash` via the Live API. Test real-time conversational voice.
- **Phase 4:** Create `/backend/tools.py`. Implement `PyGithub` logic. Register these tools in the Gemini `LiveConnectConfig`. Test tool execution via voice commands.
- **Phase 5:** Write Dockerfile and deploy to Google Cloud Run.

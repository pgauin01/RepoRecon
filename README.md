# OpenIssueFinder (RepoRecon Live Edition)

OpenIssueFinder is a voice-native, vision-enabled tactical overwatch agent designed for the Gemini Live Agent Challenge. It scouts open-source "good first issues" and helps you pair-program the fix in real-time using a multimodal voice interface.

## 🚀 Core Features

- **Live Voice Interface:** Real-time, interruptible conversation with Gemini 2.0 Flash.
- **GitHub Issue Scouting:** Uses the GitHub API to find and analyze "good first issues".
- **Code Analysis:** Fetches and analyzes repository code to suggest fixes or explain logic.
- **Tactical Dashboard:** A terminal-styled UI for monitoring agent activity and tool execution.

## 🛠️ Technical Stack

- **Frontend:** React 18, TypeScript, Vite, TailwindCSS.
- **Backend:** Python 3.11+, FastAPI, Uvicorn, WebSockets.
- **AI/ML:** Google GenAI SDK (`gemini-2.0-flash-live`), LangGraph for agent orchestration.
- **Tools:** PyGithub for repository interaction.

## ⚙️ Setup & Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud Project with Gemini API access.
- GitHub Personal Access Token (for repository scouting).

### Backend Setup

1. **Navigate to backend:**
   ```bash
   cd backend
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment:**
   Create a `.env` file in the `backend/` directory:
   ```env
   GOOGLE_API_KEY=your_google_api_key
   GITHUB_TOKEN=your_github_token
   ```
4. **Run Server:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend Setup

1. **Navigate to frontend:**
   ```bash
   cd frontend
   ```
2. **Install dependencies:**
   ```bash
   npm install
   ```
3. **Run Development Server:**
   ```bash
   npm run dev
   ```

## 🏗️ Project Structure

```text
.
├── backend/              # FastAPI Server & AI Logic
│   ├── main.py           # WebSocket entrypoint & Gemini connection
│   ├── tools.py          # GitHub scouting & code analysis tools
│   └── requirements.txt  # Python dependencies
├── frontend/             # React Application
│   ├── src/
│   │   ├── hooks/        # WebSocket & Audio hooks
│   │   └── App.tsx       # Main UI component
│   └── package.json      # Node dependencies
└── ARCHITECTURE.md       # Detailed system design & hackathon details
```

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

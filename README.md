# PLC Archive & Ladder UI Prototype

## Requirements
- Python 3.10+
- Node.js 20+ and npm

## Windows PowerShell setup

Open terminal 1 in the project root.

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend: http://127.0.0.1:8000  
Swagger API docs: http://127.0.0.1:8000/docs

Open terminal 2 in the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173

## Included
- Editable project name
- Expandable instruction folder and categories
- Instruction search
- Bits: NO Contact, NC Contact, Output Coil, Set Bit, Reset Bit
- Timer, counter, comparator, math and other catalog groups
- Click or drag supported contact/coil instructions onto the rung
- Ladder rails and visual wire connectors
- Select, edit tag/address, remove instruction, clear rung
- Save to backend JSON file with browser local-storage fallback
- FastAPI health endpoint and Swagger docs

## Limitations
This is a local UI prototype, not a complete PLC simulator. Run/Stop is visual only. No PLC scan engine evaluates the ladder. Set/reset, timers, counters, comparisons and math are catalog-only. State is stored in a local JSON file, not PostgreSQL. Do not connect it to real machinery.

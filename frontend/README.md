# PLC Studio Frontend

The interactive web frontend for **PLC Studio**, built with **React 19**, **TypeScript**, and **Vite**.

It provides a modern industrial automation workbench featuring an intuitive ladder diagram editor, a virtual hardware simulation breadboard with interactive I/O devices, a real-time 50ms PLC scan engine, and an embedded AI engineering assistant for runtime diagnostics and ladder troubleshooting.

---

## 1. Features & Capabilities

### ⚡ Ladder Logic Editor
- **Multi-Network Structure**: Group rungs into distinct networks (`NetworkView.tsx`), each with custom titles, comments, and expand/collapse controls.
- **Visual Rung Execution**: Displays live power rails and energized conductors showing active power flow through contacts and coils.
- **Instruction Support**:
  - **Normally Open Contact (`contact_no`, `--| |--`)**: Passes power when referenced bit is `1` (True).
  - **Normally Closed Contact (`contact_nc`, `--|/|--`)**: Passes power when referenced bit is `0` (False).
  - **Output Coil (`coil_output`, `--( )--`)**: Drives output address to match rung power continuity.
  - **Set Bit (`coil_set`, `--(S)--`)**: Latches target bit `ON` when rung evaluates to True; remains set until reset.
  - **Reset Bit (`coil_reset`, `--(R)--`)**: Latches target bit `OFF` when rung evaluates to True.
- **Catalog Drag & Drop / Click Insertion**: Insert contacts and coils directly into any active network.
- **Live Bit Forcing**: Force contact addresses directly in the UI for test and simulation scenarios.
- **Instruction Addressing**: Configurable standard PLC memory addresses (`I0.0–I0.7` inputs, `Q0.0–Q0.7` outputs, `M0.0+` internal memory flags).

### 🎛️ Interactive Hardware Breadboard
- **Virtual PLC Chassis**: Displays terminal strips for digital inputs (`I0.0–I0.7`) and digital outputs (`Q0.0–Q0.7`) with live LED status lights.
- **Interactive Input Components**:
  - **Normally Open Pushbutton (`PB_NO`)**: Momentary start button (active only while pressed).
  - **Normally Closed Pushbutton (`PB_NC`)**: Momentary stop button (conducts at rest, breaks when pressed).
  - **Toggle Switch (`Switch`)**: Latching two-position selector switch.
  - **Emergency Stop (`EStop`)**: Latching mushroom button, wired normally closed.
  - **Limit Switch (`Limit`)**: Mechanical limit switch sensor.
- **Visual Output Actuators**:
  - **Pilot Indicator Lights**: Red, green, yellow, and blue indicator lamps with illuminated glows.
  - **Control Relays**: Visual electromechanical relays with status indicators.
  - **AC Motors**: Industrial motor actuators with rotating state visualization.
  - **Buzzers & Solenoid Valves**: Visual warning and pneumatic/hydraulic actuator models.
- **Draggable Layout**: Freely arrange hardware parts across the canvas. Wire components to specific terminal addresses.

### ⏱️ Real-Time PLC Scan Engine
- **Deterministic 50ms Scan Loop**: Powered by `usePlcRuntime.ts` and `engine.ts`, simulating real-world PLC cyclical CPU scans:
  1. **Read Inputs**: Samples hardware switches, momentary buttons, and force overrides into the input image table (`inputs`).
  2. **Execute Ladder**: Evaluates networks sequentially from top to bottom. Results from Network 1 are immediately visible to Network 2 within the same scan.
  3. **Update Memory & Coils**: Writes output states (`memory`) and sets latching flags (`coil_set` / `coil_reset`).
  4. **Update Visuals**: Emits `energized` bit maps to render active power paths on the UI.
- **Run / Stop Control**: Instantly halt execution; stopping clears energized rails and unlatches outputs.

### 🤖 Embedded AI Engineering Assistant
- **Dockable Assistant Panel (`AgentPanel.tsx`)**: Ask questions about ladder logic, troubleshoot why an output isn't energizing, or check wiring mismatches.
- **Context-Aware Diagnostics (`agentClient.ts`)**: Automatically extracts live simulator state:
  - Project name and running/stopped state.
  - Serialized ladder networks and instruction ordering.
  - Connected hardware parts and assigned terminal addresses.
  - Current input bit (`I`) and output bit (`Q`) states.
- **Authoritative Manual Citations**: Receives grounded answers with verifiable citations (e.g., Siemens S7-1200 or Rockwell Automation 1756 manuals).
- **One-Click Diagnostic Prompts**: Quick suggestion chips (*"Explain my ladder logic"*, *"Check my wiring"*, *"Show current I/O state"*).

### 💾 Project State & Persistence
- **Full Cloud/Server Sync**: Synchronizes ladder rungs, networks, and hardware board placements with the backend REST API (`GET /api/state`, `PUT /api/state`).
- **Offline Local Storage Fallback**: Seamlessly falls back to browser `localStorage` if the backend server is unreachable.

---

## 2. Directory Structure

```
frontend/
├── index.html                   # HTML entrypoint
├── package.json                 # Dependencies & build scripts
├── tsconfig.json                # TypeScript project configuration
├── vite.config.ts               # Vite configuration (port 5173)
└── src/
    ├── main.tsx                 # React DOM root entrypoint
    ├── App.tsx                  # Primary workbench application shell & toolbar
    ├── config.ts                # Global client configuration (API URL, SCAN_MS)
    ├── types.ts                 # Core TypeScript domain types (Network, Node, Inst, Bits)
    ├── util.ts                  # ID generation and math utilities
    ├── styles.css               # Base layout styling
    ├── workbench.css            # Industrial workbench, ladder, and hardware styles
    ├── agent/
    │   ├── AgentPanel.tsx       # AI chat drawer interface with suggestions
    │   └── agentClient.ts       # Context serialization & RAG API HTTP client
    ├── hardware/
    │   ├── catalog.ts           # Hardware parts definitions (PB, switches, lights, motors)
    │   ├── graphics.tsx         # SVG rendering for industrial components & PLC chassis
    │   └── HardwarePanel.tsx    # Interactive breadboard canvas & wiring terminal strip
    ├── ladder/
    │   └── NetworkView.tsx      # Rung/network visualizer, power rails, node controls
    └── plc/
        ├── defaults.ts          # Default instruction catalog and categories
        ├── engine.ts            # Scan engine evaluator, power continuity & latching logic
        ├── networks.ts          # Network state helpers, creation, and migration
        └── usePlcRuntime.ts     # React hook executing cyclical 50ms scans
```

---

## 3. Getting Started

### Prerequisites
- **Node.js**: version `20.0.0` or higher
- **npm**: version `10.0.0` or higher

### Installation
Open a terminal in the `frontend` folder:

```powershell
cd frontend
npm install
```

### Running the Development Server
```powershell
npm run dev
```

The application will start on:  
👉 **http://127.0.0.1:5173**

### Building for Production
```powershell
npm run build
```

To preview the production build locally:
```powershell
npm run preview
```

---

## 4. Configuration

Key client settings can be customized in [`src/config.ts`](file:///c:/Users/rawat/Desktop/PLC-Stimulator/frontend/src/config.ts):

| Setting | Default Value | Description |
| :--- | :--- | :--- |
| `API` | `'http://127.0.0.1:8000/api'` | Base URL for the Node.js backend (state persistence & catalog). |
| `SCAN_MS` | `50` | PLC CPU scan cycle duration in milliseconds (20 scans per second). |

For direct RAG AI queries, [`src/agent/agentClient.ts`](file:///c:/Users/rawat/Desktop/PLC-Stimulator/frontend/src/agent/agentClient.ts) connects to:
- `RAG_API`: `'http://127.0.0.1:8001/chat'` (FastAPI RAG Assistant).

---

## 5. User Workflow & Quick Tour

1. **Construct Logic**: In the left pane, expand the *Instruction Folder* -> *Bits*. Click or drag **NO Contact** (`contact_no`) and an **Output Coil** (`coil_output`) onto Network 1.
2. **Assign Addresses**: Click on the contact to assign input address `I0.0`. Click on the coil to assign output address `Q0.0`.
3. **Wire Hardware**: In the lower Hardware panel, drag a **Pushbutton (NO)** and a **Green Pilot Light** onto the board. Set their addresses to `I0.0` and `Q0.0` respectively.
4. **Run Simulation**: Click **Run** in the top navigation bar. The scan cycle initiates.
5. **Actuate Inputs**: Click and hold the pushbutton on the hardware board. Observe:
   - Terminal `I0.0` LED illuminates on the PLC chassis.
   - Power flow turns green on Network 1 across the contact to the coil.
   - Terminal `Q0.0` activates, and the green pilot light illuminates.
6. **Ask the AI**: Click the **AI Agent** icon in the header. Ask *"Why is motor Q0.0 turning on?"* or click *"Check my wiring"*. The assistant analyzes your live canvas and responds with cited industrial documentation.


import { useEffect, useMemo, useState } from "react";
import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";

import {
  Folder,
  ChevronDown,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Save,
  Plus,
  Eraser,
  Play,
  Square,
  CircuitBoard,
  FolderTree,
  Info,
  Bot,
} from "lucide-react";

import "./workbench.css";

import type {
  Archive,
  Bits,
  FolderNode,
  HwComponent,
  Inst,
  Network,
  Node,
} from "./types";
import { API, SCAN_MS } from "./config";
import { clamp, createId } from "./util";
import { defaultArchive, fallbackInstructions } from "./plc/defaults";
import { isTerminalOutput, normalizeAddress } from "./plc/engine";
import { loadNetworks, makeDefaultNetworks, makeNetwork } from "./plc/networks";
import { usePlcRuntime } from "./plc/usePlcRuntime";
import {
  HW_BY_TYPE,
  componentSignal,
  hwInputValue,
  makeDefaultHardware,
  sanitizeHardware,
  terminalIndex,
} from "./hardware/catalog";
import HardwarePanel from "./hardware/HardwarePanel";
import NetworkView from "./ladder/NetworkView";
import AgentPanel from "./agent/AgentPanel";
import type { AgentContext } from "./agent/agentClient";

export default function App() {
  const [archive, setArchive] = useState<Archive>(defaultArchive);
  const [project, setProject] = useState("Motor Control Project");
  const [networks, setNetworks] = useState<Network[]>(makeDefaultNetworks);
  /* Network that receives new instructions (null = the first one). */
  const [activeNetwork, setActiveNetwork] = useState<string | null>(null);

  const [open, setOpen] = useState<Record<string, boolean>>({
    "instruction-folder": true,
    bits: true,
  });
  const [visible, setVisible] = useState(true);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [status, setStatus] = useState("Connecting...");
  const [message, setMessage] = useState("Ready");
  const [running, setRunning] = useState(false);

  /* Inputs forced ON by clicking a contact in the ladder while running (by address). */
  const [forced, setForced] = useState<Bits>({});

  /* Hardware board */
  const [components, setComponents] =
    useState<HwComponent[]>(makeDefaultHardware);
  const [hwActive, setHwActive] = useState<Record<string, boolean>>({});
  const [hwSelected, setHwSelected] = useState<string | null>(null);

  /* Layout */
  const [agentOpen, setAgentOpen] = useState(true);
  const [ladderW, setLadderW] = useState(520);
  const [agentW, setAgentW] = useState(320);

  const instructions = archive.instructions.length
    ? archive.instructions
    : fallbackInstructions;

  const instMap = useMemo(
    () => new Map(instructions.map((i) => [i.id, i])),
    [instructions],
  );

  const activeNetId = networks.some((n) => n.id === activeNetwork)
    ? (activeNetwork as string)
    : (networks[0]?.id ?? "");

  /*
   * Input image the PLC sees: every wired hardware input (OR-ed when several
   * parts share an address) plus anything forced from the ladder.
   */
  const inputBits = useMemo(() => {
    const bits: Bits = {};
    for (const c of components) {
      const def = HW_BY_TYPE.get(c.type);
      if (!def || def.kind !== "input") continue;
      if (terminalIndex(c.address, "input") === null) continue;
      const address = normalizeAddress(c.address);
      bits[address] =
        bits[address] === true || hwInputValue(def, hwActive[c.id] === true);
    }
    for (const [address, value] of Object.entries(forced)) {
      if (value) bits[address] = true;
    }
    return bits;
  }, [components, hwActive, forced]);

  console.log("APP networks:", networks);

  /* Scan engine: all networks (top to bottom) + inputs -> outputs / latched bits. */
  const { memory, energized } = usePlcRuntime({
    running,
    networks,
    instMap,
    inputs: inputBits,
  });

  const outputBits = useMemo(() => {
    const bits: Bits = {};
    for (const [address, value] of Object.entries(memory)) {
      if (/^Q0\.[0-7]$/.test(address)) bits[address] = value;
    }
    return bits;
  }, [memory]);

  useEffect(() => {
    fetch(`${API}/archive`)
      .then((r) => {
        if (!r.ok) throw Error();
        return r.json();
      })
      .then((d) => {
        setArchive(d);
        setStatus("API connected");
      })
      .catch(() => setStatus("API offline · local mode"));

    fetch(`${API}/state`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => {
        if (d.project_name) setProject(d.project_name);
        const loaded = loadNetworks(d);
        if (loaded) setNetworks(loaded);
      })
      .catch(() => {});

    try {
      const d = JSON.parse(localStorage.getItem("plc-state") || "null");
      if (d) {
        if (d.project_name) setProject(d.project_name);
        const loaded = loadNetworks(d);
        if (loaded) setNetworks(loaded);
        const hardware = sanitizeHardware(d.hardware);
        if (hardware) setComponents(hardware);
      }
    } catch {
      // Ignore invalid browser-stored project data.
    }
  }, []);

  /* ---------------- Network operations ---------------- */

  function patchNetwork(id: string, patch: Partial<Network>) {
    setNetworks((previous) =>
      previous.map((n) => (n.id === id ? { ...n, ...patch } : n)),
    );
  }

  function patchNode(networkId: string, instanceId: string, patch: Partial<Node>) {
    setNetworks((previous) =>
      previous.map((n) =>
        n.id !== networkId
          ? n
          : {
              ...n,
              nodes: n.nodes.map((x) =>
                x.instanceId === instanceId ? { ...x, ...patch } : x,
              ),
            },
      ),
    );
  }

  function addNetwork(afterId?: string) {
    const fresh = makeNetwork();
    setNetworks((previous) => {
      const i = afterId ? previous.findIndex((n) => n.id === afterId) : -1;
      const at = i === -1 ? previous.length : i + 1;
      return [...previous.slice(0, at), fresh, ...previous.slice(at)];
    });
    setActiveNetwork(fresh.id);
    setSelected(null);
    setMessage("Network added");
  }

  function moveNetwork(id: string, direction: -1 | 1) {
    setNetworks((previous) => {
      const i = previous.findIndex((n) => n.id === id);
      const j = i + direction;
      if (i === -1 || j < 0 || j >= previous.length) return previous;
      const next = [...previous];
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });
  }

  function nodeInNetwork(net: Network | undefined, instanceId: string | null) {
    return !!net && !!instanceId && net.nodes.some((x) => x.instanceId === instanceId);
  }

  function clearNetwork(id: string) {
    const net = networks.find((n) => n.id === id);
    if (!net) return;
    if (nodeInNetwork(net, selected)) setSelected(null);
    patchNetwork(id, { nodes: [] });
    setForced({});
    setMessage(`Network ${networks.indexOf(net) + 1} cleared`);
  }

  function deleteNetwork(id: string) {
    if (networks.length <= 1) return;
    const net = networks.find((n) => n.id === id);
    if (!net) return;
    const number = networks.indexOf(net) + 1;
    if (
      net.nodes.length &&
      !window.confirm(`Delete Network ${number} and its ${net.nodes.length} instruction(s)?`)
    ) {
      return;
    }
    if (nodeInNetwork(net, selected)) setSelected(null);
    setActiveNetwork(null);
    setNetworks((previous) => previous.filter((n) => n.id !== id));
    setMessage(`Network ${number} deleted`);
  }

  /*
   * Insert an instruction into a network (the dropped-on one, else the active one).
   * Contacts go after the selected element, or at the end; they are placed before
   * the output coil if there is one. Output Coil / Set / Reset must end the rung,
   * so only one is allowed per network.
   */
  function add(instruction: Inst, targetId?: string) {
    if (!["contact", "coil"].includes(instruction.kind)) {
      setMessage(
        `${instruction.name} is catalogued, but placement is not implemented yet.`,
      );
      return;
    }

    const net = networks.find((n) => n.id === (targetId ?? activeNetId));
    if (!net) return;
    const number = networks.indexOf(net) + 1;

    const terminalAt = net.nodes.findIndex((n) =>
      isTerminalOutput(n.instructionId),
    );
    const isOutput = instruction.kind === "coil";

    if (isOutput && terminalAt !== -1) {
      setMessage(
        `Network ${number} already ends with an output instruction. Remove it or use another network.`,
      );
      return;
    }

    const selectedAt = net.nodes.findIndex((n) => n.instanceId === selected);
    let at = selectedAt === -1 ? net.nodes.length : selectedAt + 1;
    if (isOutput) at = net.nodes.length;
    else if (terminalAt !== -1) at = Math.min(at, terminalAt);

    const newNode: Node = {
      instanceId: createId(),
      instructionId: instruction.id,
      address: instruction.default_address,
      name: instruction.name.replaceAll(" ", "_"),
    };

    setNetworks((previous) =>
      previous.map((n) =>
        n.id === net.id
          ? {
              ...n,
              nodes: [...n.nodes.slice(0, at), newNode, ...n.nodes.slice(at)],
            }
          : n,
      ),
    );
    setActiveNetwork(net.id);
    selectNode(newNode.instanceId);
    setMessage(`${instruction.name} inserted into Network ${number}`);
  }

  function insertHint(net: Network) {
    const number = networks.indexOf(net) + 1;
    setActiveNetwork(net.id);
    setMessage(
      net.nodes.some((n) => isTerminalOutput(n.instructionId))
        ? `Network ${number} ends with an output. New contacts are placed before it.`
        : `Choose an instruction from the archive to add to Network ${number}`,
    );
  }

  function selectNode(id: string | null, networkId?: string) {
    setSelected(id);
    if (networkId) setActiveNetwork(networkId);
    if (id) setHwSelected(null);
  }

  function selectPart(id: string | null) {
    setHwSelected(id);
    if (id) setSelected(null);
  }

  /*
   * Clicking a contact while the PLC runs forces that address ON
   * (or removes the force). Real inputs come from the hardware board.
   */
  function toggleForce(node: Node) {
    if (!running) return;
    const address = normalizeAddress(node.address);
    if (!address) {
      setMessage("Set an address on this contact first");
      return;
    }
    const next = forced[address] !== true;
    setForced((previous) => ({ ...previous, [address]: next }));
    setMessage(
      next
        ? `${address} forced ON from the ladder`
        : `${address} force removed`,
    );
  }

  function toggleSimulation() {
    setForced({});
    if (running) {
      setRunning(false);
      setMessage("Simulation stopped · outputs are OFF");
    } else {
      setRunning(true);
      setMessage(
        "PLC running · use the hardware board inputs (or click a contact to force it)",
      );
    }
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;

      if (
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable
      ) {
        return;
      }

      if (event.key !== "Delete" && event.key !== "Backspace") return;

      if (hwSelected) {
        event.preventDefault();
        setComponents((previous) =>
          previous.filter((c) => c.id !== hwSelected),
        );
        setHwSelected(null);
        setMessage("Selected hardware part removed");
      } else if (selected) {
        event.preventDefault();
        setNetworks((previous) =>
          previous.map((n) => ({
            ...n,
            nodes: n.nodes.filter((node) => node.instanceId !== selected),
          })),
        );
        setSelected(null);
        setMessage("Selected instruction removed");
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selected, hwSelected]);

  async function save() {
    const state = {
      project_name: project,
      networks,
      hardware: components,
    };

    localStorage.setItem("plc-state", JSON.stringify(state));

    try {
      const response = await fetch(`${API}/state`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state),
      });

      if (!response.ok) throw Error();

      setMessage("Project saved to backend and browser storage");
    } catch {
      setMessage("Saved in browser storage; backend offline");
    }
  }

  /* Everything the AI agent needs to know about the current project. */
  const getAgentContext = (): AgentContext => ({
    project,
    running,
    ladder: networks.flatMap((net, ni) =>
      net.nodes.map((n) => {
        const i = instMap.get(n.instructionId);
        return {
          network: ni + 1,
          networkTitle: net.title,
          name: n.name,
          address: n.address,
          instructionId: n.instructionId,
          instruction: i?.name ?? n.instructionId,
          kind: i?.kind ?? "unknown",
        };
      }),
    ),
    hardware: components.map((c) => {
      const def = HW_BY_TYPE.get(c.type);
      return {
        label: c.label,
        type: def?.name ?? c.type,
        kind: def?.kind ?? "input",
        address: c.address,
        signal: componentSignal(c, hwActive[c.id] === true, outputBits),
      };
    }),
    inputs: inputBits,
    outputs: outputBits,
  });

  function beginResize(
    event: ReactPointerEvent<HTMLDivElement>,
    which: "ladder" | "agent",
  ) {
    event.preventDefault();
    const startX = event.clientX;
    const startLadder = ladderW;
    const startAgent = agentW;

    const move = (e: PointerEvent) => {
      const dx = e.clientX - startX;
      if (which === "ladder") setLadderW(clamp(startLadder + dx, 280, 1200));
      else setAgentW(clamp(startAgent - dx, 240, 640));
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      document.body.classList.remove("resizing");
    };

    document.body.classList.add("resizing");
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  function folder(f: FolderNode, depth = 0): ReactNode {
    const expanded = !!open[f.id];
    const children = f.children || [];

    const list = (f.instruction_ids || [])
      .map((k) => instMap.get(k))
      .filter(
        (instruction): instruction is Inst =>
          !!instruction &&
          `${instruction.name} ${instruction.id} ${instruction.description}`
            .toLowerCase()
            .includes(search.toLowerCase()),
      );

    return (
      <div key={f.id}>
        <button
          className="tree-row"
          style={{ paddingLeft: 5 + depth * 12 }}
          onClick={() =>
            setOpen((previous) => ({
              ...previous,
              [f.id]: !previous[f.id],
            }))
          }
        >
          {expanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
          <Folder size={16} className="folder-icon" />
          {f.name}
        </button>

        {expanded && (
          <div className="tree-children">
            {children.map((child) => folder(child, depth + 1))}

            {list.map((instruction) => (
              <button
                className="instruction"
                key={instruction.id}
                title={`${instruction.tooltip} · click to insert`}
                draggable
                onDragStart={(event) =>
                  event.dataTransfer.setData("instructionId", instruction.id)
                }
                onClick={() => add(instruction)}
              >
                <span className="instruction-symbol">{instruction.symbol}</span>
                <span className="instruction-name">{instruction.name}</span>
                {!instruction.implemented && <i className="planned-dot" />}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`app ${visible ? "" : "wide"}`}>
      {visible && (
        <aside className="archive">
          <header className="archive-header">
            <span>
              <FolderTree size={19} /> Project Archive
            </span>

            <button
              className="icon-button"
              onClick={() => setVisible(false)}
              title="Hide archive"
            >
              <PanelLeftClose size={17} />
            </button>
          </header>

          <section className="project-section">
            <label>Project Name</label>
            <input
              className="project-input"
              value={project}
              onChange={(event) => setProject(event.target.value)}
              onBlur={() => {
                if (!project.trim()) setProject("Untitled PLC Project");
              }}
            />
          </section>

          <div className="archive-search">
            <Search size={15} />
            <input
              placeholder="Search instructions..."
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setOpen((previous) => ({
                  ...previous,
                  "instruction-folder": true,
                  bits: true,
                  timers: true,
                  counters: true,
                  comparators: true,
                  math: true,
                }));
              }}
            />
          </div>

          <div className="archive-tree">
            {archive.folders.map((f) => folder(f))}
          </div>

          <footer className="archive-footer">
            <Info size={14} />
            <span>
              Click an instruction to insert it into the highlighted network.
              Drag an instruction onto any network to add it there.
            </span>
          </footer>
        </aside>
      )}

      <main className="editor">
        <div className="topbar">
          {!visible && (
            <button onClick={() => setVisible(true)}>
              <PanelLeftOpen size={16} />
            </button>
          )}

          <div className="app-mark">
            <CircuitBoard size={19} />
            <b>PLC Studio</b>
            <span className="version">Prototype</span>
          </div>

          <div className="top-actions">
            <button onClick={save}>
              <Save size={15} /> Save
            </button>

            <button onClick={() => addNetwork()}>
              <Plus size={15} /> Add network
            </button>

            <button onClick={() => clearNetwork(activeNetId)}>
              <Eraser size={15} /> Clear network
            </button>

            <button
              className={running ? "run-active" : ""}
              onClick={toggleSimulation}
            >
              {running ? <Square size={15} /> : <Play size={15} />}
              {running ? "Stop" : "Run"}
            </button>

            <button
              className={agentOpen ? "run-active" : ""}
              onClick={() => setAgentOpen((v) => !v)}
              title="Show or hide the AI agent"
            >
              <Bot size={15} /> Agent
            </button>
          </div>
        </div>

        <div className="editor-tabs">
          <span className="active-tab">Main [OB1]</span>
          <span>
            {networks.length} network{networks.length === 1 ? "" : "s"}
          </span>
          <span className="editor-status">{status}</span>
        </div>

        <div className="panes">
          {/* ---------- Ladder window ---------- */}
          <section className="pane ladder-pane" style={{ width: ladderW }}>
            <header className="pane-header">
              <span>
                <CircuitBoard size={15} /> Ladder Logic
              </span>
            </header>

            <section className="workspace">
              {networks.map((net, i) => (
                <NetworkView
                  key={net.id}
                  network={net}
                  index={i}
                  total={networks.length}
                  active={net.id === activeNetId}
                  running={running}
                  instMap={instMap}
                  energized={energized}
                  inputBits={inputBits}
                  memory={memory}
                  forced={forced}
                  selectedNode={selected}
                  onActivate={() => setActiveNetwork(net.id)}
                  onSelectNode={(id) => selectNode(id, net.id)}
                  onForce={toggleForce}
                  onPatch={(patch) => patchNetwork(net.id, patch)}
                  onPatchNode={(id, patch) => patchNode(net.id, id, patch)}
                  onMove={(direction) => moveNetwork(net.id, direction)}
                  onAddBelow={() => addNetwork(net.id)}
                  onClear={() => clearNetwork(net.id)}
                  onDelete={() => deleteNetwork(net.id)}
                  onDropInstruction={(id) => {
                    const instruction = instMap.get(id);
                    if (instruction) add(instruction, net.id);
                  }}
                  onInsertClick={() => insertHint(net)}
                />
              ))}

              <button className="add-network" onClick={() => addNetwork()}>
                <Plus size={15} /> Add network
              </button>
            </section>
          </section>

          <div
            className="splitter"
            role="separator"
            aria-orientation="vertical"
            onPointerDown={(e) => beginResize(e, "ladder")}
          />

          {/* ---------- Hardware window ---------- */}
          <section className="pane hw-pane">
            <HardwarePanel
              components={components}
              setComponents={setComponents}
              selectedId={hwSelected}
              onSelect={selectPart}
              active={hwActive}
              onActive={(id, value) =>
                setHwActive((previous) => ({ ...previous, [id]: value }))
              }
              inputBits={inputBits}
              outputBits={outputBits}
              running={running}
            />
          </section>

          {/* ---------- AI agent window ---------- */}
          {agentOpen && (
            <>
              <div
                className="splitter"
                role="separator"
                aria-orientation="vertical"
                onPointerDown={(e) => beginResize(e, "agent")}
              />
              <section className="pane agent-pane" style={{ width: agentW }}>
                <AgentPanel
                  getContext={getAgentContext}
                  onClose={() => setAgentOpen(false)}
                />
              </section>
            </>
          )}
        </div>

        <footer className="statusbar">
          <span className="status-dot" />
          <span>{message}</span>
          <span className="spacer" />
          <span>{running ? `RUN · scan ${SCAN_MS} ms` : "STOP"}</span>
          <span>Local prototype</span>
          <span>UTF-8</span>
        </footer>
      </main>
    </div>
  );
}
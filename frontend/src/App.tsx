import { useEffect, useState } from 'react'

import type { ReactNode } from 'react'

import {

  Folder,

  ChevronDown,

  ChevronRight,

  PanelLeftClose,

  PanelLeftOpen,

  Search,

  Save,

  Plus,

  Play,

  Square,

  CircuitBoard,

  FolderTree,

  Info

} from 'lucide-react'

type Inst = {

  id: string

  name: string

  symbol: string

  kind: string

  implemented: boolean

  description: string

  default_address: string

  tooltip: string

}

type FolderNode = {

  id: string

  name: string

  instruction_ids?: string[]

  children?: FolderNode[]

}

type Archive = {

  folders: FolderNode[]

  instructions: Inst[]

}

type Node = {

  instanceId: string

  instructionId: string

  address: string

  name: string

}

const API = 'http://127.0.0.1:8000/api'

const defaultArchive: Archive = {

  folders: [

    {

      id: 'instruction-folder',

      name: 'Instruction Folder',

      children: [

        {

          id: 'bits',

          name: 'Bits',

          instruction_ids: [

            'contact_no',

            'contact_nc',

            'coil_output',

            'coil_set',

            'coil_reset'

          ]

        },

        {

          id: 'timers',

          name: 'Timers',

          instruction_ids: ['timer_ton', 'timer_tof', 'timer_tp']

        },

        {

          id: 'counters',

          name: 'Counters',

          instruction_ids: ['counter_ctu', 'counter_ctd']

        },

        {

          id: 'comparators',

          name: 'Comparators',

          instruction_ids: ['compare_eq', 'compare_gt', 'compare_lt']

        },

        {

          id: 'math',

          name: 'Math Operators',

          instruction_ids: ['math_add', 'math_sub', 'math_mul', 'math_div']

        },

        {

          id: 'function-blocks',

          name: 'Function Blocks',

          instruction_ids: []

        },

        {

          id: 'program-control',

          name: 'Program Control',

          instruction_ids: []

        }

      ]

    }

  ],

  instructions: []

}

const createId = () =>

  `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`

/*

 * All these instructions are terminal outputs.

 * No instruction may be placed after one of them.

 */

const isTerminalOutput = (instructionId: string) =>

  ['coil_output', 'coil_set', 'coil_reset'].includes(instructionId)

const isContact = (instruction?: Inst) =>

  instruction?.kind === 'contact'

export default function App() {

  const [archive, setArchive] = useState<Archive>(defaultArchive)

  const [project, setProject] = useState('Motor Control Project')

  const [nodes, setNodes] = useState<Node[]>([

    {

      instanceId: createId(),

      instructionId: 'contact_no',

      address: 'I0.0',

      name: 'Start_PB'

    },

    {

      instanceId: createId(),

      instructionId: 'coil_output',

      address: 'Q0.0',

      name: 'Motor_Running'

    }

  ])

  const [open, setOpen] = useState<Record<string, boolean>>({

    'instruction-folder': true,

    bits: true

  })

  const [visible, setVisible] = useState(true)

  const [search, setSearch] = useState('')

  const [selected, setSelected] = useState<string | null>(null)

  const [status, setStatus] = useState('Connecting...')

  const [message, setMessage] = useState('Ready')

  const [running, setRunning] = useState(false)

  /*

   * Simulated physical input states.

   * true = input ON; false/undefined = input OFF.

   */

  const [inputStates, setInputStates] = useState<Record<string, boolean>>({})

  const fallbackInstructions: Inst[] = [

    {

      id: 'contact_no',

      name: 'NO Contact',

      symbol: '--| |--',

      kind: 'contact',

      implemented: true,

      description: 'Passes logic when Boolean value is ON.',

      default_address: 'I0.0',

      tooltip: 'Normally Open contact'

    },

    {

      id: 'contact_nc',

      name: 'NC Contact',

      symbol: '--|/|--',

      kind: 'contact',

      implemented: true,

      description: 'Passes logic when Boolean value is OFF.',

      default_address: 'I0.1',

      tooltip: 'Normally Closed contact'

    },

    {

      id: 'coil_output',

      name: 'Output Coil',

      symbol: '--( )--',

      kind: 'coil',

      implemented: true,

      description: 'Writes rung result to output/tag.',

      default_address: 'Q0.0',

      tooltip: 'Output coil'

    },

    {

      id: 'coil_set',

      name: 'Set Bit',

      symbol: '--(S)--',

      kind: 'coil',

      implemented: false,

      description: 'Set coil; execution is not implemented.',

      default_address: 'M0.0',

      tooltip: 'Set coil'

    },

    {

      id: 'coil_reset',

      name: 'Reset Bit',

      symbol: '--(R)--',

      kind: 'coil',

      implemented: false,

      description: 'Reset coil; execution is not implemented.',

      default_address: 'M0.0',

      tooltip: 'Reset coil'

    },

    {

      id: 'timer_ton',

      name: 'TON',

      symbol: 'TON',

      kind: 'timer',

      implemented: false,

      description: 'Catalog only; execution not implemented.',

      default_address: 'T1',

      tooltip: 'On-delay timer'

    },

    {

      id: 'timer_tof',

      name: 'TOF',

      symbol: 'TOF',

      kind: 'timer',

      implemented: false,

      description: 'Catalog only; execution not implemented.',

      default_address: 'T2',

      tooltip: 'Off-delay timer'

    },

    {

      id: 'timer_tp',

      name: 'TP',

      symbol: 'TP',

      kind: 'timer',

      implemented: false,

      description: 'Catalog only; execution not implemented.',

      default_address: 'T3',

      tooltip: 'Pulse timer'

    },

    {

      id: 'counter_ctu',

      name: 'CTU',

      symbol: 'CTU',

      kind: 'counter',

      implemented: false,

      description: 'Catalog only; execution not implemented.',

      default_address: 'C1',

      tooltip: 'Count up'

    },

    {

      id: 'counter_ctd',

      name: 'CTD',

      symbol: 'CTD',

      kind: 'counter',

      implemented: false,

      description: 'Catalog only; execution not implemented.',

      default_address: 'C2',

      tooltip: 'Count down'

    },

    {

      id: 'compare_eq',

      name: 'Equal',

      symbol: '==',

      kind: 'compare',

      implemented: false,

      description: 'Catalog only; execution not implemented.',

      default_address: '',

      tooltip: 'Compare equal'

    },

    {

      id: 'compare_gt',

      name: 'Greater Than',

      symbol: '>',

      kind: 'compare',

      implemented: false,

      description: 'Catalog only; execution not implemented.',

      default_address: '',

      tooltip: 'Compare greater than'

    },

    {

      id: 'compare_lt',

      name: 'Less Than',

      symbol: '<',

      kind: 'compare',

      implemented: false,

      description: 'Catalog only; execution not implemented.',

      default_address: '',

      tooltip: 'Compare less than'

    },

    {

      id: 'math_add',

      name: 'Add',

      symbol: 'ADD',

      kind: 'math',

      implemented: false,

      description: 'Catalog only; execution not implemented.',

      default_address: '',

      tooltip: 'Add values'

    },

    {

      id: 'math_sub',

      name: 'Subtract',

      symbol: 'SUB',

      kind: 'math',

      implemented: false,

      description: 'Catalog only; execution not implemented.',

      default_address: '',

      tooltip: 'Subtract values'

    },

    {

      id: 'math_mul',

      name: 'Multiply',

      symbol: 'MUL',

      kind: 'math',

      implemented: false,

      description: 'Catalog only; execution not implemented.',

      default_address: '',

      tooltip: 'Multiply values'

    },

    {

      id: 'math_div',

      name: 'Divide',

      symbol: 'DIV',

      kind: 'math',

      implemented: false,

      description: 'Catalog only; execution not implemented.',

      default_address: '',

      tooltip: 'Divide values'

    }

  ]

  const instructions = archive.instructions.length

    ? archive.instructions

    : fallbackInstructions

  const instMap = new Map(instructions.map(i => [i.id, i]))

  useEffect(() => {

    fetch(`${API}/archive`)

      .then(r => {

        if (!r.ok) throw Error()

        return r.json()

      })

      .then(d => {

        setArchive(d)

        setStatus('API connected')

      })

      .catch(() => setStatus('API offline · local mode'))

    fetch(`${API}/state`)

      .then(r => (r.ok ? r.json() : Promise.reject()))

      .then(d => {

        if (d.project_name) setProject(d.project_name)

        if (d.instructions?.length) setNodes(d.instructions)

      })

      .catch(() => {})

    try {

      const d = JSON.parse(localStorage.getItem('plc-state') || 'null')

      if (d) {

        if (d.project_name) setProject(d.project_name)

        if (d.instructions?.length) setNodes(d.instructions)

      }

    } catch {

      // Ignore invalid browser-stored project data.

    }

  }, [])

  /*

   * Add an instruction only if the rung has not already

   * ended with an Output Coil, Set Bit, or Reset Bit.

   */

  function add(instruction: Inst) {

    if (!['contact', 'coil'].includes(instruction.kind)) {

      setMessage(

        `${instruction.name} is catalogued, but placement is not implemented yet.`

      )

      return

    }

    const terminalIndex = nodes.findIndex(n =>

      isTerminalOutput(n.instructionId)

    )

    if (terminalIndex !== -1) {

      setMessage(

        'Cannot add an instruction: Output Coil, Set Bit, and Reset Bit must end the rung.'

      )

      return

    }

    const newNode: Node = {

      instanceId: createId(),

      instructionId: instruction.id,

      address: instruction.default_address,

      name: instruction.name.replaceAll(' ', '_')

    }

    setNodes(previous => [...previous, newNode])

    setSelected(newNode.instanceId)

    setMessage(`${instruction.name} inserted into rung`)

  }

  /*

   * Evaluate a simple series rung from left to right.

   *

   * NO contact conducts when its input is ON.

   * NC contact conducts when its input is OFF.

   *

   * A contact is green only if logic reaches it and it

   * conducts. An output is green if all preceding contacts

   * conduct.

   */

  function isEnergized(targetInstanceId: string): boolean {

    if (!running) return false

    const targetIndex = nodes.findIndex(

      n => n.instanceId === targetInstanceId

    )

    if (targetIndex === -1) return false

    for (let index = 0; index <= targetIndex; index++) {

      const node = nodes[index]

      const instruction = instMap.get(node.instructionId)

      if (!instruction) return false

      if (isContact(instruction)) {

        const inputOn = inputStates[node.instanceId] === true

        const contactConducts =

          node.instructionId === 'contact_nc'

            ? !inputOn

            : inputOn

        if (!contactConducts) return false

      } else if (

        index < targetIndex &&

        isTerminalOutput(node.instructionId)

      ) {

        // Logic cannot continue beyond a terminal output.

        return false

      }

    }

    return true

  }

  function toggleInput(node: Node) {

    if (!running) return

    const newValue = !(inputStates[node.instanceId] === true)

    setInputStates(previous => ({

      ...previous,

      [node.instanceId]: newValue

    }))

    const instruction = instMap.get(node.instructionId)

    setMessage(

      `${node.address || instruction?.name || 'Input'} turned ${

        newValue ? 'ON' : 'OFF'

      }`

    )

  }

  function toggleSimulation() {

    if (running) {

      setRunning(false)

      setInputStates({})

      setMessage('Simulation stopped')

    } else {

      setRunning(true)

      setInputStates({})

      setMessage(

        'Simulation running · click input contacts to toggle them ON/OFF'

      )

    }

  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null

      if (
        target?.tagName === 'INPUT' ||
        target?.tagName === 'TEXTAREA' ||
        target?.isContentEditable
      ) {
        return
      }

      if (
        (event.key === 'Delete' || event.key === 'Backspace') &&
        selected
      ) {
        event.preventDefault()

        setNodes(previous =>
          previous.filter(node => node.instanceId !== selected)
        )
        setSelected(null)
        setMessage('Selected instruction removed')
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selected])

  async function save() {

    const state = {

      project_name: project,

      instructions: nodes

    }

    localStorage.setItem('plc-state', JSON.stringify(state))

    try {

      const response = await fetch(`${API}/state`, {

        method: 'PUT',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify(state)

      })

      if (!response.ok) throw Error()

      setMessage('Project saved to backend and browser storage')

    } catch {

      setMessage('Saved in browser storage; backend offline')

    }

  }

  function folder(f: FolderNode, depth = 0): ReactNode {

    const expanded = !!open[f.id]

    const children = f.children || []

    const list = (f.instruction_ids || [])

      .map(k => instMap.get(k))

      .filter(

        (instruction): instruction is Inst =>

          !!instruction &&

          `${instruction.name} ${instruction.id} ${instruction.description}`

            .toLowerCase()

            .includes(search.toLowerCase())

      )

    return (

      <div key={f.id}>

        <button

          className="tree-row"

          style={{ paddingLeft: 5 + depth * 12 }}

          onClick={() =>

            setOpen(previous => ({

              ...previous,

              [f.id]: !previous[f.id]

            }))

          }

        >

          {expanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}

          <Folder size={16} className="folder-icon" />

          {f.name}

        </button>

        {expanded && (

          <div className="tree-children">

            {children.map(child => folder(child, depth + 1))}

            {list.map(instruction => (

              <button

                className="instruction"

                key={instruction.id}

                title={`${instruction.tooltip} · click to insert`}

                draggable

                onDragStart={event =>

                  event.dataTransfer.setData(

                    'instructionId',

                    instruction.id

                  )

                }

                onClick={() => add(instruction)}

              >

                <span className="instruction-symbol">

                  {instruction.symbol}

                </span>

                <span className="instruction-name">

                  {instruction.name}

                </span>

                {!instruction.implemented && <i className="planned-dot" />}

              </button>

            ))}

          </div>

        )}

      </div>

    )

  }

  return (

    <div className={`app ${visible ? '' : 'wide'}`}>

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

              onChange={event => setProject(event.target.value)}

              onBlur={() => {

                if (!project.trim()) setProject('Untitled PLC Project')

              }}

            />

          </section>

          <div className="archive-search">

            <Search size={15} />

            <input

              placeholder="Search instructions..."

              value={search}

              onChange={event => {

                setSearch(event.target.value)

                setOpen(previous => ({

                  ...previous,

                  'instruction-folder': true,

                  bits: true,

                  timers: true,

                  counters: true,

                  comparators: true,

                  math: true

                }))

              }}

            />

          </div>

          <div className="archive-tree">

            {archive.folders.map(f => folder(f))}

          </div>

          <footer className="archive-footer">

            <Info size={14} />

            <span>

              Click an instruction to insert it. Drag an instruction onto the

              rung to add it.

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

            <button

              onClick={() => {

                setNodes([])

                setSelected(null)

                setInputStates({})

                setMessage('Rung cleared')

              }}

            >

              <Plus size={15} /> Clear rung

            </button>

            <button

              className={running ? 'run-active' : ''}

              onClick={toggleSimulation}

            >

              {running ? <Square size={15} /> : <Play size={15} />}

              {running ? 'Stop' : 'Run'}

            </button>

          </div>

        </div>

        <div className="editor-tabs">

          <span className="active-tab">Main [OB1]</span>

          <span>Network 1</span>

          <span className="editor-status">{status}</span>

        </div>

        <section className="workspace">

          <div className="network">

            <div className="network-header">

              <span>

                <b className="network-index">1</b> Network 1

              </span>

              <span className="network-comment">Motor control logic</span>

            </div>

            <div className="network-body">

              <div className="rail" />

              <div

                className="rung-content"

                onDragOver={event => event.preventDefault()}

                onDrop={event => {

                  event.preventDefault()

                  const instruction = instMap.get(

                    event.dataTransfer.getData('instructionId')

                  )

                  if (instruction) add(instruction)

                }}

              >

                {nodes.map(node => {

                  const instruction = instMap.get(node.instructionId)

                  if (!instruction) return null

                  const energized = isEnergized(node.instanceId)

                  const contact = isContact(instruction)

                  const inputOn = inputStates[node.instanceId] === true

                  return (

                    <div

                      key={node.instanceId}

                      className={[

                        'ladder-slot',

                        selected === node.instanceId ? 'selected' : '',

                        running && energized ? 'energized' : '',

                        running && contact ? 'sim-input' : ''

                      ]

                        .filter(Boolean)

                        .join(' ')}

                      onClick={() => {

                        setSelected(node.instanceId)

                        if (running && contact) {

                          toggleInput(node)

                        }

                      }}

                      title={

                        running && contact

                          ? `${instruction.name} · input ${

                              inputOn ? 'ON' : 'OFF'

                            } · click to toggle`

                          : `${instruction.name} · click to select`

                      }

                    >

                      <input
                          className="slot-name"
                          value={node.name}
                          aria-label={`Name for ${instruction.name}`}
                          onClick={event => event.stopPropagation()}
                          onChange={event => {
                            const name = event.target.value
                            setNodes(previous =>
                              previous.map(item =>
                                item.instanceId === node.instanceId
                                  ? { ...item, name }
                                  : item
                              )
                            )
                          }}
                          onKeyDown={event => event.stopPropagation()}
                        />

                      <div className="ladder-symbol">{instruction.symbol}</div>

                      <input
                        className="slot-address"
                        value={node.address}
                        aria-label={`Address for ${instruction.name}`}
                        placeholder="Set address"
                        onClick={event => event.stopPropagation()}
                        onChange={event => {
                          const address = event.target.value
                          setNodes(previous =>
                            previous.map(item =>
                              item.instanceId === node.instanceId
                                ? { ...item, address }
                                : item
                            )
                          )
                        }}
                        onKeyDown={event => event.stopPropagation()}
                      />

                      {running && contact && (

                        <div className="sim-state">

                          {inputOn ? 'INPUT ON' : 'INPUT OFF'}

                        </div>

                      )}

                    </div>

                  )

                })}

                <button

                  className="insert-slot"

                  onClick={() => {

                    if (nodes.some(n => isTerminalOutput(n.instructionId))) {

                      setMessage(

                        'The rung already ends with an output instruction. Remove it before adding more logic.'

                      )

                    } else {

                      setMessage('Choose an instruction from the archive')

                    }

                  }}

                >

                  <Plus size={17} /> Insert

                </button>

              </div>

              <div className="rail" />

            </div>

            <div className="network-foot">

              Network 1 · {nodes.length} instruction(s) · select an instruction

              to edit its name or address directly; press Delete to remove

              {running && ' · Simulation RUNNING'}

            </div>

          </div>

        </section>

        <footer className="statusbar">

          <span className="status-dot" />

          <span>{message}</span>

          <span className="spacer" />

          <span>Local prototype</span>

          <span>UTF-8</span>

        </footer>

      </main>

    </div>

  )

}

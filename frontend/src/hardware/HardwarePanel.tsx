import { useRef } from 'react'
import type { Dispatch, PointerEvent as ReactPointerEvent, SetStateAction } from 'react'
import { Cpu, Trash2 } from 'lucide-react'
import type { Bits, HwComponent } from '../types'
import { clamp } from '../util'
import {
  ANCHOR_Y,
  BOX_W,
  CANVAS_H,
  CANVAS_W,
  HW_BY_TYPE,
  HW_CATALOG,
  PLC,
  addressOptions,
  componentSignal,
  makeComponent,
  slotPosition,
  terminalIndex,
  terminalY
} from './catalog'
import type { HwDef } from './catalog'
import { HwGraphic } from './graphics'

type Props = {
  components: HwComponent[]
  setComponents: Dispatch<SetStateAction<HwComponent[]>>
  selectedId: string | null
  onSelect: (id: string | null) => void
  /** Physical actuation state per component id (pressed / flipped). */
  active: Record<string, boolean>
  onActive: (id: string, value: boolean) => void
  /** Resolved PLC input image (shown on the DI LEDs). */
  inputBits: Bits
  /** Output image (Q bits) driven by the ladder. */
  outputBits: Bits
  running: boolean
}

type DragState = {
  id: string
  startX: number
  startY: number
  origX: number
  origY: number
  moved: boolean
}

const DRAG_TYPE = 'application/x-plc-hw-type'

function PlcModule({
  running,
  inputBits,
  outputBits
}: {
  running: boolean
  inputBits: Bits
  outputBits: Bits
}) {
  const { x, y, w, h } = PLC
  return (
    <g fontFamily="Consolas, monospace">
      <rect x={x} y={y} width={w} height={h} rx="10" fill="#26374b" stroke="#0b121b" strokeWidth="2" />
      <rect x={x} y={y} width={w} height="52" rx="10" fill="#1b2a3c" />
      <text x={x + w / 2} y={y + 20} textAnchor="middle" fontSize="12" fontWeight="700" fill="#dbe6f3">
        PLC STUDIO CPU
      </text>
      <circle cx={x + w / 2 - 40} cy={y + 38} r="5" fill={running ? '#3ddc84' : '#3b4b5f'} />
      <text x={x + w / 2 - 31} y={y + 42} fontSize="10" fill="#9fb2c8">RUN</text>
      <circle cx={x + w / 2 + 14} cy={y + 38} r="5" fill={running ? '#3b4b5f' : '#ffb020'} />
      <text x={x + w / 2 + 23} y={y + 42} fontSize="10" fill="#9fb2c8">STOP</text>
      <text x={x + 12} y={y + 76} fontSize="9" fill="#7f93aa">INPUTS</text>
      <text x={x + w - 12} y={y + 76} fontSize="9" fill="#7f93aa" textAnchor="end">OUTPUTS</text>
      {Array.from({ length: 8 }, (_, i) => {
        const ty = terminalY(i)
        const inOn = inputBits[`I0.${i}`] === true
        const outOn = outputBits[`Q0.${i}`] === true
        return (
          <g key={i}>
            <circle cx={x} cy={ty} r="6" fill="#d4a24c" stroke="#7a5a1e" />
            <circle cx={x + 20} cy={ty} r="5" fill={inOn ? '#3ddc84' : '#3b4b5f'} />
            <text x={x + 32} y={ty + 4} fontSize="11" fill="#dbe6f3">{`I0.${i}`}</text>
            <circle cx={x + w} cy={ty} r="6" fill="#d4a24c" stroke="#7a5a1e" />
            <circle cx={x + w - 20} cy={ty} r="5" fill={outOn ? '#3ddc84' : '#3b4b5f'} />
            <text x={x + w - 32} y={ty + 4} fontSize="11" fill="#dbe6f3" textAnchor="end">{`Q0.${i}`}</text>
          </g>
        )
      })}
      <text x={x + w / 2} y={y + h - 14} textAnchor="middle" fontSize="9" fill="#7f93aa">
        8 DI · 8 DO · 24 V DC
      </text>
    </g>
  )
}

export default function HardwarePanel(props: Props) {
  const {
    components,
    setComponents,
    selectedId,
    onSelect,
    active,
    onActive,
    inputBits,
    outputBits,
    running
  } = props

  const canvasRef = useRef<HTMLDivElement>(null)
  const drag = useRef<DragState | null>(null)

  const selected = components.find(c => c.id === selectedId) ?? null
  const selectedDef = selected ? HW_BY_TYPE.get(selected.type) : undefined

  const signalOf = (c: HwComponent) =>
    componentSignal(c, active[c.id] === true, outputBits)

  function addPart(type: string, x?: number, y?: number) {
    const pos = x === undefined || y === undefined ? slotPosition(type, components) : { x, y }
    const part = makeComponent(type, pos.x, pos.y, components)
    if (!part) return
    setComponents(prev => [...prev, part])
    onSelect(part.id)
  }

  function updatePart(id: string, patch: Partial<HwComponent>) {
    setComponents(prev => prev.map(c => (c.id === id ? { ...c, ...patch } : c)))
  }

  function removePart(id: string) {
    setComponents(prev => prev.filter(c => c.id !== id))
    onSelect(null)
  }

  /* Pointer: a press that does not move is a click (actuate), otherwise a drag (move). */
  function onPointerDown(e: ReactPointerEvent<HTMLDivElement>, c: HwComponent, def: HwDef) {
    if (e.button !== 0) return
    e.currentTarget.setPointerCapture(e.pointerId)
    onSelect(c.id)
    drag.current = {
      id: c.id,
      startX: e.clientX,
      startY: e.clientY,
      origX: c.x,
      origY: c.y,
      moved: false
    }
    if (def.kind === 'input' && def.behavior === 'momentary') onActive(c.id, true)
  }

  function onPointerMove(e: ReactPointerEvent<HTMLDivElement>, def: HwDef) {
    const d = drag.current
    if (!d) return
    const dx = e.clientX - d.startX
    const dy = e.clientY - d.startY
    if (!d.moved && Math.hypot(dx, dy) > 5) {
      d.moved = true
      if (def.kind === 'input' && def.behavior === 'momentary') onActive(d.id, false)
    }
    if (d.moved) {
      updatePart(d.id, {
        x: clamp(d.origX + dx, 0, CANVAS_W - BOX_W),
        y: clamp(d.origY + dy, 0, CANVAS_H - 118)
      })
    }
  }

  function endPointer(c: HwComponent, def: HwDef, cancelled: boolean) {
    const d = drag.current
    drag.current = null
    if (!d || def.kind !== 'input') return
    if (def.behavior === 'momentary') {
      onActive(c.id, false)
    } else if (!d.moved && !cancelled) {
      onActive(c.id, active[c.id] !== true)
    }
  }

  /* Wires from each part to the PLC terminal of its address. */
  const wires = components.flatMap(c => {
    const def = HW_BY_TYPE.get(c.type)
    if (!def) return []
    const idx = terminalIndex(c.address, def.kind)
    if (idx === null) return []
    const ty = terminalY(idx)
    const live = signalOf(c)
    const [x1, y1, x2, y2] =
      def.kind === 'input'
        ? [c.x + BOX_W, c.y + ANCHOR_Y, PLC.x, ty]
        : [PLC.x + PLC.w, ty, c.x, c.y + ANCHOR_Y]
    return [
      {
        id: c.id,
        live,
        d: `M${x1} ${y1} C${x1 + 70} ${y1} ${x2 - 70} ${y2} ${x2} ${y2}`
      }
    ]
  })

  const palette = (kind: 'input' | 'output') =>
    HW_CATALOG.filter(d => d.kind === kind).map(def => (
      <button
        key={def.type}
        className="hw-item"
        title={`${def.description} · click or drag onto the board`}
        draggable
        onDragStart={e => e.dataTransfer.setData(DRAG_TYPE, def.type)}
        onClick={() => addPart(def.type)}
      >
        <span className="hw-thumb">
          <HwGraphic type={def.type} on={false} scale={0.42} />
        </span>
        <span className="hw-item-name">{def.name}</span>
      </button>
    ))

  return (
    <>
      <header className="pane-header">
        <span>
          <Cpu size={15} /> Hardware
        </span>
        <span className="pane-header-right">
          <span className={`run-badge ${running ? 'on' : ''}`}>
            {running ? 'PLC RUN' : 'PLC STOP'}
          </span>
          <button
            className="icon-button"
            title="Remove all parts from the board"
            onClick={() => {
              if (components.length && window.confirm('Remove all parts from the board?')) {
                setComponents([])
                onSelect(null)
              }
            }}
          >
            <Trash2 size={15} />
          </button>
        </span>
      </header>

      <div className="hw-body">
        <aside className="hw-palette">
          <div className="hw-group-title">Inputs</div>
          {palette('input')}
          <div className="hw-group-title">Outputs</div>
          {palette('output')}
        </aside>

        <div className="hw-stage" onPointerDown={e => e.target === e.currentTarget && onSelect(null)}>
          <div
            ref={canvasRef}
            className="hw-canvas"
            style={{ width: CANVAS_W, height: CANVAS_H }}
            onDragOver={e => e.preventDefault()}
            onDrop={e => {
              e.preventDefault()
              const type = e.dataTransfer.getData(DRAG_TYPE)
              const rect = canvasRef.current?.getBoundingClientRect()
              if (!type || !rect) return
              addPart(type, e.clientX - rect.left - BOX_W / 2, e.clientY - rect.top - ANCHOR_Y)
            }}
            onPointerDown={e => e.target === e.currentTarget && onSelect(null)}
          >
            <svg className="hw-wires" width={CANVAS_W} height={CANVAS_H}>
              <PlcModule running={running} inputBits={inputBits} outputBits={outputBits} />
              {wires.map(w => (
                <path
                  key={w.id}
                  d={w.d}
                  fill="none"
                  stroke={w.live ? '#3ddc84' : '#6f819a'}
                  strokeWidth={w.id === selectedId ? 4 : 3}
                  strokeLinecap="round"
                />
              ))}
              {components.map(c => {
                const def = HW_BY_TYPE.get(c.type)
                if (!def) return null
                const cx = def.kind === 'input' ? c.x + BOX_W : c.x
                return (
                  <circle
                    key={c.id}
                    cx={cx}
                    cy={c.y + ANCHOR_Y}
                    r="5"
                    fill="#d4a24c"
                    stroke="#7a5a1e"
                  />
                )
              })}
            </svg>

            {components.map(c => {
              const def = HW_BY_TYPE.get(c.type)
              if (!def) return null
              const signal = signalOf(c)
              const visualOn = def.kind === 'input' ? active[c.id] === true : signal
              const valid = terminalIndex(c.address, def.kind) !== null
              return (
                <div
                  key={c.id}
                  className={['hw-comp', def.kind, c.id === selectedId ? 'selected' : ''].filter(Boolean).join(' ')}
                  style={{ left: c.x, top: c.y, width: BOX_W }}
                  title={`${def.name} · ${def.description}`}
                  onPointerDown={e => onPointerDown(e, c, def)}
                  onPointerMove={e => onPointerMove(e, def)}
                  onPointerUp={() => endPointer(c, def, false)}
                  onPointerCancel={() => endPointer(c, def, true)}
                >
                  <HwGraphic type={c.type} on={visualOn} />
                  <div className="hw-label">{c.label}</div>
                  <div className={`hw-addr ${valid ? '' : 'bad'} ${valid && signal ? 'on' : ''}`}>
                    {valid ? c.address.toUpperCase() : 'no address'}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      <div className="hw-props">
        {selected && selectedDef ? (
          <>
            <span className="hw-props-title">{selectedDef.name}</span>
            <label>
              Label
              <input value={selected.label} onChange={e => updatePart(selected.id, { label: e.target.value })} />
            </label>
            <label>
              Address
              <select value={selected.address.toUpperCase()} onChange={e => updatePart(selected.id, { address: e.target.value })}>
                <option value="">— unassigned —</option>
                {addressOptions(selectedDef.kind).map(a => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </label>
            <span className={`hw-signal ${signalOf(selected) ? 'on' : ''}`}>
              {signalOf(selected) ? 'ON' : 'OFF'}
            </span>
            <button className="hw-remove" onClick={() => removePart(selected.id)}>
              <Trash2 size={13} /> Remove
            </button>
          </>
        ) : (
          <span className="hw-hint">
            Drag parts onto the board, wire them by choosing an address, press Run, then click the inputs. Drag a part to move it.
          </span>
        )}
      </div>
    </>
  )
}
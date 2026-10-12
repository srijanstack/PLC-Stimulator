import type { Bits, HwComponent, HwKind } from '../types'
import  {   clamp,   createId } from '../util'
import { normalizeAddress } from '../plc/engine'

export type HwDef = {
  type: string
  name: string
  /** Prefix for auto-generated labels. */
  tag: string
  kind: HwKind
  /** Inputs only: momentary = active while held, latching = click toggles. */
  behavior: 'momentary' | 'latching' | 'none'
  /** Wired normally-closed: the PLC input is ON at rest and OFF when actuated. */
  normallyClosed: boolean
  description: string
}

export const HW_CATALOG: HwDef[] = [
  {
    type: 'push_no',
    name: 'Pushbutton (NO)',
    tag: 'PB_NO',
    kind: 'input',
    behavior: 'momentary',
    normallyClosed: false,
    description: 'Momentary start button. Input is ON only while held.'
  },
  {
    type: 'push_nc',
    name: 'Pushbutton (NC)',
    tag: 'PB_NC',
    kind: 'input',
    behavior: 'momentary',
    normallyClosed: true,
    description: 'Momentary stop button, wired NC: input is ON at rest, OFF while pressed.'
  },
  {
    type: 'toggle',
    name: 'Toggle Switch',
    tag: 'Switch',
    kind: 'input',
    behavior: 'latching',
    normallyClosed: false,
    description: 'Click to flip. Stays where you leave it.'
  },
  {
    type: 'estop',
    name: 'E-Stop',
    tag: 'EStop',
    kind: 'input',
    behavior: 'latching',
    normallyClosed: true,
    description: 'Latching mushroom button, wired NC: input is ON at rest, OFF when pressed in.'
  },
  {
    type: 'limit',
    name: 'Limit Switch',
    tag: 'Limit',
    kind: 'input',
    behavior: 'latching',
    normallyClosed: false,
    description: 'Click to toggle, simulating the machine reaching the switch.'
  },
  {
    type: 'prox',
    name: 'Proximity Sensor',
    tag: 'Prox',
    kind: 'input',
    behavior: 'latching',
    normallyClosed: false,
    description: 'Click to toggle "target detected".'
  },
  {
    type: 'led_green',
    name: 'Green Lamp',
    tag: 'Lamp_G',
    kind: 'output',
    behavior: 'none',
    normallyClosed: false,
    description: 'Pilot lamp that lights when its output is ON.'
  },
  {
    type: 'led_red',
    name: 'Red Lamp',
    tag: 'Lamp_R',
    kind: 'output',
    behavior: 'none',
    normallyClosed: false,
    description: 'Pilot lamp that lights when its output is ON.'
  },
  {
    type: 'led_yellow',
    name: 'Yellow Lamp',
    tag: 'Lamp_Y',
    kind: 'output',
    behavior: 'none',
    normallyClosed: false,
    description: 'Pilot lamp that lights when its output is ON.'
  },
  {
    type: 'buzzer',
    name: 'Buzzer',
    tag: 'Buzzer',
    kind: 'output',
    behavior: 'none',
    normallyClosed: false,
    description: 'Sounds (animates) when its output is ON.'
  },
  {
    type: 'motor',
    name: 'Motor',
    tag: 'Motor',
    kind: 'output',
    behavior: 'none',
    normallyClosed: false,
    description: 'Spins when its output is ON.'
  },
  {
    type: 'valve',
    name: 'Solenoid Valve',
    tag: 'Valve',
    kind: 'output',
    behavior: 'none',
    normallyClosed: false,
    description: 'Opens when its output is ON.'
  }
]

export const HW_BY_TYPE = new Map(HW_CATALOG.map(d => [d.type, d]))

/* ---- Board geometry (shared by the panel and the graphics) ---- */

export const BOX_W = 120
export const BOX_H = 118
/** Y offset of the terminal on every part. */
export const ANCHOR_Y = 46
export const CANVAS_W = 1000
export const CANVAS_H = 640

export const PLC = { x: 400, y: 30, w: 200, h: 460 }
export const terminalY = (index: number) => PLC.y + 90 + index * 40

/* ---- Addresses ---- */

const INPUT_RE = /^I0\.([0-7])$/
const OUTPUT_RE = /^Q0\.([0-7])$/

/** Terminal index 0-7 for a valid address of the right kind, otherwise null. */
export function terminalIndex(address: string, kind: HwKind): number | null {
  const match = (kind === 'input' ? INPUT_RE : OUTPUT_RE).exec(
    normalizeAddress(address)
  )
  return match ? Number(match[1]) : null
}

export const addressOptions = (kind: HwKind) =>
  Array.from({ length: 8 }, (_, i) => `${kind === 'input' ? 'I' : 'Q'}0.${i}`)

function nextFreeAddress(kind: HwKind, components: HwComponent[]) {
  const used = new Set(
    components
      .filter(c => HW_BY_TYPE.get(c.type)?.kind === kind)
      .map(c => normalizeAddress(c.address))
  )
  return addressOptions(kind).find(a => !used.has(a)) ?? ''
}

/* ---- Signals ---- */

/** The level the PLC input sees for a given physical actuation. */
export const hwInputValue = (def: HwDef, actuated: boolean) =>
  def.normallyClosed ? !actuated : actuated

/** Electrical level at the part's terminal. */
export function componentSignal(
  component: HwComponent,
  actuated: boolean,
  outputs: Bits
): boolean {
  const def = HW_BY_TYPE.get(component.type)
  if (!def) return false
  if (def.kind === 'input') return hwInputValue(def, actuated)
  return outputs[normalizeAddress(component.address)] === true
}

/* ---- Creation / persistence ---- */

export function makeComponent(
  type: string,
  x: number,
  y: number,
  existing: HwComponent[]
): HwComponent | null {
  const def = HW_BY_TYPE.get(type)
  if (!def) return null
  const sameType = existing.filter(c => c.type === type).length
  return {
    id: createId(),
    type,
    x: clamp(Math.round(x), 0, CANVAS_W - BOX_W),
    y: clamp(Math.round(y), 0, CANVAS_H - BOX_H),
    address: nextFreeAddress(def.kind, existing),
    label: `${def.tag}_${sameType + 1}`
  }
}

/** Where a part lands when added by clicking the palette. */
export function slotPosition(type: string, existing: HwComponent[]) {
  const kind = HW_BY_TYPE.get(type)?.kind ?? 'input'
  const count = existing.filter(
    c => HW_BY_TYPE.get(c.type)?.kind === kind
  ).length
  const col = Math.floor(count / 4) % 2
  const row = count % 4
  const baseX = kind === 'input' ? 30 : 650
  return { x: baseX + col * 160, y: 30 + row * 140 }
}

export function makeDefaultHardware(): HwComponent[] {
  return [
    {
      id: createId(),
      type: 'push_no',
      x: 60,
      y: 110,
      address: 'I0.0',
      label: 'Start_PB'
    },
    {
      id: createId(),
      type: 'motor',
      x: 680,
      y: 80,
      address: 'Q0.0',
      label: 'Motor'
    },
    {
      id: createId(),
      type: 'led_green',
      x: 680,
      y: 240,
      address: 'Q0.0',
      label: 'Running_Lamp'
    }
  ]
}

/** Validates hardware loaded from storage. Returns null if it is not an array. */
export function sanitizeHardware(raw: unknown): HwComponent[] | null {
  if (!Array.isArray(raw)) return null
  const out: HwComponent[] = []
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue
    const r = item as Record<string, unknown>
    if (typeof r.type !== 'string' || !HW_BY_TYPE.has(r.type)) continue
    out.push({
      id: typeof r.id === 'string' ? r.id : createId(),
      type: r.type,
      x: clamp(typeof r.x === 'number' ? r.x : 0, 0, CANVAS_W - BOX_W),
      y: clamp(typeof r.y === 'number' ? r.y : 0, 0, CANVAS_H - BOX_H),
      address: typeof r.address === 'string' ? r.address : '',
      label: typeof r.label === 'string' ? r.label : r.type
    })
  }
  return out
}
export type Inst = {
  id: string
  name: string
  symbol: string
  kind: string
  implemented: boolean
  description: string
  default_address: string
  tooltip: string
}

export type FolderNode = {
  id: string
  name: string
  instruction_ids?: string[]
  children?: FolderNode[]
}

export type Archive = {
  folders: FolderNode[]
  instructions: Inst[]
}

/** One instruction placed on a rung. */
export type Node = {
  instanceId: string
  instructionId: string
  address: string
  name: string
}

/** One network (rung) of the ladder program. Networks run top to bottom each scan. */
export type Network = {
  id: string
  title: string
  comment: string
  collapsed: boolean
  nodes: Node[]
}

/** Boolean image table: address ("I0.0", "Q0.3", "M0.0") -> value. */
export type Bits = Record<string, boolean>

export type HwKind = 'input' | 'output'

/** A part placed on the hardware board. */
export type HwComponent = {
  id: string
  type: string
  x: number
  y: number
  /** PLC address this part is wired to: I0.0-I0.7 for inputs, Q0.0-Q0.7 for outputs. */
  address: string
  label: string
}
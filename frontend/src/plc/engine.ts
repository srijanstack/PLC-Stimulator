import type { Bits, Inst, Network, Node } from '../types'

export const normalizeAddress = (address: string) =>
  address.trim().toUpperCase()

/* Output Coil, Set Bit and Reset Bit all end the rung. */
export const isTerminalOutput = (instructionId: string) =>
  ['coil_output', 'coil_set', 'coil_reset'].includes(instructionId)

export const isContact = (instruction?: Inst) => instruction?.kind === 'contact'

/** A bit is ON if either the input image or the internal memory says so. */
export const readBit = (address: string, inputs: Bits, memory: Bits) =>
  inputs[address] === true || memory[address] === true

export type ScanResult = {
  /** Output (Q) and marker (M) bits after this scan. */
  memory: Bits
  /** Per-instruction "power flow reaches and passes through" flag. */
  energized: Bits
}

/**
 * One PLC scan of a single series rung, left to right.
 *
 *   NO contact  conducts when its bit is ON
 *   NC contact  conducts when its bit is OFF
 *   Output coil writes the rung result to its address
 *   Set bit     latches ON while the rung is true
 *   Reset bit   latches OFF while the rung is true
 *
 * `memory` is carried from scan to scan, which is what makes Set/Reset latch.
 */
export function scan(
  nodes: Node[],
  instMap: Map<string, Inst>,
  inputs: Bits,
  memory: Bits
): ScanResult {
  const next: Bits = { ...memory }
  const energized: Bits = {}
  let power = true

  for (const node of nodes) {
    const instruction = instMap.get(node.instructionId)
    const address = normalizeAddress(node.address)

    if (!instruction) {
      power = false
      energized[node.instanceId] = false
      continue
    }

    if (instruction.kind === 'contact') {
      const bit = readBit(address, inputs, next)
      const conducts = node.instructionId === 'contact_nc' ? !bit : bit
      power = power && conducts
      energized[node.instanceId] = power
    } else if (instruction.kind === 'coil') {
      energized[node.instanceId] = power
      if (address) {
        if (node.instructionId === 'coil_output') next[address] = power
        else if (node.instructionId === 'coil_set') {
          if (power) next[address] = true
        } else if (node.instructionId === 'coil_reset') {
          if (power) next[address] = false
        }
      }
      // Nothing can follow a terminal output.
      power = false
    } else {
      energized[node.instanceId] = false
      power = false
    }
  }

  return { memory: next, energized }
}

/**
 * One full PLC scan: networks run top to bottom and share one memory, so a bit
 * written in Network 1 is already visible to Network 2 in the same scan.
 */
export function scanNetworks(
  networks: Network[],
  instMap: Map<string, Inst>,
  inputs: Bits,
  memory: Bits
): ScanResult {
  let mem = memory
  const energized: Bits = {}
  for (const network of networks) {
    const result = scan(network.nodes, instMap, inputs, mem)
    mem = result.memory
    Object.assign(energized, result.energized)
  }
  return { memory: mem, energized }
}
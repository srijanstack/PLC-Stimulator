import { INSTRUCTION_BY_ID } from './catalog.js'

export class HttpError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message)
  }
}

const INPUT_ADDRESS = /^I0\.[0-7]$/i
const OUTPUT_ADDRESS = /^Q0\.[0-7]$/i

/** Validates addresses and enforces "contacts before output instructions". */
export function validateLadder(instructions: Record<string, unknown>[]): void {
  let outputSeen = false

  instructions.forEach((node, index) => {
    const n = index + 1
    const instructionId =
      typeof node.instructionId === 'string' ? node.instructionId : ''
    const instruction = INSTRUCTION_BY_ID.get(instructionId)

    if (!instruction) {
      throw new HttpError(422, `Instruction ${n}: unknown instruction id.`)
    }

    const address = String(node.address ?? '').trim()

    // Output coil, Set Bit, and Reset Bit all terminate the rung.
    if (instruction.kind === 'contact') {
      if (outputSeen) {
        throw new HttpError(
          422,
          `Instruction ${n}: input contacts cannot appear after an output, Set Bit, or Reset Bit.`
        )
      }
      if (!INPUT_ADDRESS.test(address)) {
        throw new HttpError(
          422,
          `Instruction ${n}: input contacts must use I0.0 through I0.7.`
        )
      }
    } else if (instruction.kind === 'coil') {
      outputSeen = true
      if (instructionId === 'coil_output' && !OUTPUT_ADDRESS.test(address)) {
        throw new HttpError(
          422,
          `Instruction ${n}: output coils must use Q0.0 through Q0.7.`
        )
      }
    }
  })
}

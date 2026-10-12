  import type { AgentContext } from './schemas.js'

  const norm = (address: string) => address.trim().toUpperCase()

  /**
   * Deterministic checks between the ladder and the hardware board.
   * Computed in code and handed to the model as facts, because small local
   * models are unreliable at cross-referencing addresses themselves.
   */
  export function checkWiring(ctx: AgentContext): string[] {
    const issues: string[] = []

    const inputsOnBoard = new Set(
      ctx.hardware.filter(h => h.kind === 'input').map(h => norm(h.address))
    )
    const outputsOnBoard = new Set(
      ctx.hardware.filter(h => h.kind === 'output').map(h => norm(h.address))
    )
    const contactAddrs = new Set(
      ctx.ladder.filter(i => i.kind === 'contact').map(i => norm(i.address))
    )
    const coilAddrs = new Set(
      ctx.ladder.filter(i => i.kind === 'coil').map(i => norm(i.address))
    )

    for (const h of ctx.hardware) {
      if (!h.address.trim()) {
        issues.push(`${h.label} has no address, so it is not wired to the PLC.`)
      }
    }

    for (const i of ctx.ladder) {
      const a = norm(i.address)
      if (!a) {
        issues.push(`${i.name} on the rung has no address.`)
      } else if (i.kind === 'contact' && /^I0\.[0-7]$/.test(a) && !inputsOnBoard.has(a)) {
        issues.push(`${i.name} reads ${a}, but no input part on the board is wired to it.`)
      } else if (i.kind === 'coil' && /^Q0\.[0-7]$/.test(a) && !outputsOnBoard.has(a)) {
        issues.push(`${i.name} drives ${a}, but no output part on the board uses it.`)
      }
    }

    for (const h of ctx.hardware) {
      const a = norm(h.address)
      if (!a) continue
      if (h.kind === 'output' && !coilAddrs.has(a)) {
        issues.push(`${h.label} is wired to ${a}, but no coil in the ladder writes it.`)
      }
      if (h.kind === 'input' && !contactAddrs.has(a)) {
        issues.push(`${h.label} is wired to ${a}, but no contact in the ladder reads it.`)
      }
    }

    if (!ctx.ladder.some(i => i.kind === 'coil')) {
      issues.push('The rung has no output coil, so nothing is ever driven.')
    }

    return issues
  }

import type { Network, Node } from '../types'
import { createId } from '../util'

export function makeNetwork(title = '', nodes: Node[] = []): Network {
  return { id: createId(), title, comment: '', collapsed: false, nodes }
}

export function makeDefaultNetworks(): Network[] {
  return [
    makeNetwork('Motor control logic', [
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
  ]
}

function sanitizeNodes(raw: unknown): Node[] {
  if (!Array.isArray(raw)) return []
  const out: Node[] = []
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue
    const r = item as Record<string, unknown>
    if (typeof r.instructionId !== 'string') continue
    out.push({
      instanceId: typeof r.instanceId === 'string' ? r.instanceId : createId(),
      instructionId: r.instructionId,
      address: typeof r.address === 'string' ? r.address : '',
      name: typeof r.name === 'string' ? r.name : r.instructionId
    })
  }
  return out
}

/**
 * Reads the networks out of a saved project.
 *  - New format: `networks: Network[]`
 *  - Old format: a flat `instructions: Node[]` becomes Network 1
 * Returns null when the save holds no ladder, so the caller keeps its defaults.
 */
export function loadNetworks(state: unknown): Network[] | null {
  if (!state || typeof state !== 'object') return null
  const s = state as Record<string, unknown>

  if (Array.isArray(s.networks) && s.networks.length) {
    const out: Network[] = []
    for (const item of s.networks) {
      if (!item || typeof item !== 'object') continue
      const r = item as Record<string, unknown>
      out.push({
        id: typeof r.id === 'string' ? r.id : createId(),
        title: typeof r.title === 'string' ? r.title : '',
        comment: typeof r.comment === 'string' ? r.comment : '',
        collapsed: r.collapsed === true,
        nodes: sanitizeNodes(r.nodes)
      })
    }
    return out.length ? out : null
  }

  if (Array.isArray(s.instructions) && s.instructions.length) {
    return [makeNetwork('Motor control logic', sanitizeNodes(s.instructions))]
  }

  return null
}
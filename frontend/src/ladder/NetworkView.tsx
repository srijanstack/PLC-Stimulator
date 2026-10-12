import {
  ArrowDown,
  ArrowUp,
  ChevronDown,
  ChevronRight,
  Eraser,
  Plus,
  Trash2
} from 'lucide-react'
import type { Bits, Inst, Network, Node } from '../types'
import { isContact, normalizeAddress, readBit } from '../plc/engine'

type Props = {
  network: Network
  index: number
  total: number
  /** This is the network new instructions are inserted into. */
  active: boolean
  running: boolean
  instMap: Map<string, Inst>
  energized: Bits
  inputBits: Bits
  memory: Bits
  forced: Bits
  selectedNode: string | null
  onActivate: () => void
  onSelectNode: (instanceId: string) => void
  onForce: (node: Node) => void
  onPatch: (patch: Partial<Network>) => void
  onPatchNode: (instanceId: string, patch: Partial<Node>) => void
  onMove: (direction: -1 | 1) => void
  onAddBelow: () => void
  onClear: () => void
  onDelete: () => void
  onDropInstruction: (instructionId: string) => void
  onInsertClick: () => void
}

export default function NetworkView(p: Props) {
  const { network, index, total, running } = p
  const number = index + 1

  return (
    <div
      id={`net-${network.id}`}
      className={`network ${p.active ? 'active' : ''}`}
      onPointerDown={p.onActivate}
    >
      <div className="network-header">
        <span className="network-title">
          <button
            className="net-btn"
            title={network.collapsed ? 'Expand network' : 'Collapse network'}
            onClick={() => p.onPatch({ collapsed: !network.collapsed })}
          >
            {network.collapsed ? (
              <ChevronRight size={14} />
            ) : (
              <ChevronDown size={14} />
            )}
          </button>
          <b className="network-index">{number}</b>
          <span className="network-label">Network {number}</span>
          <input
            className="network-title-input"
            value={network.title}
            placeholder="Title..."
            aria-label={`Title of network ${number}`}
            onChange={e => p.onPatch({ title: e.target.value })}
            onKeyDown={e => e.stopPropagation()}
          />
          {network.collapsed && (
            <span className="network-comment">
              {network.nodes.length} instruction(s)
            </span>
          )}
        </span>

        <span className="network-tools">
          <button
            className="net-btn"
            title="Move network up"
            disabled={index === 0}
            onClick={() => p.onMove(-1)}
          >
            <ArrowUp size={14} />
          </button>
          <button
            className="net-btn"
            title="Move network down"
            disabled={index === total - 1}
            onClick={() => p.onMove(1)}
          >
            <ArrowDown size={14} />
          </button>
          <button
            className="net-btn"
            title="Insert a new network below"
            onClick={p.onAddBelow}
          >
            <Plus size={14} />
          </button>
          <button
            className="net-btn"
            title="Clear this network"
            disabled={!network.nodes.length}
            onClick={p.onClear}
          >
            <Eraser size={14} />
          </button>
          <button
            className="net-btn danger"
            title={total === 1 ? 'The last network cannot be deleted' : 'Delete network'}
            disabled={total === 1}
            onClick={p.onDelete}
          >
            <Trash2 size={14} />
          </button>
        </span>
      </div>

      {!network.collapsed && (
        <>
          <input
            className="network-comment-input"
            value={network.comment}
            placeholder="Comment..."
            aria-label={`Comment of network ${number}`}
            onChange={e => p.onPatch({ comment: e.target.value })}
            onKeyDown={e => e.stopPropagation()}
          />

          <div className="network-body">
            <div className="rail" />

            <div
              className="rung-content"
              onDragOver={e => e.preventDefault()}
              onDrop={e => {
                e.preventDefault()
                const id = e.dataTransfer.getData('instructionId')
                if (id) p.onDropInstruction(id)
              }}
            >
              {network.nodes.map(node => {
                const instruction = p.instMap.get(node.instructionId)
                if (!instruction) return null

                const address = normalizeAddress(node.address)
                const isEnergized = running && p.energized[node.instanceId] === true
                const contact = isContact(instruction)
                const inputOn = readBit(address, p.inputBits, p.memory)
                const isForced = p.forced[address] === true

                return (
                  <div
                    key={node.instanceId}
                    className={[
                      'ladder-slot',
                      p.selectedNode === node.instanceId ? 'selected' : '',
                      isEnergized ? 'energized' : '',
                      running && contact ? 'sim-input' : ''
                    ]
                      .filter(Boolean)
                      .join(' ')}
                    onClick={() => {
                      p.onSelectNode(node.instanceId)
                      if (running && contact) p.onForce(node)
                    }}
                    title={
                      running && contact
                        ? `${instruction.name} · ${address || 'no address'} ${
                            inputOn ? 'ON' : 'OFF'
                          } · click to force ON / release`
                        : `${instruction.name} · click to select`
                    }
                  >
                    <input
                      className="slot-name"
                      value={node.name}
                      aria-label={`Name for ${instruction.name}`}
                      onClick={e => e.stopPropagation()}
                      onChange={e =>
                        p.onPatchNode(node.instanceId, { name: e.target.value })
                      }
                      onKeyDown={e => e.stopPropagation()}
                    />

                    <div className="ladder-symbol">{instruction.symbol}</div>

                    <input
                      className="slot-address"
                      value={node.address}
                      aria-label={`Address for ${instruction.name}`}
                      placeholder="Set address"
                      onClick={e => e.stopPropagation()}
                      onChange={e =>
                        p.onPatchNode(node.instanceId, { address: e.target.value })
                      }
                      onKeyDown={e => e.stopPropagation()}
                    />

                    {running && contact && (
                      <div className="sim-state">
                        {isForced ? 'FORCED ON' : inputOn ? 'INPUT ON' : 'INPUT OFF'}
                      </div>
                    )}
                  </div>
                )
              })}

              <button className="insert-slot" onClick={p.onInsertClick}>
                <Plus size={17} /> Insert
              </button>
            </div>

            <div className="rail" />
          </div>

          <div className="network-foot">
            Network {number} · {network.nodes.length} instruction(s) · select an
            instruction to edit its name or address directly; press Delete to
            remove
            {running && ' · Simulation RUNNING'}
          </div>
        </>
      )}
    </div>
  )
}
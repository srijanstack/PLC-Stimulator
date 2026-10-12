import { useEffect, useRef, useState } from 'react'
import type { Bits, Inst, Network } from '../types'
import { SCAN_MS } from '../config'
import { scanNetworks } from './engine'

type Args = {
    running: boolean
    networks: Network[]
    instMap: Map<string, Inst>
    /** Resolved input image (hardware switches + ladder forces). */
    inputs: Bits
}

function sameBits(a: Bits, b: Bits) {
    const ka = Object.keys(a)
    if (ka.length !== Object.keys(b).length) return false
    return ka.every(k => a[k] === b[k])
}

/**
 * Runs the scan engine every SCAN_MS while `running` is true.
 * Stopping the PLC clears all outputs and latched bits.
 */
export function usePlcRuntime(args: Args) {
    const [memory, setMemory] = useState<Bits>({})
    const [energized, setEnergized] = useState<Bits>({})
    const latest = useRef(args)

    // Always scan with the newest ladder/inputs without restarting the timer.
    useEffect(() => {
        latest.current = args
    })

    const { running } = args

    useEffect(() => {
        if (!running) return

        let mem: Bits = {}

        const tick = () => {
            const { networks, instMap, inputs } = latest.current
            if (!Array.isArray(networks)) {
                console.error('usePlcRuntime: expected networks array, got', networks)
                return
            }
            const result = scanNetworks(networks, instMap, inputs, mem)

            mem = result.memory
            setMemory(prev => (sameBits(prev, result.memory) ? prev : result.memory))
            setEnergized(prev =>
                sameBits(prev, result.energized) ? prev : result.energized
            )
        }

        tick()
        const timer = window.setInterval(tick, SCAN_MS)

        return () => {
            window.clearInterval(timer)
            setMemory({})
            setEnergized({})
        }
    }, [running])

    return { memory, energized }
}
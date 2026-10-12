import type { Archive, Inst } from '../types'

export const defaultArchive: Archive = {
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
        { id: 'function-blocks', name: 'Function Blocks', instruction_ids: [] },
        { id: 'program-control', name: 'Program Control', instruction_ids: [] }
      ]
    }
  ],
  instructions: []
}

const planned = (
  id: string,
  name: string,
  symbol: string,
  kind: string,
  default_address: string,
  tooltip: string
): Inst => ({
  id,
  name,
  symbol,
  kind,
  implemented: false,
  description: 'Catalog only; execution not implemented.',
  default_address,
  tooltip
})

/** Used when the backend archive endpoint is unreachable. */
export const fallbackInstructions: Inst[] = [
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
    implemented: true,
    description: 'Latches the bit ON while the rung is true.',
    default_address: 'Q0.1',
    tooltip: 'Set coil'
  },
  {
    id: 'coil_reset',
    name: 'Reset Bit',
    symbol: '--(R)--',
    kind: 'coil',
    implemented: true,
    description: 'Latches the bit OFF while the rung is true.',
    default_address: 'Q0.1',
    tooltip: 'Reset coil'
  },
  planned('timer_ton', 'TON', 'TON', 'timer', 'T1', 'On-delay timer'),
  planned('timer_tof', 'TOF', 'TOF', 'timer', 'T2', 'Off-delay timer'),
  planned('timer_tp', 'TP', 'TP', 'timer', 'T3', 'Pulse timer'),
  planned('counter_ctu', 'CTU', 'CTU', 'counter', 'C1', 'Count up'),
  planned('counter_ctd', 'CTD', 'CTD', 'counter', 'C2', 'Count down'),
  planned('compare_eq', 'Equal', '==', 'compare', '', 'Compare equal'),
  planned('compare_gt', 'Greater Than', '>', 'compare', '', 'Compare greater than'),
  planned('compare_lt', 'Less Than', '<', 'compare', '', 'Compare less than'),
  planned('math_add', 'Add', 'ADD', 'math', '', 'Add values'),
  planned('math_sub', 'Subtract', 'SUB', 'math', '', 'Subtract values'),
  planned('math_mul', 'Multiply', 'MUL', 'math', '', 'Multiply values'),
  planned('math_div', 'Divide', 'DIV', 'math', '', 'Divide values')
]
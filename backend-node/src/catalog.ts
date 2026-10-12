export type Instruction = {
  id: string
  name: string
  symbol: string
  kind: string
  implemented: boolean
  description: string
  default_address: string
  tooltip: string
}

export const INSTRUCTIONS: Instruction[] = [
  { id: 'contact_no', name: 'NO Contact', symbol: '--| |--', kind: 'contact', implemented: true, description: 'Passes logic when the referenced Boolean value is ON.', default_address: 'I0.0', tooltip: 'Normally Open contact' },
  { id: 'contact_nc', name: 'NC Contact', symbol: '--|/|--', kind: 'contact', implemented: true, description: 'Passes logic when the referenced Boolean value is OFF.', default_address: 'I0.1', tooltip: 'Normally Closed contact' },
  { id: 'coil_output', name: 'Output Coil', symbol: '--( )--', kind: 'coil', implemented: true, description: 'Writes the rung result to an output or Boolean tag.', default_address: 'Q0.0', tooltip: 'Output coil' },
  { id: 'coil_set', name: 'Set Bit', symbol: '--(S)--', kind: 'coil', implemented: true, description: 'Latches the bit ON while the rung is true.', default_address: 'Q0.1', tooltip: 'Set coil' },
  { id: 'coil_reset', name: 'Reset Bit', symbol: '--(R)--', kind: 'coil', implemented: true, description: 'Latches the bit OFF while the rung is true.', default_address: 'Q0.1', tooltip: 'Reset coil' },
  { id: 'timer_ton', name: 'TON', symbol: 'TON', kind: 'timer', implemented: false, description: 'On-delay timer; execution not implemented.', default_address: 'T1', tooltip: 'On-delay timer' },
  { id: 'timer_tof', name: 'TOF', symbol: 'TOF', kind: 'timer', implemented: false, description: 'Off-delay timer; execution not implemented.', default_address: 'T2', tooltip: 'Off-delay timer' },
  { id: 'timer_tp', name: 'TP', symbol: 'TP', kind: 'timer', implemented: false, description: 'Pulse timer; execution not implemented.', default_address: 'T3', tooltip: 'Pulse timer' },
  { id: 'counter_ctu', name: 'CTU', symbol: 'CTU', kind: 'counter', implemented: false, description: 'Count-up counter; execution not implemented.', default_address: 'C1', tooltip: 'Count up' },
  { id: 'counter_ctd', name: 'CTD', symbol: 'CTD', kind: 'counter', implemented: false, description: 'Count-down counter; execution not implemented.', default_address: 'C2', tooltip: 'Count down' },
  { id: 'compare_eq', name: 'Equal', symbol: '==', kind: 'compare', implemented: false, description: 'Equality comparison; execution not implemented.', default_address: '', tooltip: 'Compare equal' },
  { id: 'compare_gt', name: 'Greater Than', symbol: '>', kind: 'compare', implemented: false, description: 'Greater-than comparison; execution not implemented.', default_address: '', tooltip: 'Compare greater than' },
  { id: 'compare_lt', name: 'Less Than', symbol: '<', kind: 'compare', implemented: false, description: 'Less-than comparison; execution not implemented.', default_address: '', tooltip: 'Compare less than' },
  { id: 'math_add', name: 'Add', symbol: 'ADD', kind: 'math', implemented: false, description: 'Addition; execution not implemented.', default_address: '', tooltip: 'Add values' },
  { id: 'math_sub', name: 'Subtract', symbol: 'SUB', kind: 'math', implemented: false, description: 'Subtraction; execution not implemented.', default_address: '', tooltip: 'Subtract values' },
  { id: 'math_mul', name: 'Multiply', symbol: 'MUL', kind: 'math', implemented: false, description: 'Multiplication; execution not implemented.', default_address: '', tooltip: 'Multiply values' },
  { id: 'math_div', name: 'Divide', symbol: 'DIV', kind: 'math', implemented: false, description: 'Division; execution not implemented.', default_address: '', tooltip: 'Divide values' }
]

export const INSTRUCTION_BY_ID = new Map(INSTRUCTIONS.map(i => [i.id, i]))

export const FOLDERS = [
  {
    id: 'instruction-folder',
    name: 'Instruction Folder',
    children: [
      { id: 'bits', name: 'Bits', instruction_ids: ['contact_no', 'contact_nc', 'coil_output', 'coil_set', 'coil_reset'] },
      { id: 'timers', name: 'Timers', instruction_ids: ['timer_ton', 'timer_tof', 'timer_tp'] },
      { id: 'counters', name: 'Counters', instruction_ids: ['counter_ctu', 'counter_ctd'] },
      { id: 'comparators', name: 'Comparators', instruction_ids: ['compare_eq', 'compare_gt', 'compare_lt'] },
      { id: 'math', name: 'Math Operators', instruction_ids: ['math_add', 'math_sub', 'math_mul', 'math_div'] },
      { id: 'function-blocks', name: 'Function Blocks', instruction_ids: [] },
      { id: 'program-control', name: 'Program Control', instruction_ids: [] }
    ]
  }
]

export const createId = () =>
  `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`

export const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value))
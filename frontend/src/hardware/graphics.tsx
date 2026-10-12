import type { ReactNode } from 'react'

/*
 * All parts are drawn in a 120 x 92 box.
 * Inputs have their terminal on the right edge (120, 46);
 * outputs have it on the left edge (0, 46).
 * `on` means: actuated for inputs, energized for outputs.
 */

const EDGE = '#5b6d82'
const WIRE = '#6b7f96'

function Plate({ children }: { children: ReactNode }) {
  return (
    <>
      <line x1="88" y1="46" x2="120" y2="46" stroke={WIRE} strokeWidth="3" />
      <rect
        x="18"
        y="14"
        width="70"
        height="64"
        rx="8"
        fill="#cfd8e3"
        stroke={EDGE}
      />
      {children}
    </>
  )
}

function PushButton({ on, red }: { on: boolean; red: boolean }) {
  const up = red ? '#d6453d' : '#2fa65a'
  const down = red ? '#a52f29' : '#1e7a40'
  return (
    <Plate>
      <circle cx="53" cy="46" r="24" fill="#8fa3ba" />
      <circle
        cx="53"
        cy={on ? 48 : 44}
        r="18"
        fill={on ? down : up}
        stroke="#0000003a"
      />
      <ellipse cx="47" cy={on ? 42 : 38} rx="6" ry="4" fill="#ffffff55" />
    </Plate>
  )
}

function Toggle({ on }: { on: boolean }) {
  return (
    <Plate>
      <rect x="38" y="36" width="30" height="20" rx="4" fill="#8fa3ba" />
      <g transform={`rotate(${on ? -28 : 28} 53 46)`}>
        <rect x="50" y="14" width="6" height="32" rx="3" fill="#445468" />
        <circle cx="53" cy="14" r="7" fill={on ? '#2fa65a' : '#6b7f96'} />
      </g>
    </Plate>
  )
}

function EStop({ on }: { on: boolean }) {
  return (
    <>
      <line x1="88" y1="46" x2="120" y2="46" stroke={WIRE} strokeWidth="3" />
      <rect
        x="18"
        y="10"
        width="70"
        height="72"
        rx="8"
        fill="#f5c542"
        stroke="#a9841a"
      />
      <circle cx="53" cy="42" r="24" fill="#222b36" />
      <circle
        cx="53"
        cy={on ? 44 : 41}
        r={on ? 17 : 20}
        fill={on ? '#a52f29' : '#d6453d'}
        stroke="#0000004a"
      />
      <ellipse cx="46" cy={on ? 38 : 33} rx="7" ry="4" fill="#ffffff44" />
      <text
        x="53"
        y="78"
        textAnchor="middle"
        fontSize="8"
        fontWeight="700"
        fill="#5a4608"
      >
        E-STOP
      </text>
    </>
  )
}

function LimitSwitch({ on }: { on: boolean }) {
  return (
    <>
      <line x1="82" y1="46" x2="120" y2="46" stroke={WIRE} strokeWidth="3" />
      <rect
        x="20"
        y="26"
        width="62"
        height="40"
        rx="6"
        fill="#cfd8e3"
        stroke={EDGE}
      />
      <circle cx="66" cy="46" r="5" fill={on ? '#2fa65a' : '#8fa3ba'} />
      <g transform={`rotate(${on ? 38 : 0} 34 26)`}>
        <line
          x1="34"
          y1="26"
          x2="34"
          y2="4"
          stroke="#445468"
          strokeWidth="5"
          strokeLinecap="round"
        />
        <circle cx="34" cy="4" r="6" fill="#6b7f96" stroke="#445468" />
      </g>
    </>
  )
}

function Proximity({ on }: { on: boolean }) {
  return (
    <>
      <line x1="78" y1="46" x2="120" y2="46" stroke={WIRE} strokeWidth="3" />
      <rect
        x="20"
        y="32"
        width="58"
        height="28"
        rx="4"
        fill="#b6c3d3"
        stroke={EDGE}
      />
      {[30, 38, 46, 54, 62].map(x => (
        <line key={x} x1={x} y1="32" x2={x} y2="60" stroke="#8fa3ba" />
      ))}
      <rect x="10" y="28" width="12" height="36" rx="3" fill="#6b7f96" />
      <circle cx="68" cy="46" r="5" fill={on ? '#ffc400' : '#7d8794'} />
      {on && (
        <>
          <path
            d="M6 36 q-5 10 0 20"
            fill="none"
            stroke="#ffc400"
            strokeWidth="2"
          />
          <path
            d="M1 32 q-6 14 0 28"
            fill="none"
            stroke="#ffc400"
            strokeWidth="2"
            opacity=".6"
          />
        </>
      )}
    </>
  )
}

const LAMP = {
  green: { dim: '#2f6b45', lit: '#3ddc84' },
  red: { dim: '#7a2f2b', lit: '#ff4d42' },
  yellow: { dim: '#8a7424', lit: '#ffd23d' }
}

function Lamp({ on, color }: { on: boolean; color: keyof typeof LAMP }) {
  const c = LAMP[color]
  return (
    <>
      <line x1="0" y1="46" x2="42" y2="46" stroke={WIRE} strokeWidth="3" />
      <rect x="36" y="58" width="48" height="18" rx="4" fill="#8fa3ba" />
      {on && (
        <>
          <circle cx="60" cy="42" r="40" fill={c.lit} opacity=".12" />
          <circle cx="60" cy="42" r="32" fill={c.lit} opacity=".18" />
        </>
      )}
      <circle
        cx="60"
        cy="42"
        r="21"
        fill={on ? c.lit : c.dim}
        stroke="#0000004a"
        strokeWidth="2"
      />
      <ellipse cx="53" cy="34" rx="7" ry="4" fill="#ffffff55" />
    </>
  )
}

function Buzzer({ on }: { on: boolean }) {
  return (
    <>
      <line x1="0" y1="46" x2="38" y2="46" stroke={WIRE} strokeWidth="3" />
      <circle cx="62" cy="46" r="24" fill="#2b3544" stroke="#0f141b" />
      <circle cx="62" cy="46" r="6" fill="#0f141b" />
      <circle
        cx="62"
        cy="46"
        r="15"
        fill="none"
        stroke={on ? '#f5c542' : '#46566b'}
        strokeWidth="1.5"
      />
      {on &&
        [0, 1, 2].map(i => (
          <path
            key={i}
            className="hw-wave"
            style={{ animationDelay: `${i * 0.15}s` }}
            d={`M${92 + i * 8} ${36 - i * 3} q${6 + i * 2} ${10 + i * 3} 0 ${
              20 + i * 6
            }`}
            fill="none"
            stroke="#f5c542"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        ))}
    </>
  )
}

function Motor({ on }: { on: boolean }) {
  return (
    <>
      <line x1="0" y1="46" x2="30" y2="46" stroke={WIRE} strokeWidth="3" />
      <rect
        x="30"
        y="24"
        width="46"
        height="44"
        rx="6"
        fill="#9fb0c4"
        stroke={EDGE}
      />
      {[40, 48, 56, 64].map(x => (
        <line key={x} x1={x} y1="24" x2={x} y2="68" stroke="#8296ad" />
      ))}
      <rect x="76" y="34" width="8" height="24" fill="#6b7f96" />
      <line x1="84" y1="46" x2="100" y2="46" stroke="#445468" strokeWidth="4" />
      <g
        className={on ? 'hw-spin' : undefined}
        style={{ transformOrigin: '100px 46px' }}
      >
        {[0, 120, 240].map(a => (
          <ellipse
            key={a}
            cx="100"
            cy="32"
            rx="5"
            ry="13"
            fill={on ? '#3a86d6' : '#7c90a8'}
            transform={`rotate(${a} 100 46)`}
          />
        ))}
        <circle cx="100" cy="46" r="4" fill="#2b3544" />
      </g>
    </>
  )
}

function Valve({ on }: { on: boolean }) {
  return (
    <>
      <line x1="0" y1="46" x2="26" y2="46" stroke={WIRE} strokeWidth="3" />
      <rect
        x="26"
        y="40"
        width="76"
        height="16"
        fill={on ? '#7cc4ff' : '#cfd8e3'}
        stroke={EDGE}
      />
      <rect
        x="46"
        y="30"
        width="36"
        height="36"
        rx="4"
        fill="#6b7f96"
        stroke="#445468"
      />
      <rect
        x="52"
        y="6"
        width="24"
        height="24"
        rx="3"
        fill={on ? '#f5c542' : '#a7b4c4'}
        stroke={EDGE}
      />
      <line x1="56" y1="14" x2="72" y2="14" stroke="#0000003a" />
      <line x1="56" y1="20" x2="72" y2="20" stroke="#0000003a" />
      {on && (
        <path
          d="M30 48 h12 M88 48 h10"
          stroke="#ffffff"
          strokeWidth="2"
          strokeDasharray="4 3"
        />
      )}
    </>
  )
}

function body(type: string, on: boolean): ReactNode {
  switch (type) {
    case 'push_no':
      return <PushButton on={on} red={false} />
    case 'push_nc':
      return <PushButton on={on} red />
    case 'toggle':
      return <Toggle on={on} />
    case 'estop':
      return <EStop on={on} />
    case 'limit':
      return <LimitSwitch on={on} />
    case 'prox':
      return <Proximity on={on} />
    case 'led_green':
      return <Lamp on={on} color="green" />
    case 'led_red':
      return <Lamp on={on} color="red" />
    case 'led_yellow':
      return <Lamp on={on} color="yellow" />
    case 'buzzer':
      return <Buzzer on={on} />
    case 'motor':
      return <Motor on={on} />
    case 'valve':
      return <Valve on={on} />
    default:
      return (
        <rect x="20" y="16" width="80" height="60" fill="#cfd8e3" rx="6" />
      )
  }
}

export function HwGraphic({
  type,
  on,
  scale = 1
}: {
  type: string
  on: boolean
  scale?: number
}) {
  return (
    <svg
      className="hw-graphic"
      viewBox="0 0 120 92"
      width={120 * scale}
      height={92 * scale}
      aria-hidden="true"
    >
      {body(type, on)}
    </svg>
  )
}
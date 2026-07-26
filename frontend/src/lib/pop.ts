// Shared pop-art design tokens — usable in both Server and Client Components.

export const INK = '#0a0a0c'
export const CREAM = '#f4ead6'

export const POP = {
  red: '#ff2e4d',
  redDeep: '#e01e37',
  blue: '#1a5fd4',
  yellow: '#ffd400',
  teal: '#0fb890',
  orange: '#ff6a00',
  magenta: '#ff2d95',
  cyan: '#00c8ff',
}

// Hard (blur-less) offset shadow — the comic-book look.
export const hard = (c: string = INK, x = 6, y = 6) => ({ boxShadow: `${x}px ${y}px 0 ${c}` })

// Per-page accent theming (matches the homepage section colors).
export interface PageTheme {
  bg: string
  text: string
  sub: string
  accent: string
  accent2: string
  tone: 'light' | 'dark'
}

export const PAGE_THEME = {
  fights: { bg: CREAM, text: INK, sub: '#57534e', accent: POP.yellow, accent2: POP.redDeep, tone: 'light' },
  predict: { bg: CREAM, text: INK, sub: '#57534e', accent: POP.blue, accent2: POP.red, tone: 'light' },
  fighters: { bg: CREAM, text: INK, sub: '#57534e', accent: POP.teal, accent2: POP.redDeep, tone: 'light' },
  fighter: { bg: CREAM, text: INK, sub: '#57534e', accent: POP.red, accent2: POP.blue, tone: 'light' },
  compare: { bg: CREAM, text: INK, sub: '#57534e', accent: POP.magenta, accent2: POP.blue, tone: 'light' },
  model: { bg: INK, text: '#fafafa', sub: '#a1a1aa', accent: POP.orange, accent2: POP.yellow, tone: 'dark' },
} satisfies Record<string, PageTheme>

export const TIER_COLOR: Record<string, string> = {
  High: POP.red,
  Medium: POP.orange,
  Low: '#71717a',
}

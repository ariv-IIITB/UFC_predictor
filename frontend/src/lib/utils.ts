import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function fmt(n: number | null | undefined, decimals = 1): string {
  if (n == null) return '—'
  return n.toFixed(decimals)
}

export function fmtPct(n: number | null | undefined): string {
  if (n == null) return '—'
  return `${(n * 100).toFixed(1)}%`
}

export function fmtOdds(n: number | null | undefined): string {
  if (n == null) return '—'
  return n.toFixed(2)
}

export function fmtProfit(n: number | null | undefined): string {
  if (n == null) return '—'
  const sign = n >= 0 ? '+' : ''
  return `${sign}${n.toFixed(2)}u`
}

export function fmtDate(d: string | null | undefined): string {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function slugify(name: string): string {
  return encodeURIComponent(name.trim())
}

export function deslugify(slug: string): string {
  return decodeURIComponent(slug)
}

export function getCountdown(target: string): { days: number; hours: number; minutes: number; seconds: number; past: boolean } {
  const now = Date.now()
  const then = new Date(target).getTime()
  const diff = then - now

  if (diff <= 0) return { days: 0, hours: 0, minutes: 0, seconds: 0, past: true }

  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((diff % (1000 * 60)) / 1000)

  return { days, hours, minutes, seconds, past: false }
}

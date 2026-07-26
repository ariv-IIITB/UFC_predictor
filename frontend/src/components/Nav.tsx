'use client'

import { useState, useEffect } from 'react'
import { Menu, X } from 'lucide-react'
import { cn } from '@/lib/utils'

// Single-page section anchors (href '/#id' so they also work from sub-pages).
const sections = [
  { id: 'top', label: 'Home', color: '#ff2e4d' },
  { id: 'predictions', label: 'Predictions', color: '#2e7dff' },
  { id: 'history', label: 'Fights', color: '#ffd400' },
  { id: 'fighters', label: 'Fighters', color: '#00e5a0' },
  { id: 'model', label: 'Model', color: '#ff6a00' },
]

// Standalone tool page.
const BUILD = { href: '/build', label: 'Build', color: '#ff2d95' }

export default function Nav() {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState('top')

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActive(entry.target.id)
        })
      },
      { rootMargin: '-45% 0px -50% 0px', threshold: 0 }
    )
    sections.forEach((s) => {
      const el = document.getElementById(s.id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [])

  const activeColor = sections.find((s) => s.id === active)?.color ?? '#ff2e4d'

  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-[#2a2a30]/60 bg-[#0a0a0c]/85 backdrop-blur-md">
      {/* Colored progress accent that follows the active section */}
      <div
        className="absolute top-0 left-0 h-[2px] transition-all duration-500"
        style={{
          background: activeColor,
          width: `${((sections.findIndex((s) => s.id === active) + 1) / sections.length) * 100}%`,
        }}
      />

      <div className="mx-auto max-w-7xl px-6 flex items-center justify-between h-14">
        <a
          href="/#top"
          className="text-sm font-bold tracking-widest uppercase text-[#fafafa] transition-colors duration-200"
          style={{ fontFamily: "'Space Grotesk', sans-serif" }}
        >
          UFC <span style={{ color: activeColor }}>EDGE</span>
        </a>

        <nav className="hidden md:flex items-center gap-8">
          {sections.map(({ id, label, color }) => (
            <a
              key={id}
              href={`/#${id}`}
              className={cn(
                'text-xs tracking-widest uppercase font-medium transition-colors duration-200',
                active === id ? '' : 'text-[#a1a1aa] hover:text-[#fafafa]'
              )}
              style={active === id ? { color } : undefined}
            >
              {label}
            </a>
          ))}
          <a
            href={BUILD.href}
            className="text-xs tracking-widest uppercase font-bold px-3 py-1 text-white transition-transform hover:scale-105"
style={{ background: BUILD.color }}
          >
            {BUILD.label}
          </a>
        </nav>

        <button
          className="md:hidden text-[#a1a1aa] hover:text-[#fafafa] transition-colors"
          onClick={() => setOpen(!open)}
          aria-label="Toggle menu"
        >
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {open && (
        <div className="md:hidden border-t border-[#2a2a30] bg-[#0a0a0c]">
          {sections.map(({ id, label, color }) => (
            <a
              key={id}
              href={`/#${id}`}
              onClick={() => setOpen(false)}
              className={cn(
                'block px-6 py-4 text-xs tracking-widest uppercase font-medium border-b border-[#2a2a30]/60 transition-colors duration-200',
                active === id ? '' : 'text-[#a1a1aa] hover:text-[#fafafa]'
              )}
              style={active === id ? { color } : undefined}
            >
              {label}
            </a>
          ))}
          <a
            href={BUILD.href}
            onClick={() => setOpen(false)}
            className="block px-6 py-4 text-xs tracking-widest uppercase font-bold border-b border-[#2a2a30]/60"
            style={{ color: BUILD.color }}
          >
            {BUILD.label}
          </a>
        </div>
      )}
    </header>
  )
}

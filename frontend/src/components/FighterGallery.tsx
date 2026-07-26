'use client'

import Image from 'next/image'
import Link from 'next/link'
import { useRef } from 'react'
import { motion, useInView, useScroll, useTransform } from 'framer-motion'

const TICKER = 'KNOCKOUT · SUBMISSION · DECISION · UNANIMOUS · SPLIT · TKO · RNC · ARMBAR · GUILLOTINE · '

const COLS: Array<Array<{ src: string; aspect: string; delay: number }>> = [
  [
    { src: '/fighters/f1.avif', aspect: 'aspect-[3/4]', delay: 0 },
    { src: '/fighters/f5.avif', aspect: 'aspect-[4/5]', delay: 0.18 },
  ],
  [
    { src: '/fighters/f3.avif', aspect: 'aspect-[3/4]', delay: 0.07 },
    { src: '/fighters/f6.avif', aspect: 'aspect-[5/4]', delay: 0.22 },
  ],
  [
    { src: '/fighters/f2.avif', aspect: 'aspect-[3/4]', delay: 0.04 },
    { src: '/fighters/f4.avif', aspect: 'aspect-[4/5]', delay: 0.13 },
  ],
]

function FighterCard({ src, aspect, delay }: { src: string; aspect: string; delay: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-80px 0px' })
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] })
  const yMotion = useTransform(scrollYProgress, [0, 1], ['-7%', '7%'])

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 48 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.9, delay, ease: [0.16, 1, 0.3, 1] }}
      className={`relative overflow-hidden ${aspect} group cursor-pointer w-full`}
    >
      {/* Image layer — scaled up so ±7% parallax never exposes background */}
      <motion.div
        style={{ y: yMotion }}
        className="absolute inset-0 scale-[1.16] origin-center"
      >
        <Image
          src={src}
          fill
          alt=""
          className="object-cover object-top grayscale-[30%] group-hover:grayscale-0 group-hover:scale-[1.04] transition-all duration-700 ease-out"
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
        />
      </motion.div>

      {/* Bottom gradient vignette */}
      <div className="absolute inset-0 bg-gradient-to-t from-[#09090b]/50 via-transparent to-transparent pointer-events-none" />
{/* Red reveal bar on hover */}
      <div className="absolute inset-x-0 bottom-0 h-[3px] bg-[#e63946] origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-500 z-10" />

      {/* Top-left corner accent */}
      <div className="absolute top-0 left-0 w-6 h-[2px] bg-[#e63946] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      <div className="absolute top-0 left-0 w-[2px] h-6 bg-[#e63946] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
    </motion.div>
  )
}

export default function FighterGallery() {
  const sectionRef = useRef<HTMLDivElement>(null)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const headingInView = useInView(headingRef, { once: true, margin: '-60px' })

  return (
    <section ref={sectionRef} className="border-t border-[#3f3f46] overflow-hidden">

      {/* Section header */}
      <div className="px-6 pt-20 pb-10 mx-auto max-w-7xl flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <motion.p
            initial={{ opacity: 0, x: -16 }}
            animate={headingInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className="text-xs tracking-[0.35em] uppercase text-[#a1a1aa] mb-3"
          >
            The fighters
          </motion.p>
          <motion.h2
            ref={headingRef}
            initial={{ opacity: 0, y: 32 }}
            animate={headingInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
            className="font-bold text-[#fafafa] leading-[0.88] tracking-tight"
            style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 'clamp(52px, 8vw, 100px)' }}
          >
            ROSTER
          </motion.h2>
        </div>
        <motion.div
          initial={{ opacity: 0 }}
          animate={headingInView ? { opacity: 1 } : {}}
          transition={{ duration: 0.6, delay: 0.25 }}
        >
          <Link
            href="/fighters"
            className="text-xs tracking-widest uppercase text-[#e63946] hover:text-[#ff6b6b] transition-colors duration-200"
          >
            All fighters →
          </Link>
        </motion.div>
      </div>

      {/* Ticker strip */}
      <div className="relative w-full overflow-hidden border-y border-[#3f3f46] py-2 mb-2 bg-[#09090b]">
        <div className="flex whitespace-nowrap" style={{ animation: 'ticker 28s linear infinite' }}>
          <span className="text-[10px] tracking-[0.25em] uppercase text-[#3f3f46] pr-8 shrink-0">{TICKER.repeat(4)}</span>
          <span className="text-[10px] tracking-[0.25em] uppercase text-[#3f3f46] pr-8 shrink-0" aria-hidden>{TICKER.repeat(4)}</span>
        </div>
        <style>{`@keyframes ticker { from { transform: translateX(0) } to { transform: translateX(-50%) } }`}</style>
      </div>

      {/* 3-column masonry grid */}
      <div className="px-[1px] pb-[1px]">
        <div className="grid grid-cols-3 gap-[1px] bg-[#3f3f46]">
          {COLS.map((col, ci) => (
            <div key={ci} className="flex flex-col gap-[1px] bg-[#3f3f46]">
              {col.map((img) => (
                <div key={img.src} className="bg-[#09090b]">
                  <FighterCard src={img.src} aspect={img.aspect} delay={img.delay} />
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Bottom label */}
      <div className="px-6 py-8 mx-auto max-w-7xl">
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-[10px] tracking-[0.4em] uppercase text-[#3f3f46]"
        >
          UFC · MMA · All weight classes · 2021 – present
        </motion.p>
      </div>

    </section>
  )
}

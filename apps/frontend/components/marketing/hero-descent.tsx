'use client'

import { useEffect, useRef } from 'react'
import { useReducedMotion, useScroll, useTransform, motion } from 'motion/react'
import { HeroStatic } from '@/components/marketing/hero-static'

export function HeroDescent() {
  const reduce = useReducedMotion()
  if (reduce) return <HeroStatic />
  return <HeroTrack />
}

function HeroTrack() {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] })
  const y0 = useTransform(scrollYProgress, [0, 1], [0, 40])
  const y1 = useTransform(scrollYProgress, [0, 1], [0, 120])
  const y2 = useTransform(scrollYProgress, [0, 1], [0, 200])

  return (
    <div ref={ref} className="relative h-[320vh]">
      <div className="sticky top-0 min-h-dvh overflow-hidden">
        <motion.div style={{ y: y0 }} className="absolute inset-0 bg-abyss-950" />
        <motion.div style={{ y: y1 }} className="absolute inset-x-0 top-1/3 h-40 bg-abyss-800" />
        <motion.div style={{ y: y2 }} className="absolute inset-x-0 bottom-0 h-24 bg-abyss-600" />
        <DesktopPlates />
        <div className="relative z-10">
          <HeroStatic />
        </div>
      </div>
    </div>
  )
}

function DesktopPlates() {
  const shown = useRef(false)
  const node = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (window.matchMedia('(min-width: 1024px)').matches) {
      shown.current = true
      if (node.current) node.current.hidden = false
    }
  }, [])
  return (
    <div ref={node} hidden className="pointer-events-none absolute inset-0 hidden lg:block">
      {/* Extra plates exist only at lg and are not in the phone DOM fetch path. */}
      <div className="absolute inset-y-0 left-0 w-1/5 bg-abyss-900/40" />
      <div className="absolute inset-y-0 right-0 w-1/5 bg-abyss-800/40" />
    </div>
  )
}

'use client'

import { useRef } from 'react'
import {
  motion,
  useMotionTemplate,
  useReducedMotion,
  useScroll,
  useTransform,
} from 'motion/react'
import { HeroStatic } from '@/components/marketing/hero-static'
import { LampGlow, MarineSnow, Stratum } from '@/components/marketing/sea-strata'

export function HeroDescent() {
  const reduce = useReducedMotion()
  // Reduced motion still gets the composition, just held still. Dropping to
  // bare copy would leave the hero with no visual at all.
  if (reduce) return <HeroStill />
  return <HeroTrack />
}

function HeroStill() {
  return (
    <div className="relative min-h-dvh overflow-hidden bg-abyss-950">
      <div className="absolute inset-x-0 top-0 h-[46vh]">
        <LampGlow className="absolute inset-0" />
      </div>
      {PLANES.map((plane) => (
        <div key={plane.depth} className={`absolute inset-x-0 ${plane.position}`}>
          <Stratum depth={plane.depth} className="h-full w-full" />
        </div>
      ))}
      <div className="relative z-10">
        <HeroStatic />
      </div>
    </div>
  )
}

// Nearer water travels further, which is what reads as depth.
const PLANES = [
  { depth: 0, travel: 10, position: 'top-[26%] h-[30vh]' },
  { depth: 1, travel: 24, position: 'top-[38%] h-[34vh]' },
  { depth: 2, travel: 42, position: 'top-[52%] h-[38vh]' },
  { depth: 3, travel: 62, position: 'top-[68%] h-[42vh]' },
  { depth: 4, travel: 84, position: 'top-[84%] h-[46vh]' },
] as const

function HeroTrack() {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start start', 'end start'],
  })

  // Water removes warm light first, so the descent desaturates and the lamp is
  // the last colour to go. That loss is the argument the page is making.
  const saturate = useTransform(scrollYProgress, [0.15, 0.7], [1, 0.3])
  const contrast = useTransform(scrollYProgress, [0.15, 0.7], [1, 1.08])
  const grade = useMotionTemplate`saturate(${saturate}) contrast(${contrast})`

  const tint = useTransform(scrollYProgress, [0.25, 1], [0, 0.92])
  const lampFade = useTransform(scrollYProgress, [0, 0.55], [1, 0])
  const lampRise = useTransform(scrollYProgress, [0, 1], ['0vh', '-24vh'])

  return (
    <div ref={ref} className="relative h-[240vh]">
      <div className="sticky top-0 min-h-dvh overflow-hidden bg-abyss-950">
        {/* The grade sits inside the sticky element: a filter on an ancestor of
            a sticky node drops it out of its sticky context on iOS Safari. */}
        <motion.div style={{ filter: grade }} className="absolute inset-0">
          <motion.div
            style={{ y: lampRise, opacity: lampFade }}
            className="absolute inset-x-0 top-0 h-[46vh] will-change-transform"
          >
            <LampGlow className="absolute inset-0" />
          </motion.div>

          {PLANES.map((plane) => (
            <HeroPlane key={plane.depth} plane={plane} progress={scrollYProgress} />
          ))}

          <MarineSnow className="pointer-events-none absolute inset-0 hidden lg:block" />
        </motion.div>

        {/* Depth tint: the abyss closing over the composition. */}
        <motion.div style={{ opacity: tint }} className="absolute inset-0 bg-abyss-950" />

        <div className="relative z-10">
          <HeroStatic />
        </div>
      </div>
    </div>
  )
}

function HeroPlane({
  plane,
  progress,
}: {
  plane: (typeof PLANES)[number]
  progress: ReturnType<typeof useScroll>['scrollYProgress']
}) {
  const y = useTransform(progress, [0, 1], ['0vh', `${plane.travel}vh`])
  return (
    <motion.div
      style={{ y }}
      className={`absolute inset-x-0 ${plane.position} will-change-transform`}
    >
      <Stratum depth={plane.depth} className="h-full w-full" />
    </motion.div>
  )
}

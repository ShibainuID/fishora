'use client'

import { useRef } from 'react'
import Image from 'next/image'
import {
  motion,
  useMotionTemplate,
  useReducedMotion,
  useScroll,
  useTransform,
} from 'motion/react'
import { HeroStatic } from '@/components/marketing/hero-static'
import { LampGlow } from '@/components/marketing/sea-strata'

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
        // No will-change-transform here: nothing moves, and the hint would cost
        // a compositor layer per plane for no reason.
        <div key={plane.depth} className={`absolute inset-x-0 ${plane.position}`}>
          <PlaneImage plane={plane} />
        </div>
      ))}
      <div className="relative z-10">
        <HeroStatic />
      </div>
    </div>
  )
}

/**
 * Nearer water travels further, which is what reads as depth.
 *
 * `crop` moves each plane to a different part of the photograph so five bands
 * of the same water do not read as one image repeated, and `shade` sinks each
 * plane further into the abyss, because light is what depth takes away first.
 */
const PLANES = [
  { depth: 0, travel: 6, position: 'top-[26%] h-[46vh]', crop: 12, shade: 0.1 },
  { depth: 1, travel: 14, position: 'top-[38%] h-[50vh]', crop: 34, shade: 0.28 },
  { depth: 2, travel: 24, position: 'top-[52%] h-[54vh]', crop: 55, shade: 0.45 },
  { depth: 3, travel: 34, position: 'top-[68%] h-[58vh]', crop: 74, shade: 0.62 },
  { depth: 4, travel: 44, position: 'top-[84%] h-[62vh]', crop: 90, shade: 0.78 },
] as const

/**
 * How much of a band's height is spent fading in at the top.
 *
 * The bands are sized around this: a plane has to stay long enough to cover the
 * whole fade of the plane below it, at both ends of the scroll, or the descent
 * opens a visible seam between them at some point in the middle.
 */
const FADE = 0.35

/**
 * One band of water.
 *
 * The top edge is masked to transparent rather than cut square: five hard
 * horizontal edges stacked up read as ribbons of photograph, not as a sea. The
 * mask blends each band into whatever sits behind it, which is the plane above,
 * so the fade works between planes and not just against the page ground.
 *
 * The planes also travel a short distance relative to each other. A wide spread
 * gives a stronger parallax but pulls the bands apart far enough to show the
 * ground between them, and a gap in open water reads as a rendering fault.
 */
function PlaneImage({ plane }: { plane: (typeof PLANES)[number] }) {
  const fade = `linear-gradient(to bottom, transparent 0%, #000 ${FADE * 100}%, #000 100%)`
  return (
    <div
      className="relative size-full overflow-hidden"
      style={{ maskImage: fade, WebkitMaskImage: fade }}
    >
      <Image
        src="/sea.jpg"
        alt=""
        fill
        // The hero is the LCP element, so the first band is not lazy.
        priority={plane.depth === 0}
        sizes="100vw"
        className="object-cover"
        style={{ objectPosition: `50% ${plane.crop}%` }}
      />
      <div
        className="absolute inset-0 bg-abyss-950"
        style={{ opacity: plane.shade }}
      />
    </div>
  )
}

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
      <PlaneImage plane={plane} />
    </motion.div>
  )
}

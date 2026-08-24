'use client'

import { useEffect, useRef, type ReactNode } from 'react'

export function FlowPan({ children }: { children: ReactNode }) {
  const wrap = useRef<HTMLElement>(null)
  const track = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const narrow = window.matchMedia('(max-width: 1023px)').matches
    if (reduce || narrow || !wrap.current || !track.current) return
    let revert: (() => void) | undefined
    import('gsap').then(async ({ default: gsap }) => {
      const { ScrollTrigger } = await import('gsap/ScrollTrigger')
      gsap.registerPlugin(ScrollTrigger)
      const ctx = gsap.context(() => {
        const distance = track.current!.scrollWidth - window.innerWidth
        gsap.to(track.current, {
          x: -distance,
          ease: 'none',
          scrollTrigger: {
            trigger: wrap.current,
            start: 'top top',
            end: () => `+=${distance}`,
            pin: true,
            scrub: 1,
            invalidateOnRefresh: true,
          },
        })
      }, wrap)
      revert = () => ctx.revert()
    })
    return () => revert?.()
  }, [])

  return (
    <section ref={wrap} className="lg:overflow-hidden">
      <div ref={track}>{children}</div>
    </section>
  )
}

'use client'

import Link from 'next/link'
import { useCallback, useMemo, useState, useSyncExternalStore } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { Fish, Funnel, Sliders } from '@phosphor-icons/react/dist/ssr'
import { Button } from '@/components/common/button'
import { EmptyState } from '@/components/common/empty-state'
import { MatchedEmpty } from '@/components/buyer/matched-empty'
import { LotCard } from '@/components/lot/lot-card'
import { FilterRail } from '@/components/marketplace/filter-rail'
import { FilterSheet } from '@/components/marketplace/filter-sheet'
import { listLots } from '@/lib/api/commerce'
import {
  activeFilterCount,
  lotApiQuery,
  parseFilters,
  serializeFilters,
  type MarketplaceFilters,
} from '@/lib/marketplace-filters'
import { SPECIES } from '@/lib/species'
import type { components } from '@/lib/api/schema'

type Lot = components['schemas']['LotResponse']

const POLL_MS = 15_000

// Mirrors the server query in the marketplace page. Polling with anything else
// would answer a filtered grid with the whole open market.

interface PollSnapshot {
  lots: Lot[]
  fresh: number
}

function ViewTab({
  href,
  current,
  children,
}: {
  href: string
  current: boolean
  children: React.ReactNode
}) {
  return (
    <Link
      href={href}
      aria-current={current ? 'page' : undefined}
      className={[
        // A rule under the current label rather than a filled pill, so the page
        // background carries through the way the shell's own tabs do.
        'text-body-sm flex min-h-11 min-w-0 items-center justify-center truncate border-b-2 px-3',
        current ? 'border-ink text-ink' : 'border-transparent text-ink-muted hover:text-ink',
      ].join(' ')}
    >
      {children}
    </Link>
  )
}

// An external store, not state in an effect: the interval, the tab visibility
// and the fetch all live outside React, and useSyncExternalStore is how this
// codebase reads such values.
function createLotPoll(load: (query: string) => Promise<Lot[]>) {
  const listeners = new Set<() => void>()
  let snapshot: PollSnapshot | null = null
  let seen = new Set<string>()
  let fresh = 0
  let query = ''
  let timer: ReturnType<typeof setInterval> | null = null

  const emit = () => {
    for (const listener of listeners) listener()
  }

  const poll = () => {
    const asked = query
    load(asked)
      .then((lots) => {
        // A late reply from a filter the buyer already left must not land.
        if (asked !== query) return
        const arrived = lots.filter((lot) => !seen.has(lot.id))
        for (const lot of arrived) seen.add(lot.id)
        fresh += arrived.length
        const same =
          snapshot !== null &&
          snapshot.fresh === fresh &&
          snapshot.lots.length === lots.length &&
          snapshot.lots.every((lot, index) => lot.id === lots[index].id)
        if (same) return
        snapshot = { lots, fresh }
        emit()
      })
      .catch(() => {
        // A dropped poll keeps the last good grid. Blanking it would be worse
        // than being fifteen seconds stale.
      })
  }

  const stopTimer = () => {
    if (timer === null) return
    clearInterval(timer)
    timer = null
  }

  const resume = (immediate: boolean) => {
    if (document.visibilityState === 'hidden') {
      stopTimer()
      return
    }
    if (timer !== null) return
    timer = setInterval(poll, POLL_MS)
    // Coming back to a parked tab, the grid is as stale as the time away.
    if (immediate) poll()
  }

  const onVisible = () => resume(true)

  return {
    read: () => snapshot,
    dismiss: () => {
      if (fresh === 0) return
      fresh = 0
      if (snapshot !== null) snapshot = { lots: snapshot.lots, fresh: 0 }
      emit()
    },
    start(nextQuery: string, seedIds: string[], listener: () => void) {
      if (nextQuery !== query) {
        query = nextQuery
        snapshot = null
        fresh = 0
      }
      seen = new Set([...seedIds, ...(snapshot?.lots ?? []).map((lot) => lot.id)])
      listeners.add(listener)
      resume(false)
      document.addEventListener('visibilitychange', onVisible)
      window.addEventListener('focus', onVisible)
      return () => {
        listeners.delete(listener)
        document.removeEventListener('visibilitychange', onVisible)
        window.removeEventListener('focus', onVisible)
        if (listeners.size === 0) stopTimer()
      }
    },
  }
}

const noSnapshot = () => null

export function MarketplaceView({
  lots,
  inventoryEmpty,
  matched = false,
  matchScores = {},
  profileMissing = false,
}: {
  lots: Lot[]
  inventoryEmpty: boolean
  /** True when the caller resolved recommendations rather than the open grid. */
  matched?: boolean
  /** Real per-lot scores from the matching engine, keyed by lot id. */
  matchScores?: Record<string, number>
  profileMissing?: boolean
}) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const search = searchParams.toString()
  const filters = useMemo(() => parseFilters(search), [search])
  const [sheetOpen, setSheetOpen] = useState(false)
  const count = activeFilterCount(filters)
  const showMatched = matched || filters.matched

  const poll = useMemo(() => createLotPoll(listLots), [])
  const pollQuery = useMemo(() => lotApiQuery(filters), [filters])
  // A joined string, so a re-render with an equal list does not resubscribe.
  const seed = useMemo(() => lots.map((lot) => lot.id).join(','), [lots])
  const subscribe = useCallback(
    (onChange: () => void) =>
      // The matched grid is ordered by the recommendation engine, so open
      // marketplace lots must never overwrite it.
      showMatched ? () => {} : poll.start(pollQuery, seed ? seed.split(',') : [], onChange),
    [poll, showMatched, pollQuery, seed]
  )
  const live = useSyncExternalStore(subscribe, poll.read, noSnapshot)
  const current = live?.lots ?? lots
  const fresh = live?.fresh ?? 0

  // Switching views keeps the filters the buyer already set.
  const viewHref = (wantsMatched: boolean) => {
    const query = serializeFilters({ ...filters, matched: wantsMatched })
    return query ? `${pathname}?${query}` : pathname
  }

  const apply = (next: MarketplaceFilters) => {
    const query = serializeFilters(next)
    router.replace(query ? `${pathname}?${query}` : pathname)
  }

  const visible = useMemo(() => {
    return current.filter((lot) => {
      const label = lot.species_id.replace('species_', '')
      if (filters.species.length && !filters.species.includes(label as never)) return false
      if (filters.minPrice && Number(lot.starting_price_per_kg) < Number(filters.minPrice)) return false
      if (filters.maxPrice && Number(lot.starting_price_per_kg) > Number(filters.maxPrice)) return false
      if (filters.minQuantity && Number(lot.quantity_kg) < Number(filters.minQuantity)) return false
      if (filters.maxQuantity && Number(lot.quantity_kg) > Number(filters.maxQuantity)) return false
      return true
    })
  }, [current, filters])

  return (
    <div className="pb-24 lg:pb-8">
      {/* The heading spans both columns. Inside the grid column it would have
          pushed the cards down while the filter rail beside them started at
          the top of the page. */}
      <header>
        <h1 className="text-h1 text-ink">
          {showMatched ? 'Matched for me' : 'All lots'}
        </h1>
        <p className="text-body-sm mt-1 max-w-[52ch] text-ink-muted">
          {showMatched
            ? 'Diurutkan menurut kecocokan dengan preferensi Anda.'
            : 'Semua lot lelang yang masih aktif.'}
        </p>
      </header>

      <div className="mt-4 flex gap-8 lg:mt-6">
        <FilterRail filters={filters} onChange={apply} />
        <div className="min-w-0 flex-1">
          {/* No fill of its own: the toolbar sits on the page background as part
              of the heading block, carrying only the baseline the current tab is
              drawn against. It wraps rather than scrolls, so a narrow screen
              never cuts a control in half. */}
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-line pb-2">
            {/* Both views are named and the current one is marked. The single
                link before this showed the view you were already on while
                navigating to the other one. */}
            <nav aria-label="Tampilan lot" className="-mb-2 flex min-w-0 gap-1">
              <ViewTab href={viewHref(false)} current={!showMatched}>
                All lots
              </ViewTab>
              <ViewTab href={viewHref(true)} current={showMatched}>
                Matched for me
              </ViewTab>
            </nav>
            {fresh > 0 && (
              <button
                type="button"
                onClick={poll.dismiss}
                className="text-body-sm min-h-11 shrink-0 rounded-full border border-line px-3 text-ink"
              >
                {fresh} lot baru
              </button>
            )}
            <div className="ml-auto flex shrink-0 items-center gap-2 lg:hidden">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                icon={<Funnel size={16} />}
                onClick={() => setSheetOpen(true)}
              >
                Filters{count ? ` ${count}` : ''}
              </Button>
              <button type="button" aria-label="Urutkan" className="grid size-11 shrink-0 place-items-center">
                <Sliders size={20} />
              </button>
            </div>
          </div>

          {count > 0 && (
            <div
              tabIndex={0}
              role="group"
              aria-label="Filter aktif"
              className="flex gap-2 overflow-x-auto py-3 whitespace-nowrap"
            >
              {filters.species.map((label) => (
                <button
                  key={label}
                  type="button"
                  className="text-body-sm min-h-11 shrink-0 rounded-full border border-line px-3"
                  onClick={() => apply({ ...filters, species: filters.species.filter((item) => item !== label) })}
                >
                  {SPECIES[label].commonName}
                </button>
              ))}
            </div>
          )}

          {showMatched && profileMissing ? (
            <MatchedEmpty hasProfile={false} />
          ) : inventoryEmpty && current.length === 0 ? (
            <EmptyState icon={Fish} message="Belum ada lot aktif." action={<Button type="button">Muat ulang</Button>} />
          ) : visible.length === 0 ? (
            <EmptyState
              icon={Funnel}
              message="Tidak ada lot yang cocok dengan filter ini."
              action={
                <Button type="button" variant="secondary" onClick={() => apply({ ...filters, species: [], minPrice: '', maxPrice: '', minQuantity: '', maxQuantity: '' })}>
                  Hapus filter
                </Button>
              }
            />
          ) : (
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {visible.map((lot, index) => (
                <Link key={lot.id} href={`/marketplace/${lot.id}`}>
                  <LotCard
                    lot={lot}
                    matchPercent={showMatched ? matchScores[lot.id] : undefined}
                    priority={index === 0}
                  />
                </Link>
              ))}
            </div>
          )}
        </div>
        </div>
      <FilterSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        filters={filters}
        onChange={apply}
        resultCount={visible.length}
      />
    </div>
  )
}

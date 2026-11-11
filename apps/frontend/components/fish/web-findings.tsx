import { Globe } from '@phosphor-icons/react/dist/ssr'
import { Skeleton } from '@/components/common/skeleton'
import type { WebResearch } from '@/lib/api/fish'
import { normaliseDashes } from '@/lib/format'

const FIELD_NAMES: Record<string, string> = {
  physical_characteristics: 'Physical traits',
  taste: 'Taste',
  texture: 'Texture',
  processing_methods: 'Suitable for',
  commercial_uses: 'Commercial uses',
  potential_buyer_segments: 'Potential buyers',
  similar_or_substitute_species: 'Substitutes',
}

function fieldName(field: string): string {
  return FIELD_NAMES[field] ?? field
}

function host(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

/**
 * Leads an agent found on the web for the fields the verified sources leave
 * empty. Operator-only: they were checked against the page excerpt the search
 * returned, but nobody reviewed them, so they never reach the buyer card.
 */
export function WebFindings({ research }: { research: WebResearch }) {
  const fields = research.fields.map(fieldName).join(', ')

  return (
    <section aria-labelledby="web-findings" className="rounded-2xl border border-line px-5 py-5">
      <h3 id="web-findings" className="text-label mb-1 inline-flex items-center gap-1.5 text-ink">
        <Globe className="size-4" aria-hidden />
        Web leads, not verified
      </h3>
      <p className="text-body-sm mb-4 max-w-[65ch] text-ink-muted">
        Searched for the fields the verified sources leave empty ({fields}). Each lead was checked against the
        page it cites, but nobody has reviewed it, so buyers do not see it.
      </p>

      {research.status === 'running' && (
        <div className="flex flex-col gap-2" aria-live="polite">
          <p className="text-body-sm text-ink-muted">Searching the web…</p>
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-2/3" />
        </div>
      )}

      {research.status === 'failed' && (
        <p className="text-body-sm text-state-warn">The web search is unavailable right now.</p>
      )}

      {research.status === 'done' && research.findings.length === 0 && (
        <p className="text-body-sm text-ink-muted">No web source passed the check.</p>
      )}

      {research.status === 'done' && research.findings.length > 0 && (
        <ul className="flex flex-col gap-3">
          {research.findings.map((finding) => (
            <li key={`${finding.field}-${finding.text}`} className="flex flex-col gap-0.5">
              <span className="text-label text-ink">{fieldName(finding.field)}</span>
              <span className="text-body text-ink">{normaliseDashes(finding.text)}</span>
              <a
                href={finding.url}
                target="_blank"
                rel="noreferrer"
                className="text-body-sm text-ink-muted underline underline-offset-2"
              >
                {normaliseDashes(finding.title)} ({host(finding.url)})
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

import { ShieldCheck } from '@phosphor-icons/react/dist/ssr'
import { TaxonomyQualifier } from '@/components/fish/taxonomy-qualifier'
import { SourceList } from '@/components/fish/source-list'
import type { KnowledgeCard } from '@/lib/api/fish'
import { normaliseDashes } from '@/lib/format'

// The verified surface. MarketSignals stays a sibling, never a child.
export interface KnowledgeCardViewProps {
  card: KnowledgeCard
  /** Normalized CV label, so MIXED_TAXONOMY on tuna can name the genus. */
  label: string
}

export function KnowledgeCardView({ card, label }: KnowledgeCardViewProps) {
  return (
    <article className="rounded-2xl border-l-2 border-l-verified bg-surface px-5 py-5">
      <header className="text-body-sm mb-4 inline-flex items-center gap-1.5 text-verified">
        <ShieldCheck className="size-4" weight="fill" aria-hidden />
        Pengetahuan terverifikasi
      </header>

      <div className="flex flex-col gap-5">
        {card.scientific_name && (
          <p className="text-body max-w-[65ch] text-ink-muted italic">
            {display(card.scientific_name)}
          </p>
        )}

        <TaxonomyQualifier status={card.taxonomy_status} label={label} />

        {card.physical_characteristics && (
          <Field heading="Ciri fisik" body={card.physical_characteristics} />
        )}
        {card.taste && <Field heading="Rasa" body={card.taste} />}
        {card.texture && <Field heading="Tekstur" body={card.texture} />}
        <ChipList heading="Cara memasak" items={card.processing_methods} />
        <ChipList heading="Penggunaan komersial" items={card.commercial_uses} />
        <ChipList heading="Ikan serupa" items={card.similar_or_substitute_species} />
        <ChipList heading="Segmen pembeli" items={card.potential_buyer_segments} />

        {card.limitations.length > 0 && (
          <section aria-labelledby="knowledge-limitations">
            <h3 id="knowledge-limitations" className="text-label mb-2 text-ink">
              Keterbatasan
            </h3>
            <ul className="text-body-sm flex flex-col gap-2 text-ink-muted">
              {card.limitations.map((item) => (
                <li key={item}>{display(item)}</li>
              ))}
            </ul>
          </section>
        )}

        {card.sources.length > 0 && (
          <section aria-labelledby="knowledge-sources">
            <h3 id="knowledge-sources" className="text-label mb-2 text-ink">
              Sumber
            </h3>
            <SourceList sources={card.sources} />
          </section>
        )}
      </div>
    </article>
  )
}

function Field({ heading, body }: { heading: string; body: string }) {
  return (
    <section>
      <h3 className="text-label mb-1 text-ink">{heading}</h3>
      <p className="text-body max-w-[65ch] text-ink-muted">{display(body)}</p>
    </section>
  )
}

function ChipList({ heading, items }: { heading: string; items: string[] }) {
  if (items.length === 0) return null
  return (
    <section>
      <h3 className="text-label mb-2 text-ink">{heading}</h3>
      <ul className="text-body-sm flex flex-col gap-1 text-ink-muted">
        {items.map((item) => (
          <li key={item}>{display(item)}</li>
        ))}
      </ul>
    </section>
  )
}

/** Strips long dashes and leaked markdown headings from generated text. */
function display(text: string): string {
  return normaliseDashes(text.replace(/^#{1,6}\s+/gm, ''))
}

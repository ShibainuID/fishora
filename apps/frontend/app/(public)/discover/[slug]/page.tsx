import { notFound } from 'next/navigation'
import Image from 'next/image'
import { KnowledgeCardView } from '@/components/fish/knowledge-card'
import { getDiscover } from '@/lib/api/commerce'
import { SPECIES, isSpeciesLabel } from '@/lib/species'

export const dynamic = 'force-dynamic'

export default async function DiscoverPage({
  params,
}: {
  params: Promise<{ slug: string }>
}) {
  const { slug } = await params
  let data
  try {
    data = await getDiscover(slug)
  } catch {
    notFound()
  }
  const label = data.species_id.replace('species_', '')
  const names = isSpeciesLabel(label) ? SPECIES[label] : { commonName: data.card.common_name, scientificName: data.card.scientific_name }
  const month = 'Agustus 2026' // mock: landing month only, no coordinates

  return (
    <main className="mx-auto max-w-[420px] px-4 py-8">
        <Image
          src="/globe.svg"
          alt={names.commonName}
          width={420}
          height={280}
          priority
          className="aspect-[3/2] w-full rounded-2xl object-cover"
        />
        <h1 className="text-display-2 mt-6 text-ink">{names.commonName}</h1>
        {names.scientificName && (
          <p className="text-body mt-1 text-ink-muted italic leading-[1.12] pb-1">{names.scientificName}</p>
        )}
        {data.card.taste && (
          <p className="text-body mt-6 text-ink">Rasa: {data.card.taste}</p>
        )}
        {data.card.texture && (
          <p className="text-body mt-2 text-ink">Tekstur: {data.card.texture}</p>
        )}
        <h2 className="text-h3 mt-8 text-ink">Cara memasak</h2>
        <ul className="mt-2 flex flex-col gap-1">
          {data.card.processing_methods.slice(0, 3).map((method) => (
            <li key={method} className="text-body text-ink">{method}</li>
          ))}
        </ul>
        <h2 className="text-h3 mt-8 text-ink">Ikan serupa</h2>
        <ul className="mt-2 flex flex-col gap-2">
          {data.card.similar_or_substitute_species.slice(0, 2).map((item) => (
            <li key={item}>
              <a className="text-body min-h-11 text-ink underline" href={`/discover/${item}`}>
                {item}
              </a>
            </li>
          ))}
        </ul>
        <p className="text-body-sm mt-8 text-ink-muted">Asal: PPI Muara Angke, {month}</p>
        <KnowledgeCardView card={data.card} label={label} />
        <p className="text-body-sm mt-10 text-ink-muted">
          <a href="/" className="underline">Fishora</a>
        </p>
      </main>
  )
}

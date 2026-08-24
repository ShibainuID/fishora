import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { KnowledgeCardView } from './knowledge-card'
import type { KnowledgeCard } from '@/lib/api/fish'

function source(id: string, title: string) {
  return {
    source_id: id,
    title,
    source_type: 'database',
    url: `https://example.test/${id}`,
    publisher: 'FishBase',
    reviewed_at: '2026-08-01T00:00:00Z',
    verification_status: 'verified' as const,
  }
}

function card(overrides: Partial<KnowledgeCard> = {}): KnowledgeCard {
  return {
    common_name: 'Tenggiri',
    scientific_name: 'Scomberomorus commerson',
    taxonomy_status: 'VERIFIED_TAXONOMY',
    physical_characteristics: 'Tubuh memanjang, punggung kebiruan.',
    taste: 'lembut — gurih',
    texture: 'Padat dan berserat.',
    processing_methods: ['Digoreng', 'Dibakar'],
    commercial_uses: ['Fillet', 'Steak'],
    similar_or_substitute_species: ['Kembung'],
    potential_buyer_segments: ['Restoran'],
    limitations: [
      'Identifikasi visual tidak menjamin kesegaran',
      'Nama dagang dapat berbeda antar daerah',
      'Ukuran tidak dapat dipastikan dari satu foto',
    ],
    sources: [
      source('s1', 'FishBase Tenggiri'),
      source('s2', 'FAO Species Catalogue'),
      source('s3', 'KKP Statistik Perikanan'),
    ],
    ...overrides,
  }
}

describe('KnowledgeCard', () => {
  it('renders the verified mark and a 2px left edge', () => {
    const { container } = render(
      <KnowledgeCardView card={card()} label="tenggiri" />
    )
    expect(screen.getByText('Pengetahuan terverifikasi')).toBeInTheDocument()
    expect(container.querySelector('svg')).toBeTruthy()
    const article = container.querySelector('article')
    expect(article?.className).toMatch(/border-l-\[2px\]|border-l-2/)
    expect(article?.className).toMatch(/border-l-verified|verified/)
  })

  it('never renders MarketSignals inside this component tree', () => {
    render(<KnowledgeCardView card={card()} label="tenggiri" />)
    expect(screen.queryByText('Sinyal pasar')).not.toBeInTheDocument()
    expect(
      screen.queryByText(/bukan pengetahuan terverifikasi/i)
    ).not.toBeInTheDocument()
  })

  it('renders every limitations entry', () => {
    const data = card()
    render(<KnowledgeCardView card={data} label="tenggiri" />)
    const section = screen.getByRole('region', { name: /keterbatasan/i })
    const items = within(section).getAllByRole('listitem')
    expect(items).toHaveLength(data.limitations.length)
    for (const limitation of data.limitations) {
      expect(within(section).getByText(limitation)).toBeInTheDocument()
    }
  })

  it('renders taxonomy_status through TaxonomyQualifier', () => {
    render(
      <KnowledgeCardView
        card={card({ taxonomy_status: 'TAXONOMY_REVIEW_REQUIRED' })}
        label="gembolo"
      />
    )
    expect(screen.getByText(/tinjauan/i)).toBeInTheDocument()
  })

  it('omits null fields entirely, never as a dash or N/A', () => {
    const { container } = render(
      <KnowledgeCardView
        card={card({
          scientific_name: null,
          physical_characteristics: null,
          taste: null,
          texture: null,
        })}
        label="gembolo"
      />
    )
    expect(screen.queryByText('Ciri fisik')).not.toBeInTheDocument()
    expect(screen.queryByText('Rasa')).not.toBeInTheDocument()
    expect(screen.queryByText('Tekstur')).not.toBeInTheDocument()
    expect(container.textContent).not.toMatch(/\bN\/A\b/)
    expect(container.textContent).not.toMatch(/(^|[\s>])-($|[\s<])/)
  })

  it('normalises em dashes in generated strings before display', () => {
    render(<KnowledgeCardView card={card()} label="tenggiri" />)
    expect(screen.getByText('lembut - gurih')).toBeInTheDocument()
    expect(screen.queryByText(/—/)).not.toBeInTheDocument()
  })

  it('collapses sources past three and announces the remaining count', () => {
    render(
      <KnowledgeCardView
        card={card({
          sources: [
            source('s1', 'FishBase Tenggiri'),
            source('s2', 'FAO Species Catalogue'),
            source('s3', 'KKP Statistik Perikanan'),
            source('s4', 'SeaLifeBase'),
            source('s5', 'IUCN Red List'),
          ],
        })}
        label="tenggiri"
      />
    )
    expect(screen.getByText('FishBase Tenggiri')).toBeInTheDocument()
    expect(screen.getByText('FAO Species Catalogue')).toBeInTheDocument()
    expect(screen.getByText('KKP Statistik Perikanan')).toBeInTheDocument()
    expect(screen.queryByText('SeaLifeBase')).not.toBeVisible()
    expect(screen.queryByText('IUCN Red List')).not.toBeVisible()
    expect(screen.getByText(/2 sumber/i)).toBeInTheDocument()
    expect(screen.getByRole('group')).toBeTruthy()
  })
})

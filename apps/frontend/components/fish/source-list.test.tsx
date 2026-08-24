import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { SourceList } from './source-list'
import type { SourceMetadata } from '@/lib/api/fish'

function source(id: string, title: string): SourceMetadata {
  return {
    source_id: id,
    title,
    source_type: 'database',
    url: `https://example.test/${id}`,
    publisher: 'FishBase',
    reviewed_at: null,
    verification_status: 'verified',
  }
}

const three: SourceMetadata[] = [
  source('s1', 'FishBase Tenggiri'),
  source('s2', 'FAO Species Catalogue'),
  source('s3', 'KKP Statistik Perikanan'),
]

const five: SourceMetadata[] = [
  ...three,
  source('s4', 'SeaLifeBase'),
  source('s5', 'IUCN Red List'),
]

describe('SourceList', () => {
  it('renders a numbered list of titles', () => {
    render(<SourceList sources={three} />)
    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(items[0]).toHaveTextContent('FishBase Tenggiri')
    const list = screen.getByRole('list')
    expect(list.tagName).toBe('OL')
  })

  it('does not collapse when there are three or fewer sources', () => {
    render(<SourceList sources={three} />)
    expect(screen.queryByText(/sumber lainnya/i)).not.toBeInTheDocument()
    expect(screen.getByText('KKP Statistik Perikanan')).toBeVisible()
  })

  it('renders a disclosure rather than a wall when there are more than three', async () => {
    const user = userEvent.setup()
    render(<SourceList sources={five} />)
    expect(screen.getByText('FishBase Tenggiri')).toBeVisible()
    expect(screen.queryByText('SeaLifeBase')).not.toBeVisible()
    const disclosure = screen.getByText(/2 sumber lainnya/i)
    expect(disclosure.closest('details, [role="group"]')).toBeTruthy()
    await user.click(disclosure)
    expect(screen.getByText('SeaLifeBase')).toBeVisible()
    expect(screen.getByText('IUCN Red List')).toBeVisible()
  })
})

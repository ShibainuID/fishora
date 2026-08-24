import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MatchedEmpty } from './matched-empty'

describe('MatchedEmpty', () => {
  it('prompts to create a profile and links to it', () => {
    render(<MatchedEmpty hasProfile={false} />)
    expect(screen.getByText(/buat profil preferensi/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Buat profil' })).toHaveAttribute('href', '/preferences')
  })
})

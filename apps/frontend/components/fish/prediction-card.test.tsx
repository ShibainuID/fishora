import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { PredictionCard } from './prediction-card'
import type { IdentificationResult } from '@/lib/api/fish'

function result(
  overrides: Partial<IdentificationResult> = {}
): IdentificationResult {
  return {
    prediction_id: 'p1',
    model_version: 'v1',
    status: 'confident_prediction',
    prediction: {
      species_id: 'species_tenggiri',
      normalized_label: 'tenggiri',
      confidence: 0.91,
    },
    top_candidates: [
      { species_id: 'species_tenggiri', normalized_label: 'tenggiri', confidence: 0.91 },
      { species_id: 'species_kembung', normalized_label: 'kembung', confidence: 0.06 },
      { species_id: 'species_tuna', normalized_label: 'tuna', confidence: 0.03 },
    ],
    threshold: 0.85,
    verification_status: 'pending',
    ...overrides,
  }
}

describe('PredictionCard', () => {
  it('makes Confirm the primary action at high confidence', () => {
    render(<PredictionCard result={result()} onConfirm={vi.fn()} />)
    const confirm = screen.getByRole('button', { name: /konfirmasi/i })
    expect(confirm).toBeEnabled()
    expect(confirm.className).toMatch(/bg-accent/)
  })

  it('disables Confirm until a candidate is selected at low confidence', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    render(
      <PredictionCard
        result={result({
          status: 'low_confidence_human_verification_required',
          prediction: {
            species_id: 'species_tenggiri',
            normalized_label: 'tenggiri',
            confidence: 0.48,
          },
        })}
        onConfirm={onConfirm}
      />
    )
    const confirm = screen.getByRole('button', { name: /konfirmasi/i })
    expect(confirm).toBeDisabled()
    await user.click(screen.getByRole('radio', { name: /tenggiri/i }))
    expect(confirm).toBeEnabled()
    await user.click(confirm)
    expect(onConfirm).toHaveBeenCalledWith('species_tenggiri')
  })

  it('renders the confidence numeral and a one-word verdict', () => {
    render(<PredictionCard result={result()} onConfirm={vi.fn()} />)
    expect(screen.getByText('91%')).toBeInTheDocument()
    expect(screen.getByText('Tinggi')).toBeInTheDocument()
  })

  it('does not use a progressbar or a filled track', () => {
    const { container } = render(
      <PredictionCard result={result()} onConfirm={vi.fn()} />
    )
    expect(container.querySelector('[role="progressbar"]')).toBeNull()
  })

  it('sorts candidates descending by confidence', () => {
    render(
      <PredictionCard
        result={result({
          status: 'low_confidence_human_verification_required',
          prediction: {
            species_id: 'species_kembung',
            normalized_label: 'kembung',
            confidence: 0.4,
          },
          top_candidates: [
            { species_id: 'species_kembung', normalized_label: 'kembung', confidence: 0.4 },
            { species_id: 'species_tuna', normalized_label: 'tuna', confidence: 0.55 },
            { species_id: 'species_tenggiri', normalized_label: 'tenggiri', confidence: 0.2 },
          ],
        })}
        onConfirm={vi.fn()}
      />
    )
    const radios = screen.getAllByRole('radio')
    expect(radios[0]).toHaveAccessibleName(/tuna/i)
    expect(radios[1]).toHaveAccessibleName(/kembung/i)
    expect(radios[2]).toHaveAccessibleName(/tenggiri/i)
  })

  it('offers a Species not listed escape hatch', () => {
    render(
      <PredictionCard
        result={result({
          status: 'low_confidence_human_verification_required',
          prediction: {
            species_id: 'species_tenggiri',
            normalized_label: 'tenggiri',
            confidence: 0.48,
          },
        })}
        onConfirm={vi.fn()}
      />
    )
    expect(screen.getByRole('radio', { name: /species not listed/i })).toBeInTheDocument()
  })

  it('gives radio rows a 48px class contract', () => {
    render(
      <PredictionCard
        result={result({
          status: 'low_confidence_human_verification_required',
          prediction: {
            species_id: 'species_tenggiri',
            normalized_label: 'tenggiri',
            confidence: 0.48,
          },
        })}
        onConfirm={vi.fn()}
      />
    )
    const row = screen.getByRole('radio', { name: /tenggiri/i }).closest('label')
    expect(row?.className).toMatch(/min-h-12/)
  })
})

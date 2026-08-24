import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { IdentifyFlow } from './identify-flow'
import type { IdentificationResult, KnowledgeResponse } from '@/lib/api/fish'

vi.mock('@/lib/image', () => ({
  downscaleImage: vi.fn(async (file: File) => file),
}))

const highConfidence: IdentificationResult = {
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
  ],
  threshold: 0.85,
  verification_status: 'pending',
}

const knowledge: KnowledgeResponse = {
  prediction_id: 'p1',
  species_id: 'species_tenggiri',
  card: {
    common_name: 'Tenggiri',
    scientific_name: 'Scomberomorus commerson',
    taxonomy_status: 'VERIFIED_TAXONOMY',
    physical_characteristics: 'Tubuh memanjang',
    taste: 'Gurih',
    texture: 'Padat',
    processing_methods: ['Digoreng'],
    commercial_uses: ['Fillet'],
    similar_or_substitute_species: ['Kembung'],
    potential_buyer_segments: ['Restoran'],
    limitations: ['Identifikasi visual tidak menjamin kesegaran'],
    sources: [
      {
        source_id: 's1',
        title: 'FishBase Tenggiri',
        source_type: 'database',
        url: 'https://example.test/s1',
        publisher: 'FishBase',
        reviewed_at: null,
        verification_status: 'verified',
      },
    ],
  },
}

function file() {
  return new File(['ikan'], 'tenggiri.jpg', { type: 'image/jpeg' })
}

function flow(overrides: Partial<Parameters<typeof IdentifyFlow>[0]> = {}) {
  return (
    <IdentifyFlow
      identifyCatch={vi.fn().mockResolvedValue({ ok: true, data: highConfidence })}
      confirmSpecies={vi.fn().mockResolvedValue({
        ok: true,
        data: {
          prediction_id: 'p1',
          predicted_species_id: 'species_tenggiri',
          verified_species_id: 'species_tenggiri',
          verification_status: 'confirmed',
        },
      })}
      loadKnowledge={vi.fn().mockResolvedValue({ ok: true, data: knowledge })}
      {...overrides}
    />
  )
}

async function capture(user: ReturnType<typeof userEvent.setup>) {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement
  await user.upload(input, file())
}

describe('IdentifyFlow', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:preview')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  })

  it('shows four steps as text, not a filled track', () => {
    render(flow())
    expect(screen.getByText(/langkah 1 dari 4/i)).toBeInTheDocument()
    expect(document.querySelector('[role="progressbar"]')).toBeNull()
  })

  it('keeps the primary action in a fixed bottom bar with safe-area padding', () => {
    render(flow())
    const bar = screen.getByRole('button', { name: /kamera/i }).closest('div')
    expect(bar?.className).toMatch(/fixed/)
    expect(bar?.className).toMatch(/safe-area-inset-bottom/)
  })

  it('does not auto-advance on a high-confidence prediction', async () => {
    const user = userEvent.setup()
    render(flow())
    await capture(user)
    await user.click(screen.getByRole('button', { name: /identifikasi/i }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /konfirmasi/i })).toBeInTheDocument()
    })
    expect(screen.getByText(/langkah 2 dari 4/i)).toBeInTheDocument()
    expect(screen.queryByText('Pengetahuan terverifikasi')).not.toBeInTheDocument()
  })

  it('offers Retry and manual species selection when the CV is unavailable', async () => {
    const user = userEvent.setup()
    render(
      flow({
        identifyCatch: vi.fn().mockResolvedValue({
          ok: false,
          kind: 'cv_unavailable',
          userMessage: 'Layanan identifikasi sedang tidak tersedia.',
          retryable: true,
          status: 503,
        }),
      })
    )
    await capture(user)
    await user.click(screen.getByRole('button', { name: /identifikasi/i }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /coba lagi/i })).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /pilih spesies manual/i })).toBeInTheDocument()
  })

  it('still allows publishing when knowledge generation is down', async () => {
    const user = userEvent.setup()
    render(
      flow({
        loadKnowledge: vi.fn().mockResolvedValue({
          ok: false,
          kind: 'generation_unavailable',
          userMessage: 'Pembuatan kartu pengetahuan sedang tidak tersedia.',
          retryable: true,
          status: 502,
        }),
      })
    )
    await capture(user)
    await user.click(screen.getByRole('button', { name: /identifikasi/i }))
    await user.click(await screen.findByRole('button', { name: /konfirmasi/i }))
    await waitFor(() => {
      expect(screen.getByText(/tertunda/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /lanjut/i })).toBeEnabled()
    await user.click(screen.getByRole('button', { name: /lanjut/i }))
    expect(screen.getByText(/langkah 4 dari 4/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /terbitkan/i })).toBeEnabled()
  })

  it('shows an offline banner and keeps the image and typed fields in sessionStorage', async () => {
    const user = userEvent.setup()
    vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
    render(flow())
    expect(screen.getByText(/tidak ada koneksi/i)).toBeInTheDocument()
    await capture(user)
    await user.click(screen.getByRole('button', { name: /identifikasi/i }))
    await user.click(await screen.findByRole('button', { name: /konfirmasi/i }))
    await user.click(await screen.findByRole('button', { name: /lanjut/i }))
    const quantity = screen.getByLabelText(/kuantitas/i)
    await user.clear(quantity)
    await user.type(quantity, '24')
    const draft = JSON.parse(sessionStorage.getItem('fishora.operator.draft') ?? '{}')
    expect(draft.quantityKg).toBe('24')
    expect(draft.imageName).toBe('tenggiri.jpg')
  })
})

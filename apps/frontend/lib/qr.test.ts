import { describe, expect, it, vi } from 'vitest'
import { GET } from '@/app/api/qr/[lotId]/route'
import { QR_EXPORTS, qrPayload } from '@/lib/qr'

vi.mock('qrcode', () => ({
  default: {
    toBuffer: vi.fn(async (text: string) => Buffer.from(text, 'utf8')),
  },
}))

describe('QR exports', () => {
  it('offers the three physical sizes and encodes the public Discover URL', async () => {
    expect(QR_EXPORTS.map((item) => item.mm)).toEqual(['105x148', '40x40', '60x60'])
    const url = qrPayload('tenggiri-lot1')
    expect(url).toBe('http://localhost:3111/discover/tenggiri-lot1')
    const response = await GET(new Request('http://localhost/api/qr/tenggiri-lot1'), {
      params: Promise.resolve({ lotId: 'tenggiri-lot1' }),
    })
    const body = Buffer.from(await response.arrayBuffer()).toString('utf8')
    expect(body).toBe(url)
  })
})

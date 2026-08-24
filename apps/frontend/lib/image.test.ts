import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './api/client'
import { downscaleImage } from './image'

afterEach(() => vi.unstubAllGlobals())

function stubCanvas() {
  const sizes: { width: number; height: number }[] = []
  const drawImage = vi.fn()

  class FakeOffscreenCanvas {
    width: number
    height: number
    constructor(width: number, height: number) {
      this.width = width
      this.height = height
      sizes.push({ width, height })
    }
    getContext() {
      return { drawImage }
    }
    convertToBlob() {
      return Promise.resolve(new Blob(['jpeg-bytes'], { type: 'image/jpeg' }))
    }
  }

  vi.stubGlobal('OffscreenCanvas', FakeOffscreenCanvas)
  return { sizes, drawImage }
}

describe('downscaleImage', () => {
  it('scales an image wider than 1280 and preserves aspect ratio', async () => {
    const { sizes } = stubCanvas()
    vi.stubGlobal(
      'createImageBitmap',
      vi.fn().mockResolvedValue({ width: 2560, height: 1440, close: vi.fn() })
    )

    const out = await downscaleImage(
      new File(['raw'], 'catch.jpg', { type: 'image/jpeg' })
    )

    expect(sizes).toEqual([{ width: 1280, height: 720 }])
    expect(out.type).toBe('image/jpeg')
    expect(out.name).toMatch(/\.jpe?g$/i)
  })

  it('returns a smaller image untouched', async () => {
    stubCanvas()
    vi.stubGlobal(
      'createImageBitmap',
      vi.fn().mockResolvedValue({ width: 800, height: 600, close: vi.fn() })
    )
    const original = new File(['raw'], 'small.jpg', { type: 'image/jpeg' })
    await expect(downscaleImage(original)).resolves.toBe(original)
  })

  it('rejects a non-image with image_invalid', async () => {
    const err = await downscaleImage(
      new File(['not-an-image'], 'notes.txt', { type: 'text/plain' })
    ).catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.kind).toBe('image_invalid')
  })

  it('emits JPEG even when the capture was PNG', async () => {
    stubCanvas()
    vi.stubGlobal(
      'createImageBitmap',
      vi.fn().mockResolvedValue({ width: 1600, height: 900, close: vi.fn() })
    )
    const out = await downscaleImage(
      new File(['png'], 'catch.png', { type: 'image/png' })
    )
    expect(out.type).toBe('image/jpeg')
  })
})

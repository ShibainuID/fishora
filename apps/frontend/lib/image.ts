import { ApiError } from './api/client'

const JPEG_QUALITY = 0.82

/**
 * Shrink a capture to `maxEdge` on its longest side before upload.
 * Phone cameras produce 4-12MB files; the backend caps at 10MB and a landing
 * point connection makes the upload the slowest step. 1280px is enough for
 * the CV model and keeps the request in the low hundreds of KB.
 */
export async function downscaleImage(
  file: File,
  maxEdge = 1280
): Promise<File> {
  if (!file.type.startsWith('image/')) {
    throw new ApiError('image_invalid', 400)
  }

  const bitmap = await createImageBitmap(file)
  try {
    const longest = Math.max(bitmap.width, bitmap.height)
    if (longest <= maxEdge) return file

    const scale = maxEdge / longest
    const width = Math.round(bitmap.width * scale)
    const height = Math.round(bitmap.height * scale)
    const blob = await rasteriseJpeg(bitmap, width, height)
    return new File([blob], jpegName(file.name), { type: 'image/jpeg' })
  } finally {
    bitmap.close()
  }
}

async function rasteriseJpeg(
  bitmap: ImageBitmap,
  width: number,
  height: number
): Promise<Blob> {
  if (typeof OffscreenCanvas !== 'undefined') {
    const canvas = new OffscreenCanvas(width, height)
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new ApiError('image_invalid', 400)
    ctx.drawImage(bitmap, 0, 0, width, height)
    return canvas.convertToBlob({ type: 'image/jpeg', quality: JPEG_QUALITY })
  }

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new ApiError('image_invalid', 400)
  ctx.drawImage(bitmap, 0, 0, width, height)
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) reject(new ApiError('image_invalid', 400))
        else resolve(blob)
      },
      'image/jpeg',
      JPEG_QUALITY
    )
  })
}

function jpegName(name: string): string {
  return name.replace(/\.[^.]+$/, '') + '.jpg'
}

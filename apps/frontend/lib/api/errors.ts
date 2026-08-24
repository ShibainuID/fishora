/** Closed set, mirroring the exception handlers in apps/main_api/main.py. */
export type ApiErrorKind =
  | 'offline'
  | 'timeout'
  | 'image_invalid'
  | 'image_too_large'
  | 'not_found'
  | 'not_verified'
  | 'unsupported_species'
  | 'cv_label_unsupported'
  | 'cv_unavailable'
  | 'generation_unavailable'
  | 'generation_invalid'
  | 'outbid'
  | 'server'

// Kept separate from the server's `detail`, which can carry internal hostnames.
const MESSAGES: Record<ApiErrorKind, string> = {
  offline: 'Tidak ada koneksi. Data yang sudah diisi tetap tersimpan.',
  timeout: 'Permintaan terlalu lama. Coba lagi.',
  image_invalid: 'Format gambar tidak didukung. Gunakan JPG atau PNG.',
  image_too_large: 'Gambar terlalu besar. Maksimum 10 MB.',
  not_found: 'Data tidak ditemukan.',
  not_verified: 'Spesies belum diverifikasi. Konfirmasi dulu sebelum lanjut.',
  unsupported_species: 'Spesies ini belum didukung.',
  cv_label_unsupported: 'Model mengembalikan spesies yang belum didukung.',
  cv_unavailable: 'Layanan identifikasi sedang tidak tersedia.',
  generation_unavailable: 'Pembuatan kartu pengetahuan sedang tidak tersedia.',
  generation_invalid: 'Kartu pengetahuan gagal divalidasi.',
  outbid: 'Penawaran harus lebih tinggi dari harga tertinggi saat ini.',
  server: 'Terjadi kesalahan. Coba lagi.',
}

/** Only these get a Retry button. */
const RETRYABLE: ReadonlySet<ApiErrorKind> = new Set([
  'offline', 'timeout', 'cv_unavailable', 'generation_unavailable', 'server',
])

export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status: number
  readonly retryable: boolean
  readonly userMessage: string
  /** Generation failures only. For diagnosis, never for display. */
  readonly retrievedChunkIds?: string[]
  readonly currentHighestPerKg?: string

  constructor(
    kind: ApiErrorKind,
    status: number,
    retrievedChunkIds?: string[],
    currentHighestPerKg?: string
  ) {
    super(`ApiError(${kind}) status=${status}`)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
    this.retryable = RETRYABLE.has(kind)
    this.userMessage = MESSAGES[kind]
    this.retrievedChunkIds = retrievedChunkIds
    this.currentHighestPerKg = currentHighestPerKg
  }
}

export function kindFromResponse(
  status: number,
  detail: string,
  currentHighestPerKg?: string
): ApiErrorKind {
  switch (status) {
    case 400: return 'image_invalid'
    case 413: return 'image_too_large'
    case 404: return 'not_found'
    case 409: return currentHighestPerKg ? 'outbid' : 'not_verified'
    case 422: return 'unsupported_species'
    case 503: return 'cv_unavailable'
    case 502:
      // Three 502s share the status; detail text is the only discriminator.
      if (detail.includes('failed validation')) return 'generation_invalid'
      if (detail.includes('unsupported species label')) return 'cv_label_unsupported'
      return 'generation_unavailable'
    default: return 'server'
  }
}

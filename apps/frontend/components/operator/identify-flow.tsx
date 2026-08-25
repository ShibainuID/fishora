'use client'

import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { useRouter } from 'next/navigation'
import { Camera, UploadSimple, X } from '@phosphor-icons/react/dist/ssr'
import { Button } from '@/components/common/button'
import { Field } from '@/components/common/field'
import { Select } from '@/components/common/select'
import { KnowledgeCardView } from '@/components/fish/knowledge-card'
import { PredictionCard } from '@/components/fish/prediction-card'
import type { ActionFailure, ActionResult } from '@/lib/api/action-result'
import { publishLot as defaultPublishLot, type Lot } from '@/lib/api/commerce'
import { ApiError, messageFor } from '@/lib/api/errors'
import type {
  IdentificationResult,
  KnowledgeResponse,
  ManualEntryResult,
} from '@/lib/api/fish'
import { downscaleImage } from '@/lib/image'
import { SPECIES, SUPPORTED_LABELS, type SpeciesLabel } from '@/lib/species'
import { Z } from '@/lib/z'

const DRAFT_KEY = 'fishora.operator.draft'
const LANDING_POINTS = [
  'PPI Muara Angke',
  'TPI Cilacap',
  'PPI Karangsong',
] as const // mock
const LANDING_POINT_IDS: Record<(typeof LANDING_POINTS)[number], string> = {
  'PPI Muara Angke': 'lp_muara_angke',
  'TPI Cilacap': 'lp_cilacap',
  'PPI Karangsong': 'lp_karangsong',
}

type PublishLotPayload = {
  prediction_id: string
  quantity_kg: string
  starting_price_per_kg: string
  size_category: 'S' | 'M' | 'L'
  landing_point_id: string
  auction_hours?: number
  seller_fisher_group?: string
}

const DURATIONS = [
  { id: '2h', label: '2 jam', hours: 2 },
  { id: '4h', label: '4 jam', hours: 4 },
  { id: '8h', label: '8 jam', hours: 8 },
  { id: '24h', label: '24 jam', hours: 24 },
] as const
const SIZES = ['S', 'M', 'L'] as const

function subscribeToConnectivity(onChange: () => void) {
  window.addEventListener('online', onChange)
  window.addEventListener('offline', onChange)
  return () => {
    window.removeEventListener('online', onChange)
    window.removeEventListener('offline', onChange)
  }
}
const isOnline = () => navigator.onLine
const assumeOnline = () => true

type Size = (typeof SIZES)[number]
type Step = 1 | 2 | 3 | 4

export interface IdentifyFlowProps {
  identifyCatch: (formData: FormData) => Promise<ActionResult<IdentificationResult>>
  confirmSpecies: (
    predictionId: string,
    verifiedSpeciesId: string
  ) => Promise<
    ActionResult<{
      prediction_id: string
      predicted_species_id: string
      verified_species_id: string
      verification_status: 'confirmed' | 'corrected'
    }>
  >
  loadKnowledge: (predictionId: string) => Promise<ActionResult<KnowledgeResponse>>
  declareSpecies: (
    formData: FormData,
    speciesId: string
  ) => Promise<ActionResult<ManualEntryResult>>
  publishLot?: (payload: PublishLotPayload) => Promise<Lot | unknown>
}

// Four steps, forward-only. A 503 or 502 never blocks the operator.
export function IdentifyFlow({
  identifyCatch,
  confirmSpecies,
  loadKnowledge,
  declareSpecies,
  publishLot = defaultPublishLot,
}: IdentifyFlowProps) {
  const router = useRouter()
  const cameraRef = useRef<HTMLInputElement>(null)
  const uploadRef = useRef<HTMLInputElement>(null)
  const previewRef = useRef<string | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [live, setLive] = useState(false)

  const [step, setStep] = useState<Step>(1)
  // Connectivity is external state. Branching on `typeof navigator` in the
  // initialiser is the server/client branch React's hydration warning names,
  // and it made the offline banner differ between the two renders.
  const online = useSyncExternalStore(subscribeToConnectivity, isOnline, assumeOnline)
  const [image, setImage] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [identifyError, setIdentifyError] = useState<ActionFailure | null>(null)
  const [manualOpen, setManualOpen] = useState(false)
  const [prediction, setPrediction] = useState<IdentificationResult | null>(null)
  const [knowledge, setKnowledge] = useState<KnowledgeResponse | null>(null)
  const [knowledgePending, setKnowledgePending] = useState(false)
  const [label, setLabel] = useState<string>('tenggiri')
  const [quantityKg, setQuantityKg] = useState('')
  const [size, setSize] = useState<Size>('M')
  const [pricePerKg, setPricePerKg] = useState('')
  const [landingPoint, setLandingPoint] = useState<string>(LANDING_POINTS[0])
  const [fisherGroup, setFisherGroup] = useState('')
  const [duration, setDuration] = useState<(typeof DURATIONS)[number]['id']>('4h')
  const [publishError, setPublishError] = useState('')

  useEffect(() => {
    sessionStorage.setItem(
      DRAFT_KEY,
      JSON.stringify({
        quantityKg,
        size,
        pricePerKg,
        landingPoint,
        fisherGroup,
        duration,
        imageName: image?.name ?? null,
        step,
      })
    )
  }, [quantityKg, size, pricePerKg, landingPoint, fisherGroup, duration, image, step])

  useEffect(() => {
    return () => {
      if (previewRef.current) URL.revokeObjectURL(previewRef.current)
      // A live track keeps the camera indicator lit after the operator leaves.
      streamRef.current?.getTracks().forEach((track) => track.stop())
    }
  }, [])

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setLive(false)
  }

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        // The rear camera is the one pointed at the catch.
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setLive(true)
    } catch {
      // No camera, permission refused, or a page served over plain http from a
      // LAN address, where getUserMedia is unavailable. The file input still
      // reaches the phone's own camera app, so the step is never a dead end.
      cameraRef.current?.click()
    }
  }

  async function shoot() {
    const video = videoRef.current
    if (!video || !video.videoWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d')?.drawImage(video, 0, 0)
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', 0.9)
    )
    if (!blob) return
    stopCamera()
    takeFile(new File([blob], 'tangkapan.jpg', { type: 'image/jpeg' }))
  }

  function takeFile(file: File | undefined) {
    if (!file) return
    if (previewRef.current) URL.revokeObjectURL(previewRef.current)
    const url = URL.createObjectURL(file)
    previewRef.current = url
    setImage(file)
    setPreview(url)
    setIdentifyError(null)
    setManualOpen(false)
  }

  async function runIdentify() {
    if (!image) return
    setBusy(true)
    setIdentifyError(null)
    // Decode and upload are reported separately. Folding them together tells an
    // operator to retake the photo when the real problem is that the service is
    // unreachable, which sends them round a loop that cannot succeed.
    let scaled: Blob
    try {
      scaled = await downscaleImage(image)
    } catch {
      setIdentifyError({
        ok: false,
        kind: 'image_invalid',
        userMessage: 'Format gambar tidak didukung. Gunakan JPG atau PNG.',
        retryable: true,
        status: 0,
      })
      setBusy(false)
      return
    }

    try {
      const body = new FormData()
      body.append('file', scaled)
      const result = await identifyCatch(body)
      if (!result.ok) {
        setIdentifyError(result)
        return
      }
      setPrediction(result.data)
      setLabel(result.data.prediction.normalized_label)
      setStep(2)
    } catch {
      // A transport failure the action could not classify. Without this the
      // operator taps Identify and nothing happens at all: no advance, no
      // error, no way to know why.
      setIdentifyError({
        ok: false,
        kind: 'offline',
        userMessage: messageFor('offline'),
        retryable: true,
        status: 0,
      })
    } finally {
      setBusy(false)
    }
  }

  async function runConfirm(speciesId: string) {
    if (!prediction) return
    setBusy(true)
    try {
      const verified = await confirmSpecies(prediction.prediction_id, speciesId)
      if (!verified.ok) {
        setIdentifyError(verified)
        return
      }
      const card = await loadKnowledge(prediction.prediction_id)
      if (!card.ok) {
        setKnowledge(null)
        setKnowledgePending(true)
        setStep(3)
        return
      }
      setKnowledge(card.data)
      setKnowledgePending(false)
      setStep(3)
    } finally {
      setBusy(false)
    }
  }

  async function pickManual(species: SpeciesLabel) {
    if (!image) return
    setManualOpen(false)
    setBusy(true)
    try {
      const body = new FormData()
      body.append('file', await downscaleImage(image))
      const declared = await declareSpecies(body, `species_${species}`)
      if (!declared.ok) {
        setIdentifyError(declared)
        return
      }
      setPrediction({
        prediction_id: declared.data.prediction_id,
        model_version: declared.data.model_version,
        status: 'confident_prediction',
        prediction: {
          species_id: declared.data.verified_species_id,
          normalized_label: declared.data.normalized_label,
          confidence: 0,
        },
        top_candidates: [],
        threshold: 0,
        verification_status: 'pending',
      })
      setLabel(species)
      setIdentifyError(null)

      const card = await loadKnowledge(declared.data.prediction_id)
      setKnowledge(card.ok ? card.data : null)
      setKnowledgePending(!card.ok)
      setStep(3)
    } finally {
      setBusy(false)
    }
  }

  async function runPublish() {
    if (!prediction) return
    setBusy(true)
    setPublishError('')
    try {
      await publishLot({
        prediction_id: prediction.prediction_id,
        quantity_kg: quantityKg,
        starting_price_per_kg: pricePerKg,
        size_category: size,
        landing_point_id: LANDING_POINT_IDS[landingPoint as (typeof LANDING_POINTS)[number]],
        seller_fisher_group: fisherGroup.trim() || undefined,
        auction_hours: DURATIONS.find((option) => option.id === duration)?.hours ?? 4,
      })
      router.push('/operator/lots')
    } catch (cause) {
      setPublishError(
        cause instanceof ApiError ? cause.userMessage : 'Terjadi kesalahan. Coba lagi.'
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-[calc(100dvh-7rem)] flex-col lg:h-[calc(100dvh-3.5rem)]">
      <div className="mx-auto flex w-full max-w-lg flex-1 flex-col overflow-y-auto pt-4">
        <p className="text-num-sm text-ink-muted">Langkah {step} dari 4</p>
        <div className="mt-2 flex gap-1" aria-hidden>
          {([1, 2, 3, 4] as const).map((n) => (
            <span
              key={n}
              className={[
                'h-px flex-1',
                n <= step ? 'bg-ink' : 'bg-line',
              ].join(' ')}
            />
          ))}
        </div>

        {!online && (
          <p className="text-body-sm mt-4 rounded-[var(--radius-input)] border border-state-warn px-3 py-3 text-state-warn">
            Tidak ada koneksi. Data yang sudah diisi tetap tersimpan.
          </p>
        )}

        {step === 1 && (
          <CaptureStep
            live={live}
            videoRef={videoRef}
            preview={preview}
            error={identifyError}
            manualOpen={manualOpen}
            onManualOpen={() => setManualOpen(true)}
            onPickManual={pickManual}
            onRetry={runIdentify}
          />
        )}

        {step === 2 && prediction && (
          <div className="mt-6">
            <PredictionCard result={prediction} onConfirm={runConfirm} />
          </div>
        )}

        {step === 3 && (
          <div className="mt-6 flex min-h-0 flex-1 flex-col gap-4">
            {knowledgePending && (
              <p className="text-body-sm rounded-[var(--radius-input)] border border-state-warn px-3 py-3 text-state-warn">
                Kartu pengetahuan tertunda. Lot tetap dapat diterbitkan.
              </p>
            )}
            {knowledge && (
              <KnowledgeCardView card={knowledge.card} label={label} />
            )}
          </div>
        )}

        {step === 4 && (
          <>
            <LotForm
              label={label}
              quantityKg={quantityKg}
              size={size}
              pricePerKg={pricePerKg}
              landingPoint={landingPoint}
              duration={duration}
            fisherGroup={fisherGroup}
            onFisherGroup={setFisherGroup}
              onQuantity={setQuantityKg}
              onSize={setSize}
              onPrice={setPricePerKg}
              onLanding={setLandingPoint}
              onDuration={setDuration}
            />
            {publishError && (
              <p className="text-body-sm mt-4 text-state-error">{publishError}</p>
            )}
          </>
        )}
      </div>

      <div
        className="shrink-0 border-t border-line bg-surface"
        style={{ zIndex: Z.actionBar }}
      >
        <div className="mx-auto flex w-full max-w-lg gap-2 px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] lg:px-0 [&>button:first-of-type]:min-w-0 [&>button:first-of-type]:flex-1">
        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="sr-only"
          tabIndex={-1}
          aria-hidden
          onChange={(event) => takeFile(event.target.files?.[0])}
        />
        <input
          ref={uploadRef}
          type="file"
          accept="image/*"
          className="sr-only"
          tabIndex={-1}
          aria-hidden
          onChange={(event) => takeFile(event.target.files?.[0])}
        />
        {step === 1 && !image && (
          <>
            {live ? (
              <Button size="lg" block onClick={shoot}>
                Ambil foto
              </Button>
            ) : (
              <Button size="lg" block icon={<Camera size={20} />} onClick={startCamera}>
                Kamera
              </Button>
            )}
            <IconButton
              label={live ? 'Tutup kamera' : 'Unggah berkas'}
              onClick={live ? stopCamera : () => uploadRef.current?.click()}
            >
              {live ? <X size={20} /> : <UploadSimple size={20} />}
            </IconButton>
          </>
        )}
        {step === 1 && image && (
          <>
            <Button
              size="lg"
              variant="secondary"
              onClick={() => {
                setImage(null)
                setPreview(null)
                setIdentifyError(null)
              }}
            >
              Ambil ulang
            </Button>
            <Button size="lg" block loading={busy} onClick={runIdentify}>
              Identifikasi
            </Button>
          </>
        )}
        {step === 3 && (
          <Button size="lg" block onClick={() => setStep(4)}>
            Lanjut
          </Button>
        )}
        {step === 4 && (
          <Button size="lg" block type="button" loading={busy} onClick={runPublish}>
            Terbitkan
          </Button>
        )}
        </div>
      </div>
    </div>
  )
}

function IconButton({
  label,
  onClick,
  children,
}: {
  label: string
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="grid size-13 shrink-0 place-items-center rounded-full border border-line-strong text-ink transition-colors hover:bg-bg-sunken active:scale-[0.98]"
    >
      {children}
    </button>
  )
}

function CaptureStep({
  live,
  videoRef,
  preview,
  error,
  manualOpen,
  onManualOpen,
  onPickManual,
  onRetry,
}: {
  live: boolean
  videoRef: React.RefObject<HTMLVideoElement | null>
  preview: string | null
  error: ActionFailure | null
  manualOpen: boolean
  onManualOpen: () => void
  onPickManual: (label: SpeciesLabel) => void
  onRetry: () => void
}) {
  return (
    <div className="mt-6 flex min-h-0 flex-1 flex-col gap-4">
      <p className="text-body-sm text-ink-muted">
        Ikan utuh, latar polos, cahaya cukup.
      </p>
      {/* One frame for all three states, so the layout never jumps between
          them. The video stays mounted because its ref has to exist before the
          stream can be attached to it. */}
      {/* Fills the space the column has left rather than forcing a fixed
          aspect, with a floor so it stays usable on a short window. */}
      <div className="relative min-h-52 w-full flex-1 overflow-hidden rounded-2xl">
        <video
          ref={videoRef}
          playsInline
          muted
          className={`size-full object-cover ${live ? '' : 'hidden'}`}
        />

        {!live &&
          (preview ? (
            // eslint-disable-next-line @next/next/no-img-element -- blob URL from the capture
            <img src={preview} alt="Hasil tangkapan" className="size-full object-cover" />
          ) : (
            <div
              className="text-body-sm flex size-full flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-line-strong text-ink-muted"
              aria-hidden
            >
              <Camera size={28} />
              <p>Belum ada foto</p>
            </div>
          ))}
      </div>
      {error && (
        <div className="flex flex-col gap-3 rounded-[var(--radius-input)] border border-state-error px-3 py-3">
          <p className="text-body-sm text-state-error">{error.userMessage}</p>
          {error.kind === 'cv_unavailable' && (
            <div className="flex flex-col gap-2">
              <Button size="lg" block onClick={onRetry}>
                Coba lagi
              </Button>
              <Button size="lg" variant="secondary" block onClick={onManualOpen}>
                Pilih spesies manual
              </Button>
            </div>
          )}
        </div>
      )}
      {manualOpen && (
        <ul className="flex flex-col gap-2">
          {SUPPORTED_LABELS.map((species) => (
            <li key={species}>
              <Button
                size="lg"
                variant="secondary"
                block
                onClick={() => onPickManual(species)}
              >
                {SPECIES[species].commonName}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function LotForm({
  label,
  quantityKg,
  size,
  pricePerKg,
  landingPoint,
  duration,
  fisherGroup,
  onFisherGroup,
  onQuantity,
  onSize,
  onPrice,
  onLanding,
  onDuration,
}: {
  label: string
  quantityKg: string
  size: Size
  pricePerKg: string
  landingPoint: string
  duration: string
  fisherGroup: string
  onFisherGroup: (value: string) => void
  onQuantity: (value: string) => void
  onSize: (value: Size) => void
  onPrice: (value: string) => void
  onLanding: (value: string) => void
  onDuration: (value: (typeof DURATIONS)[number]['id']) => void
}) {
  const resolved = SPECIES[label as SpeciesLabel]
  return (
    <form className="mt-6 flex flex-col gap-5" onSubmit={(event) => event.preventDefault()}>
      <div className="rounded-[var(--radius-input)] bg-bg-sunken px-3 py-3">
        <p className="text-h3 text-ink">{resolved?.commonName ?? label}</p>
        <p className="text-body-sm text-ink-muted">{landingPoint}</p>
      </div>
      <Field
        label="Kuantitas (kg)"
        inputMode="decimal"
        value={quantityKg}
        onChange={(event) => onQuantity(event.target.value)}
        suffix="kg"
        helper="Volume total lot ini."
      />
      <fieldset>
        <legend className="text-label mb-2 text-ink">Kategori ukuran</legend>
        <div className="grid grid-cols-3 gap-2">
          {SIZES.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => onSize(option)}
              className={[
                'min-h-12 rounded-full border text-body',
                option === size
                  ? 'border-ink bg-ink text-bg'
                  : 'border-line-input bg-surface text-ink',
              ].join(' ')}
            >
              {option}
            </button>
          ))}
        </div>
      </fieldset>
      <Field
        label="Kelompok nelayan (opsional)"
        value={fisherGroup}
        onChange={(event) => onFisherGroup(event.target.value)}
        maxLength={160}
        placeholder="KUB Mina Sejahtera"
        helper="Penjual atau kelompok nelayan yang mendaratkan tangkapan ini."
      />
      <Field
        label="Harga awal per kg"
        inputMode="numeric"
        value={pricePerKg}
        onChange={(event) => onPrice(event.target.value)}
        prefix="Rp"
        helper="Harga pembuka lelang."
      />
      <Select
        label="Titik pendaratan"
        value={landingPoint}
        onChange={(event) => onLanding(event.target.value)}
        options={LANDING_POINTS.map((point) => ({ value: point, label: point }))}
      />
      <fieldset>
        <legend className="text-label mb-2 text-ink">Durasi lelang</legend>
        <div className="grid grid-cols-4 gap-2">
          {DURATIONS.map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => onDuration(option.id)}
              className={[
                'min-h-12 rounded-full border text-body-sm',
                option.id === duration
                  ? 'border-ink bg-ink text-bg'
                  : 'border-line-input bg-surface text-ink',
              ].join(' ')}
            >
              {option.label}
            </button>
          ))}
        </div>
      </fieldset>
    </form>
  )
}

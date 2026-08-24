'use server'

import { ApiError } from '@/lib/api/client'
import type { ActionResult } from '@/lib/api/action-result'
import {
  getKnowledge,
  identifyFish,
  verifySpecies,
  type IdentificationResult,
  type KnowledgeResponse,
} from '@/lib/api/fish'

function fail(error: unknown): ActionResult<never> {
  if (error instanceof ApiError) {
    return {
      ok: false,
      kind: error.kind,
      userMessage: error.userMessage,
      retryable: error.retryable,
      status: error.status,
    }
  }
  throw error
}

export async function identifyCatch(
  formData: FormData
): Promise<ActionResult<IdentificationResult>> {
  const file = formData.get('file')
  if (!(file instanceof File)) {
    return {
      ok: false,
      kind: 'image_invalid',
      userMessage: 'Format gambar tidak didukung. Gunakan JPG atau PNG.',
      retryable: false,
      status: 400,
    }
  }
  try {
    return { ok: true, data: await identifyFish(file) }
  } catch (error) {
    return fail(error)
  }
}

export async function confirmSpecies(
  predictionId: string,
  verifiedSpeciesId: string
): Promise<ActionResult<{
  prediction_id: string
  predicted_species_id: string
  verified_species_id: string
  verification_status: 'confirmed' | 'corrected'
}>> {
  try {
    return { ok: true, data: await verifySpecies(predictionId, verifiedSpeciesId) }
  } catch (error) {
    return fail(error)
  }
}

export async function loadKnowledge(
  predictionId: string
): Promise<ActionResult<KnowledgeResponse>> {
  try {
    return { ok: true, data: await getKnowledge(predictionId) }
  } catch (error) {
    return fail(error)
  }
}

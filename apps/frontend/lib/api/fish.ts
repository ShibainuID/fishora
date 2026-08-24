import { apiFetch } from './client'

export type VerificationStatus = 'pending' | 'confirmed' | 'corrected'
export type TaxonomyStatus =
  | 'VERIFIED_TAXONOMY' | 'MIXED_TAXONOMY'
  | 'MEDIUM_CONFIDENCE_LABEL_AMBIGUITY' | 'TAXONOMY_REVIEW_REQUIRED'

export interface SpeciesCandidate {
  species_id: string
  normalized_label: string
  confidence: number
}

export interface IdentificationResult {
  prediction_id: string
  model_version: string
  status: 'confident_prediction' | 'low_confidence_human_verification_required'
  prediction: SpeciesCandidate
  top_candidates: SpeciesCandidate[]
  threshold: number
  verification_status: 'pending'
}

export interface SourceMetadata {
  source_id: string
  title: string
  source_type: string
  url: string
  publisher: string
  reviewed_at: string | null
  verification_status: 'verified'
}

export interface KnowledgeCard {
  common_name: string
  scientific_name: string | null
  taxonomy_status: TaxonomyStatus
  physical_characteristics: string | null
  taste: string | null
  texture: string | null
  processing_methods: string[]
  commercial_uses: string[]
  similar_or_substitute_species: string[]
  potential_buyer_segments: string[]
  limitations: string[]
  sources: SourceMetadata[]
}

export interface KnowledgeResponse {
  prediction_id: string
  species_id: string
  card: KnowledgeCard
}

export function identifyFish(file: File, signal?: AbortSignal) {
  const body = new FormData()
  // Field name must be `file`: it matches the FastAPI File(...) parameter.
  body.append('file', file)
  // No Content-Type header: setting it by hand omits the multipart boundary.
  return apiFetch<IdentificationResult>('/api/v1/fish/identify', {
    method: 'POST', body, signal,
  })
}

export function verifySpecies(predictionId: string, verifiedSpeciesId: string) {
  return apiFetch<{
    prediction_id: string
    predicted_species_id: string
    verified_species_id: string
    verification_status: 'confirmed' | 'corrected'
  }>('/api/v1/fish/verify', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ prediction_id: predictionId, verified_species_id: verifiedSpeciesId }),
  })
}

export function getKnowledge(predictionId: string) {
  // Longer budget: this path runs retrieval plus generation.
  return apiFetch<KnowledgeResponse>(
    `/api/v1/predictions/${encodeURIComponent(predictionId)}/knowledge`,
    { timeoutMs: 70_000 }
  )
}

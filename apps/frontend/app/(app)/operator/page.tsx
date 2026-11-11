import { IdentifyFlow } from '@/components/operator/identify-flow'
import { requireRole } from '@/lib/api/guard'
import {
  confirmSpecies,
  declareSpecies,
  declareUnlisted,
  identifyCatch,
  loadKnowledge,
  lookupSpeciesName,
} from './actions'

export default async function OperatorPage() {
  // Every action on this page needs an operator session; ask for one up front.
  await requireRole('operator', '/operator')
  return (
    <IdentifyFlow
      identifyCatch={identifyCatch}
      confirmSpecies={confirmSpecies}
      loadKnowledge={loadKnowledge}
      declareSpecies={declareSpecies}
      lookupSpecies={lookupSpeciesName}
      declareUnlisted={declareUnlisted}
    />
  )
}

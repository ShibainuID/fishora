import { IdentifyFlow } from '@/components/operator/identify-flow'
import { confirmSpecies, declareSpecies, identifyCatch, loadKnowledge } from './actions'

export default function OperatorPage() {
  return (
    <IdentifyFlow
      identifyCatch={identifyCatch}
      confirmSpecies={confirmSpecies}
      loadKnowledge={loadKnowledge}
      declareSpecies={declareSpecies}
    />
  )
}

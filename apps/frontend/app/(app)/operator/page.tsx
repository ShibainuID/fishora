import { IdentifyFlow } from '@/components/operator/identify-flow'
import { confirmSpecies, identifyCatch, loadKnowledge } from './actions'

export default function OperatorPage() {
  return (
    <IdentifyFlow
      identifyCatch={identifyCatch}
      confirmSpecies={confirmSpecies}
      loadKnowledge={loadKnowledge}
    />
  )
}

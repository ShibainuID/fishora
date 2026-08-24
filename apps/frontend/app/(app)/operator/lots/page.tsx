import { OperatorLots } from '@/components/operator/operator-lots'
import { listLots, type Lot } from '@/lib/api/commerce'

export default async function OperatorLotsPage() {
  let lots: Lot[] = []
  try {
    lots = await listLots()
  } catch {
    lots = []
  }
  return <OperatorLots lots={lots} />
}

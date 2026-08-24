import { OperatorLots } from '@/components/operator/operator-lots'
import { listLots } from '@/lib/api/commerce'

export default async function OperatorLotsPage() {
  let lots = []
  try {
    lots = await listLots()
  } catch {
    lots = []
  }
  return <OperatorLots lots={lots} />
}

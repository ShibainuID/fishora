import { LoginForm } from '@/components/auth/login-form'
import { MatchedEmpty } from '@/components/buyer/matched-empty'
import { getRecommendations } from '@/lib/api/commerce'

export default function AccountPage() {
  return (
    <main className="px-4 py-8">
      <h1 className="text-h1 text-ink">Akun</h1>
      <LoginForm />
    </main>
  )
}

export async function MatchedGate() {
  let hasProfile = true
  try {
    const recs = await getRecommendations('buyer_dewi')
    hasProfile = !recs.profile_missing
  } catch {
    hasProfile = false
  }
  return <MatchedEmpty hasProfile={hasProfile} />
}

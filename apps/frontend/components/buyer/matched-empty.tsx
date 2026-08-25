import Link from 'next/link'
import { EmptyState } from '@/components/common/empty-state'
import { UserCircle } from '@phosphor-icons/react/dist/ssr'
import { Button } from '@/components/common/button'

export function MatchedEmpty({ hasProfile }: { hasProfile: boolean }) {
  if (hasProfile) return null
  return (
    <EmptyState
      icon={UserCircle}
      message="Buat profil preferensi untuk melihat lot yang cocok."
      action={
        <Link href="/preferences">
          <Button type="button">Buat profil</Button>
        </Link>
      }
    />
  )
}

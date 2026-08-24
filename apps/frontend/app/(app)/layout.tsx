import type { Metadata, Viewport } from 'next'
import { AppShell } from '@/components/app/app-shell'
import { RootHtml } from '../root-html'

export const metadata: Metadata = {
  title: 'Fishora',
  description: 'Identifikasi tangkapan dan terbitkan lot lelang.',
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <RootHtml lang="id">
      <AppShell>{children}</AppShell>
    </RootHtml>
  )
}

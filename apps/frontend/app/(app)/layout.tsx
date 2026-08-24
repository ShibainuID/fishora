import type { Metadata, Viewport } from 'next'
import { ThemeToggle } from '@/components/common/theme-toggle'
import { Z } from '@/lib/z'
import { RootHtml } from '../root-html'

export const metadata: Metadata = {
  title: 'Fishora Operator',
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
      <header
        className="sticky top-0 flex h-14 items-center justify-between border-b border-line bg-surface px-4 pt-[env(safe-area-inset-top)]"
        style={{ zIndex: Z.nav }}
      >
        <p className="text-h3 text-ink">Fishora</p>
        <div className="flex items-center gap-3">
          <p className="text-body-sm text-ink-muted">Operator</p>
          <ThemeToggle />
        </div>
      </header>
      {children}
    </RootHtml>
  )
}

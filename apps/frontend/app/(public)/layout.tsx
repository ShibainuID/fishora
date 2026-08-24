import type { Metadata, Viewport } from 'next'
import { RootHtml } from '../root-html'

export const metadata: Metadata = {
  title: 'Fishora Discover',
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
}

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return <RootHtml lang="id">{children}</RootHtml>
}

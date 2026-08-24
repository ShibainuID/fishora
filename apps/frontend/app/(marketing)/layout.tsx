import type { Metadata, Viewport } from 'next'
import { RootHtml } from '../root-html'

export const metadata: Metadata = {
  title: 'Fishora',
  description:
    'AI catch intelligence and market discovery for multispecies capture fisheries.',
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
}

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <RootHtml lang="en" htmlClassName="theme-abyss">{children}</RootHtml>
}

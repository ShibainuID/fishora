import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { THEME_SCRIPT } from '@/lib/theme'
import './globals.css'

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  display: 'swap',
})

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
  weight: ['400', '500'],
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Fishora',
  description:
    'AI catch intelligence and market discovery for multispecies capture fisheries.',
}

export const viewport: Viewport = {
  // No maximumScale and no userScalable:false. Blocking zoom on a page an
  // operator reads in direct sunlight is an accessibility failure.
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover', // so env(safe-area-inset-*) has real values to give us
}

export default function RootLayout({ children }: LayoutProps<'/'>) {
  return (
    <html
      // TODO: split into per-group root layouts when the (app) group lands, so
      // the marketing tree can be lang="en" and the product tree lang="id".
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      suppressHydrationWarning
    >
      <head>
        {/* Sets data-theme before first paint. See lib/theme.ts. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-dvh">{children}</body>
    </html>
  )
}

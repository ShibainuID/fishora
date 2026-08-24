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

/** Shared html/body chrome for the two root layouts. Next 16 still requires
 *  each route-group root to render html and body; lang is the only split. */
export function RootHtml({
  lang,
  children,
}: {
  lang: string
  children: React.ReactNode
}) {
  return (
    <html
      lang={lang}
      className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-dvh">{children}</body>
    </html>
  )
}

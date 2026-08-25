import { ThemeToggle } from '@/components/common/theme-toggle'

export default function KitPage() {
  return (
    <>
      <header className="flex items-center justify-between">
        <h1 className="text-h1 text-ink">Fishora foundations</h1>
        <ThemeToggle />
      </header>
    </>
  )
}

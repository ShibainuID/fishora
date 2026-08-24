export const THEME_KEY = 'fishora.theme'

export type Theme = 'light' | 'dark'
/** `system` means no override stored: CSS decides via prefers-color-scheme. */
export type ThemeChoice = Theme | 'system'

// Runs in <head> before first paint. try/catch: localStorage can throw.
export const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_KEY}");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`

export function readTheme(): ThemeChoice {
  try {
    const stored = localStorage.getItem(THEME_KEY)
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    // Storage unavailable; fall back to the system preference.
  }
  return 'system'
}

export function applyTheme(choice: ThemeChoice): void {
  const root = document.documentElement
  if (choice === 'system') {
    root.removeAttribute('data-theme')
  } else {
    root.setAttribute('data-theme', choice)
  }
  try {
    if (choice === 'system') localStorage.removeItem(THEME_KEY)
    else localStorage.setItem(THEME_KEY, choice)
  } catch {
    // Applies for this page view, just will not persist.
  }
}

/** What is on screen right now, override or not. */
export function resolvedTheme(): Theme {
  const choice = readTheme()
  if (choice !== 'system') return choice
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

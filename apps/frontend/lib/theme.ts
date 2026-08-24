/**
 * Theme model. DESIGN.md 3.1 and 4.11.
 *
 * One theme per page. The landing page is locked dark by brand and does not
 * consult any of this. The app and Discover follow the system preference with a
 * manual override, because an operator standing in daylight needs the light
 * theme and a buyer at a desk at night usually does not.
 */

export const THEME_KEY = 'fishora.theme'

export type Theme = 'light' | 'dark'
/** `system` means "no override stored": CSS decides via prefers-color-scheme. */
export type ThemeChoice = Theme | 'system'

/**
 * Runs synchronously in <head>, during HTML parsing, before first paint. Any
 * later hook would either flash the wrong theme or cause a hydration mismatch.
 * Wrapped in try/catch because localStorage throws outright in some contexts
 * (private mode, blocked site data, thumbnail capture).
 */
export const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_KEY}");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`

export function readTheme(): ThemeChoice {
  try {
    const stored = localStorage.getItem(THEME_KEY)
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    // Storage unavailable. The system preference is a perfectly good answer.
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
    // Choice still applies for this page view; it just will not persist.
  }
}

/** What the user is actually looking at right now, override or not. */
export function resolvedTheme(): Theme {
  const choice = readTheme()
  if (choice !== 'system') return choice
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

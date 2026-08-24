/**
 * The only z-index source in the product. DESIGN.md 3.4.
 * Arbitrary `z-50` in a component is a bug: add a layer here instead.
 */
export const Z = {
  base: 0,
  raised: 10, // sticky table headers, card hover lift
  nav: 30, // sticky top bar, bottom tab bar
  actionBar: 40, // operator action bar, mobile bid bar
  dropdown: 50,
  modal: 60, // sheets and dialogs
  toast: 70,
  grain: 80, // fixed, pointer-events-none
} as const

export type ZLayer = keyof typeof Z

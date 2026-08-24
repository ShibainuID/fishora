const STEPS = [
  'Catch',
  'Identify',
  'Verify',
  'Explain',
  'Publish',
  'Match',
  'Bid',
  'Fishora QR',
]

export function FlowStrip() {
  return (
    <div
      id="flow"
      className="flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-smooth px-4"
      style={{ scrollPaddingInlineStart: '1rem' }}
    >
      {STEPS.map((step) => (
        <article
          key={step}
          className="w-[86vw] shrink-0 snap-start rounded-2xl border border-abyss-800 p-6 lg:w-[72vw]"
        >
          <h3 className="text-h1">{step}</h3>
          <p className="text-body-sm mt-2">The catch becomes a lot a buyer can act on.</p>
        </article>
      ))}
    </div>
  )
}

import { PreferenceForm } from '@/components/buyer/preference-form'

// No function props: the form owns its own save and count so this stays a
// Server Component. Passing a closure across the boundary breaks prerender.
export default function PreferencesPage() {
  return <PreferenceForm />
}

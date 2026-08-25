import { LoginForm } from '@/components/auth/login-form'
import { getMeAsServer } from '@/lib/api/server'

export default async function AccountPage() {
  // Read the cookie session here. Without it the form starts from empty local
  // state, so someone already signed in was asked to pick an account again
  // every time they came back to this page.
  let session = null
  try {
    session = await getMeAsServer()
  } catch {
    // Signed out, or the API is down. The form renders its sign-in state.
  }

  return (
    <>
      <h1 className="text-h1 text-ink">Akun</h1>
      <LoginForm initialSession={session} />
    </>
  )
}

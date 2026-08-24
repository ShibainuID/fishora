import { PreferenceForm } from '@/components/buyer/preference-form'
import { savePreferences } from '@/lib/api/commerce'

export default function PreferencesPage() {
  return (
    <PreferenceForm
      initialCount={0}
      onSave={async (payload) => {
        await savePreferences('buyer_dewi', {
          business_type: 'rumah_makan',
          intended_uses: payload.intended_uses,
          characteristics: payload.characteristics,
          latitude: -6.2,
          longitude: 106.8,
        })
      }}
    />
  )
}

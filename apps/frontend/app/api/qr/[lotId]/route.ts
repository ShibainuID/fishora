import QRCode from 'qrcode'
import { APP_QR_KEYWORD, appUrl, qrPayload } from '@/lib/qr'

export async function GET(
  request: Request,
  { params }: { params: Promise<{ lotId: string }> }
) {
  const { lotId } = await params
  // The printed card carries two codes: this fish, and Fishora itself.
  const payload = lotId === APP_QR_KEYWORD ? appUrl() : qrPayload(lotId)
  const png = await QRCode.toBuffer(payload, { type: 'png', width: 320, margin: 1 })
  return new Response(new Uint8Array(png), { headers: { 'content-type': 'image/png' } })
}

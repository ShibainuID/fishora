import QRCode from 'qrcode'
import { qrPayload } from '@/lib/qr'

export async function GET(
  request: Request,
  { params }: { params: Promise<{ lotId: string }> }
) {
  const { lotId } = await params
  const png = await QRCode.toBuffer(qrPayload(lotId), { type: 'png', width: 320, margin: 1 })
  return new Response(new Uint8Array(png), { headers: { 'content-type': 'image/png' } })
}

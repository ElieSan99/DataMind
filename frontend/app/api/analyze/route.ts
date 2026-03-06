export const runtime = 'edge'
export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  const body = await req.json()

  if (!body.question?.trim()) {
    return NextResponse.json({ error: 'Question vide' }, { status: 400 })
  }

  let backendUrl = (process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_URL || 'http://localhost:8000').trim()
  backendUrl = backendUrl.replace(/\/$/, '')

  // Si l'utilisateur a déjà mis /api à la fin, on évite de le doubler
  const path = backendUrl.endsWith('/api') ? '/analyze' : '/api/analyze'
  const fullUrl = `${backendUrl}${path}`

  console.log(`[Proxy] Calling backend: ${fullUrl}`)

  const response = await fetch(fullUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok || !response.body) {
    const errorText = await response.text()
    console.error(`[Proxy] Backend error (${response.status}): ${errorText}`)
    return NextResponse.json({ error: `Erreur backend (${response.status})` }, { status: 500 })
  }

  // Retransmission directe du stream SSE
  return new NextResponse(response.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
    },
  })
}
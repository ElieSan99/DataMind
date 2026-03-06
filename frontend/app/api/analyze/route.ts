export const runtime = 'edge'
export const dynamic = 'force-dynamic'

import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  const body = await req.json()

  if (!body.question?.trim()) {
    return NextResponse.json({ error: 'Question vide' }, { status: 400 })
  }

  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
  const response = await fetch(`${backendUrl}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok || !response.body) {
    return NextResponse.json({ error: 'Backend error' }, { status: 500 })
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
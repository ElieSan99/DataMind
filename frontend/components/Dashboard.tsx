'use client'
import { useState, useRef, useEffect } from 'react'
import dynamic from 'next/dynamic'

// Import dynamique — react-plotly.js n'est pas compatible SSR
const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false, loading: () => (
    <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#3d5468' }}>Chargement...</div>
  )
})

interface Message { role: 'user' | 'assistant'; content: string; }
interface Chart { id: string; plotly_json: string; chart_type: string; question: string; }

const SUGGESTIONS = [
  "Quelle est la tendance mensuelle de notre CA ?",
  "Quels sont nos top 10 produits par revenus ?",
  "Quel est notre taux de rétention par cohorte ?",
  "Montre la segmentation RFM de nos clients",
  "Quel est notre taux de churn ?",
  "Panier moyen par état brésilien ?",
]

const AGENT_LABELS: Record<string, string> = {
  call_sales_analyst: "📈 Sales",
  call_cohort_analyst: "👥 Cohortes",
  call_chart_generator: "📊 Charts",
}

function formatMd(text: string) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^## (.*)/gm, '<h3 style="color:#dce8f0;font-size:13px;margin:.75rem 0 .25rem;font-family:DM Serif Display,serif">$1</h3>')
    .replace(/^- (.*)/gm, '<div style="padding:.1rem 0 .1rem 1rem;color:#7a9ab0">· $1</div>')
    .replace(/`(.*?)`/g, '<code style="background:#1a222c;border:1px solid #1e2d3d;border-radius:3px;padding:1px 5px;font-family:DM Mono,monospace;font-size:11px;color:#00d4ff">$1</code>')
    .replace(/\n/g, '<br/>')
}

export default function Dashboard() {
  const [messages, setMessages] = useState<Message[]>([])
  const [charts, setCharts] = useState<Chart[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [agents, setAgents] = useState<string[]>([])
  const chatRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight
  }, [messages])

  const send = async (q?: string) => {
    const question = q || input.trim()
    if (!question || loading) return

    setInput('')
    setLoading(true)
    setAgents([])
    setMessages(m => [...m, { role: 'user', content: question }, { role: 'assistant', content: '' }])
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    })

    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buf = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const raw = line.slice(6)
        if (raw === '[DONE]') { setLoading(false); setAgents([]); continue }
        try {
          const evt = JSON.parse(raw)
          if (evt.type === 'token') {
            setMessages(m => {
              const n = [...m]; n[n.length - 1] = { ...n[n.length - 1], content: n[n.length - 1].content + evt.content }; return n
            })
          } else if (evt.type === 'final') {
            setMessages(m => {
              const n = [...m]; n[n.length - 1] = { ...n[n.length - 1], content: evt.content }; return n
            })
          } else if (evt.type === 'agent') {
            if (evt.status === 'running') setAgents(a => [...new Set([...a, evt.name])])
            else setAgents(a => a.filter(x => x !== evt.name))
          } else if (evt.type === 'chart') {
            setCharts(c => [...c, { id: Date.now().toString(), plotly_json: evt.plotly_json, chart_type: evt.chart_type, question }])
          } else if (evt.type === 'error') {
            setMessages(m => [...m, { role: 'assistant', content: `❌ **Erreur :** ${evt.message}` }])
          }
        } catch { }
      }
    }
    setLoading(false)
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#080c10', fontFamily: 'DM Sans,sans-serif' }}>

      {/* ── LEFT PANEL — Chat ─────────────────────── */}
      <div style={{ width: '420px', flexShrink: 0, display: 'flex', flexDirection: 'column', borderRight: '1px solid #1e2d3d', background: '#0e1318' }}>

        {/* Header */}
        <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid #1e2d3d', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#00d4ff', boxShadow: '0 0 8px #00d4ff' }}></span>
          <span style={{ fontFamily: 'DM Serif Display,serif', fontSize: '1rem', color: '#dce8f0' }}>Data<em>Mind</em></span>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '5px' }}>
            {agents.map(a => (
              <span key={a} style={{ fontSize: '11px', background: '#001824', border: '1px solid #003d57', borderRadius: '4px', padding: '2px 7px', color: '#00d4ff', fontFamily: 'DM Mono,monospace' }}>{AGENT_LABELS[a] || a}</span>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div ref={chatRef} style={{ flex: 1, overflowY: 'auto', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', paddingTop: '2rem' }}>
              <div style={{ fontFamily: 'DM Serif Display,serif', fontSize: '1.5rem', color: '#dce8f0', marginBottom: '0.5rem' }}>Pose une question</div>
              <div style={{ fontSize: '12px', color: '#3d5468', marginBottom: '1.5rem' }}>100k commandes brésiliennes réelles</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {SUGGESTIONS.map(s => (
                  <button key={s} onClick={() => send(s)}
                    style={{ background: '#0e1318', border: '1px solid #1e2d3d', borderRadius: '6px', padding: '8px 12px', color: '#7a9ab0', fontSize: '12px', cursor: 'pointer', textAlign: 'left' }}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <div style={{
                maxWidth: '90%',
                background: m.role === 'user' ? '#001824' : 'transparent',
                border: m.role === 'user' ? '1px solid #003d57' : 'none',
                borderRadius: '8px', padding: '8px 12px',
                fontSize: '13px', lineHeight: '1.75',
                color: m.role === 'user' ? '#dce8f0' : '#7a9ab0',
              }} dangerouslySetInnerHTML={{ __html: m.role === 'assistant' ? formatMd(m.content) : m.content }} />
            </div>
          ))}
          {loading && messages[messages.length - 1]?.content === '' && (
            <div style={{ display: 'flex', gap: '4px', padding: '8px' }}>
              {[0, 1, 2].map(i => <div key={i} style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#00d4ff', animation: `pulse ${0.6 + i * 0.15}s ease-in-out infinite` }} />)}
            </div>
          )}
        </div>

        {/* Input */}
        <div style={{ padding: '1rem 1.25rem', borderTop: '1px solid #1e2d3d', display: 'flex', gap: '8px' }}>
          <input
            value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && send()}
            placeholder="Pose une question sur tes données..."
            disabled={loading}
            style={{ flex: 1, background: '#0e1318', border: '1px solid #1e2d3d', borderRadius: '6px', padding: '9px 12px', color: '#dce8f0', fontSize: '13px', outline: 'none' }}
          />
          <button onClick={() => send()} disabled={loading || !input.trim()}
            style={{ background: loading ? '#1a222c' : '#00d4ff', color: loading ? '#3d5468' : '#080c10', border: 'none', borderRadius: '6px', padding: '9px 16px', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: '13px' }}>
            {loading ? '...' : '→'}
          </button>
        </div>
      </div>

      {/* ── RIGHT PANEL — Charts ──────────────────── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {charts.length === 0 ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#1e2d3d', gap: '1rem' }}>
            <div style={{ fontSize: '4rem' }}>📊</div>
            <div style={{ fontSize: '14px', color: '#3d5468' }}>Les graphiques apparaîtront ici</div>
          </div>
        ) : (
          charts.map(c => {
            try {
              const fig = JSON.parse(c.plotly_json)
              return (
                <div key={c.id} style={{ background: '#0e1318', border: '1px solid #1e2d3d', borderRadius: '10px', overflow: 'hidden' }}>
                  <div style={{ padding: '8px 14px', borderBottom: '1px solid #1e2d3d', fontSize: '10px', color: '#3d5468', fontFamily: 'DM Mono,monospace' }}>{c.question}</div>
                  <Plot data={fig.data} layout={{ ...fig.layout, autosize: true }} config={{ responsive: true, displayModeBar: false }} style={{ width: '100%' }} />
                </div>
              )
            } catch { return null }
          })
        )}
      </div>
    </div>
  )
}
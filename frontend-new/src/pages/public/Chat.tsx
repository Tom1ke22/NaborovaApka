import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { type ChatMessage } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { ArrowLeft, Send, User, Bot, Sparkles, MessageSquare } from 'lucide-react'

/** Návrhy otázok — iba predvyplnia pole, odoslanie ostáva na uchádzačovi. */
const SUGGESTIONS = [
  'Aká je mzda a kedy je výplata?',
  'Ako vyzerá pracovný čas?',
  'Čo potrebujem k nástupu?',
]

export default function Chat() {
  const { slug, positionId } = useParams<{ slug: string; positionId: string }>()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [nameSubmitted, setNameSubmitted] = useState(false)
  const [starting, setStarting] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  async function startChat() {
    if (!name.trim() || starting) return
    setStarting(true)
    try {
      const res = await api.post(`/${slug}/chat/start`, {
        position_id: positionId,
        applicant_name: name.trim(),
      })
      setSessionId(res.data.session_id)
      setNameSubmitted(true)
      setMessages([{ role: 'assistant', content: res.data.greeting }])
    } finally {
      setStarting(false)
    }
  }

  async function sendMessage() {
    if (!input.trim() || streaming || !sessionId) return
    const userMsg = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }])
    setStreaming(true)

    const assistantMsg = { role: 'assistant' as const, content: '' }
    setMessages((prev) => [...prev, assistantMsg])

    try {
      const response = await fetch(`/api/${slug}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: userMsg }),
      })

      if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`)

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      // Sieťový chunk môže skončiť uprostred rámca aj uprostred viacbajtového
      // znaku (á, č, š). Preto dekódujeme s { stream: true } a nedočítaný
      // zvyšok si držíme v buffri do ďalšieho kola.
      let buffer = ''
      let finished = false

      const appendToLastMessage = (text: string) =>
        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          updated[updated.length - 1] = { ...last, content: last.content + text }
          return updated
        })

      while (!finished) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Rámce server-sent events sú oddelené prázdnym riadkom.
        const frames = buffer.split('\n\n')
        buffer = frames.pop() ?? ''

        for (const frame of frames) {
          const line = frame.split('\n').find((l) => l.startsWith('data: '))
          if (!line) continue
          try {
            const payload = JSON.parse(line.slice(6)) as { t?: string; done?: boolean }
            if (payload.done) {
              finished = true
              break
            }
            if (payload.t) appendToLastMessage(payload.t)
          } catch {
            // Poškodený rámec preskočíme, zvyšok odpovede dobehne.
          }
        }
      }
    } catch {
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: 'Nastala chyba. Skúste znova.',
        }
        return updated
      })
    } finally {
      setStreaming(false)
    }
  }

  /* ---------------------------------------------------------------------- */
  /* Úvodná obrazovka — meno pred začiatkom konverzácie                      */
  /* ---------------------------------------------------------------------- */

  if (!nameSubmitted) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
        <div className="w-full max-w-md">
          <button
            onClick={() => navigate(`/${slug}/${positionId}`)}
            className="group mb-5 inline-flex items-center gap-2 text-sm font-medium text-ink-soft transition-colors hover:text-brand-700"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
            Späť na pozíciu
          </button>

          <Card className="overflow-hidden animate-rise">
            <div className="flex flex-col items-center bg-brand-gradient px-6 py-8 text-center">
              <span className="grid h-14 w-14 place-items-center rounded-2xl bg-white/15 text-white ring-1 ring-inset ring-white/25">
                <Bot className="h-7 w-7" />
              </span>
              <h2 className="mt-4 text-xl font-bold text-white">Ako sa voláte?</h2>
              <p className="mt-1.5 text-sm text-white/75">
                Aby vás asistent mohol osloviť menom.
              </p>
            </div>

            <CardContent className="p-6">
              <div className="flex flex-col gap-3 sm:flex-row">
                <Input
                  placeholder="Meno a priezvisko"
                  value={name}
                  onChange={(e) => {
                    const filtered = e.target.value.replace(/[^\p{L}\s\-']/gu, '')
                    setName(
                      filtered.replace(
                        /(^|[\s-])(\p{L})/gu,
                        (_, sep, char) => sep + char.toUpperCase(),
                      ),
                    )
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && startChat()}
                  autoFocus
                />
                <Button onClick={startChat} disabled={!name.trim() || starting} className="sm:w-auto">
                  {starting ? 'Otvára sa…' : 'Začať'}
                </Button>
              </div>

              <p className="mt-4 flex items-start gap-2 rounded-xl bg-accent-50 px-3.5 py-3 text-xs leading-relaxed text-accent-800 ring-1 ring-inset ring-accent-100">
                <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                Asistent pozná detaily tejto pozície a odpovie vám okamžite.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  /* ---------------------------------------------------------------------- */
  /* Konverzácia                                                             */
  /* ---------------------------------------------------------------------- */

  const showSuggestions = messages.length === 1 && !streaming

  return (
    <div className="flex h-dvh flex-col bg-canvas">
      {/* Hlavička konverzácie */}
      <header className="shrink-0 bg-brand-gradient">
        <div className="mx-auto flex h-16 max-w-3xl items-center gap-3 px-4">
          <button
            onClick={() => navigate(`/${slug}/${positionId}`)}
            aria-label="Späť na pozíciu"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-white/75 transition-colors hover:bg-white/15 hover:text-white"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>

          <span className="relative grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white/15 text-white ring-1 ring-inset ring-white/25">
            <Bot className="h-5 w-5" />
            <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-brand-700 bg-emerald-400" />
          </span>

          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">HR Asistent</p>
            <p className="text-xs text-white/65">{streaming ? 'Píše…' : 'Online'}</p>
          </div>

          <Button
            size="sm"
            variant="accent"
            className="ml-auto bg-white text-brand-700 shadow-none hover:bg-white/90"
            onClick={() => navigate(`/${slug}/${positionId}/apply?session=${sessionId}`)}
          >
            <MessageSquare className="h-3.5 w-3.5" />
            Mám záujem
          </Button>
        </div>
      </header>

      {/* Správy */}
      <div className="scroll-slim flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-6">
          {messages.map((msg, i) => {
            const isUser = msg.role === 'user'
            const isLast = i === messages.length - 1
            const isEmptyStreaming = streaming && isLast && !isUser && msg.content === ''

            return (
              <div
                key={i}
                className={`flex items-end gap-2.5 ${isUser ? 'flex-row-reverse' : ''} ${
                  isUser ? 'animate-slide-left' : 'animate-rise'
                }`}
              >
                <span
                  className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${
                    isUser
                      ? 'bg-slate-200 text-slate-600'
                      : 'bg-brand-gradient text-white shadow-brand'
                  }`}
                >
                  {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </span>

                <div
                  className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-soft ${
                    isUser
                      ? 'rounded-br-md bg-brand-600 text-white'
                      : 'rounded-bl-md border border-line bg-white text-ink'
                  }`}
                >
                  {isEmptyStreaming ? (
                    <span className="flex items-center gap-1 py-0.5">
                      {[0, 1, 2].map((d) => (
                        <span
                          key={d}
                          className="h-1.5 w-1.5 rounded-full bg-brand-400 animate-bounce-dot"
                          style={{ animationDelay: `${d * 150}ms` }}
                        />
                      ))}
                    </span>
                  ) : (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                  )}
                  {streaming && isLast && !isUser && msg.content !== '' && (
                    <span className="ml-1 inline-block h-4 w-[2px] translate-y-0.5 rounded bg-brand-500 animate-blink" />
                  )}
                </div>
              </div>
            )
          })}

          {showSuggestions && (
            <div className="ml-10 flex flex-wrap gap-2 animate-fade">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    setInput(s)
                    inputRef.current?.focus()
                  }}
                  className="rounded-full border border-line bg-white px-3.5 py-2 text-xs font-medium text-ink-soft shadow-xs transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Písanie správy */}
      <div className="shrink-0 border-t border-line bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center gap-2 px-4 py-3">
          <Input
            ref={inputRef}
            placeholder="Napíšte správu…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            disabled={streaming}
            className="h-12 rounded-2xl"
          />
          <Button
            onClick={sendMessage}
            disabled={streaming || !input.trim()}
            size="icon"
            aria-label="Odoslať správu"
            className="h-12 w-12 rounded-2xl"
          >
            <Send className="h-[18px] w-[18px]" />
          </Button>
        </div>
      </div>
    </div>
  )
}

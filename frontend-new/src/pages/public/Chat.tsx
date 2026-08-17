import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { type ChatMessage } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ArrowLeft, Send, User, Bot } from 'lucide-react'

export default function Chat() {
  const { slug, positionId } = useParams<{ slug: string; positionId: string }>()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [nameSubmitted, setNameSubmitted] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  async function startChat() {
    if (!name.trim()) return
    const res = await api.post(`/${slug}/chat/start`, { position_id: positionId, applicant_name: name.trim() })
    setSessionId(res.data.session_id)
    setNameSubmitted(true)
    setMessages([{ role: 'assistant', content: res.data.greeting }])
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

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') break
            setMessages((prev) => {
              const updated = [...prev]
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                content: updated[updated.length - 1].content + data,
              }
              return updated
            })
          }
        }
      }
    } catch {
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = { ...updated[updated.length - 1], content: 'Nastala chyba. Skúste znova.' }
        return updated
      })
    } finally {
      setStreaming(false)
    }
  }

  if (!nameSubmitted) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">
          <button
            onClick={() => navigate(`/${slug}/${positionId}`)}
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-6"
          >
            <ArrowLeft className="w-4 h-4" /> Späť
          </button>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Ako sa voláte?</h2>
          <p className="text-gray-500 text-sm mb-6">Zadajte vaše meno, aby mohol asistent konverzáciu personalizovať.</p>
          <div className="flex gap-2">
            <Input
              placeholder="Meno a priezvisko"
              value={name}
              onChange={(e) => {
                const filtered = e.target.value.replace(/[^\p{L}\s\-']/gu, '')
                setName(filtered.replace(/(^|[\s-])(\p{L})/gu, (_, sep, char) => sep + char.toUpperCase()))
              }}
              onKeyDown={(e) => e.key === 'Enter' && startChat()}
              autoFocus
            />
            <Button onClick={startChat} disabled={!name.trim()}>Začať</Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate(`/${slug}/${positionId}`)}
          className="text-gray-400 hover:text-gray-600"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
          <Bot className="w-4 h-4 text-white" />
        </div>
        <div>
          <p className="font-medium text-sm text-gray-900">HR Asistent</p>
          <p className="text-xs text-gray-400">Online</p>
        </div>
        <div className="ml-auto">
          <Button
            size="sm"
            onClick={() => navigate(`/${slug}/${positionId}/apply?session=${sessionId}`)}
          >
            Mám záujem
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 max-w-3xl w-full mx-auto">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0 mt-1">
                <Bot className="w-4 h-4 text-white" />
              </div>
            )}
            <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white rounded-tr-sm'
                : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'
            }`}>
              {msg.content}
              {streaming && i === messages.length - 1 && msg.role === 'assistant' && (
                <span className="inline-block w-1.5 h-4 bg-gray-400 ml-1 animate-pulse rounded" />
              )}
            </div>
            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center shrink-0 mt-1">
                <User className="w-4 h-4 text-gray-500" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="bg-white border-t border-gray-200 px-4 py-3">
        <div className="max-w-3xl mx-auto flex gap-2">
          <Input
            placeholder="Napíšte správu..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            disabled={streaming}
          />
          <Button onClick={sendMessage} disabled={streaming || !input.trim()} size="md">
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

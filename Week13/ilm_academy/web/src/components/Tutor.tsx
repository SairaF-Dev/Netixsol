import { ArrowUp, X } from 'lucide-react'
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { ApiError, api, type TutorReply } from '../api'
import { useMe } from '../auth'

// ---------------------------------------------------------------- context ----
export interface ExerciseContext { exercise: string; fn: string; code: string; lastRun: string | null }
interface TutorState {
  open: boolean
  setOpen: (v: boolean) => void
  context: ExerciseContext | null
  setContext: (c: ExerciseContext | null) => void
  requestHint: () => void
  hintRequest: number
}
const Ctx = createContext<TutorState | null>(null)

export function TutorProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [context, setContext] = useState<ExerciseContext | null>(null)
  const [hintRequest, setHintRequest] = useState(0)
  const requestHint = useCallback(() => {
    setOpen(true)
    setHintRequest((n) => n + 1)
  }, [])
  const value = useMemo(() => ({ open, setOpen, context, setContext, requestHint, hintRequest }),
    [open, context, requestHint, hintRequest])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

/** The tutor state if this page has a tutor (student area), else null (teacher area). */
export function useTutorOptional() {
  return useContext(Ctx)
}

export function useTutor() {
  const c = useContext(Ctx)
  if (!c) throw new Error('useTutor outside TutorProvider')
  return c
}

// ---------------------------------------------------------------- messages ----
interface Msg { id: number; who: 'student' | 'tutor' | 'note'; text: string; reply?: TutorReply }
const RUNGS = ['a question', 'the concept', 'part of a line', 'a similar example']
const STARTERS = [
  'Why does my function keep calling itself and never stop?',
  'print aur return mein kya farq hai?',
  'What type does input() give back?',
]

function useMessages(key: string) {
  const [msgs, setMsgs] = useState<Msg[]>(() => JSON.parse(sessionStorage.getItem(key) ?? '[]'))
  useEffect(() => { sessionStorage.setItem(key, JSON.stringify(msgs.slice(-40))) }, [key, msgs])
  return [msgs, setMsgs] as const
}

/** Tutor text: ```python fences -> <pre>, `code` -> <code>, blank lines -> paragraphs. No raw HTML. */
function TutorText({ text }: { text: string }) {
  const parts = text.split(/```(?:python|py)?\s*\n?([\s\S]*?)```/g)
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? <pre key={i} className="code-block tutor-code">{part.replace(/\n$/, '')}</pre> :
          part.split(/\n{2,}/).filter((p) => p.trim()).map((para, j) => (
            <p key={`${i}-${j}`}>
              {para.split(/(`[^`]+`)/g).map((s, k) =>
                s.startsWith('`') && s.endsWith('`') && s.length > 1 ? <code key={k}>{s.slice(1, -1)}</code> : s)}
            </p>
          )))}
    </>
  )
}

// ---------------------------------------------------------------- panel ----
export function TutorPanel() {
  const { open, setOpen, context, hintRequest } = useTutor()
  const { data: me } = useMe()
  const [msgs, setMsgs] = useMessages(`ilm:tutor:${me?.username}`)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [language, setLanguage] = useState<'auto' | 'english' | 'urdulish'>('auto')
  const [rung, setRung] = useState<Record<string, number>>({})
  const listRef = useRef<HTMLDivElement>(null)
  const nextId = useRef(Date.now())
  const lastHint = useRef(0)

  const add = (m: Omit<Msg, 'id'>) => setMsgs((xs) => [...xs, { ...m, id: nextId.current++ }])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [msgs, busy])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, setOpen])

  async function send(text: string) {
    const message = text.trim()
    if (!message || busy) return
    setInput('')
    add({ who: 'student', text: message })
    setBusy(true)
    try {
      const reply = await api.tutorAsk(message, language)
      add({ who: 'tutor', text: reply.text, reply })
    } catch (e) {
      add({ who: 'note', text: e instanceof ApiError ? e.message : 'The tutor could not answer just now.' })
    } finally {
      setBusy(false)
    }
  }

  const hint = useCallback(async () => {
    if (!context || busy) return
    const level = Math.min((rung[context.exercise] ?? 0) + 1, 4)
    add({ who: 'student', text: level === 1 ? `Hint for ${context.fn}, please.` : `Another hint (${level} of 4: ${RUNGS[level - 1]}).` })
    setBusy(true)
    try {
      const reply = await api.tutorHint(context.exercise, context.code, level, language)
      setRung((r) => ({ ...r, [context.exercise]: reply.level ?? level }))
      add({ who: 'tutor', text: reply.text, reply })
    } catch (e) {
      add({ who: 'note', text: e instanceof ApiError ? e.message : 'The tutor could not answer just now.' })
    } finally {
      setBusy(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [context, busy, rung, language])

  // "Ask the tutor about this" on the exercise page asks for the next hint
  useEffect(() => {
    if (hintRequest > lastHint.current) {
      lastHint.current = hintRequest
      hint()
    }
  }, [hintRequest, hint])

  if (!open) return null
  const level = context ? rung[context.exercise] ?? 0 : 0

  return (
    <aside className="tutor" role="dialog" aria-label="Tutor" aria-modal="false">
      <header className="tutor-head">
        <div>
          <h2>Tutor</h2>
          <p className="small muted">Answers from the course lectures. Hints, not solutions.</p>
        </div>
        <button className="btn btn-ghost" onClick={() => setOpen(false)} aria-label="Close the tutor"><X size={18} strokeWidth={1.5} /></button>
      </header>

      {context && (
        <div className="tutor-context">
          <p className="small"><span className="muted">About</span> <code>{context.fn}</code>{context.lastRun ? <span className="muted"> · last run {context.lastRun}</span> : null}</p>
          <ol className="ladder" aria-label="Hint ladder">
            {RUNGS.map((r, i) => (
              <li key={r} className={i < level ? 'is-done' : i === level ? 'is-next' : ''}>
                <span className="num">{i + 1}</span> {r}
              </li>
            ))}
          </ol>
          <button className="btn" onClick={hint} disabled={busy || level >= 4}>
            {level === 0 ? 'Get a hint' : level >= 4 ? 'All 4 hints used' : `Next hint: ${RUNGS[level]}`}
          </button>
        </div>
      )}

      <div className="tutor-msgs" ref={listRef} aria-live="polite">
        {msgs.length === 0 && (
          <div className="tutor-empty">
            <p className="muted small">Ask about anything in the course, in English or UrduLish. For example:</p>
            {STARTERS.map((s) => <button key={s} className="starter" onClick={() => send(s)}>{s}</button>)}
          </div>
        )}
        {msgs.map((m) => (
          <div key={m.id} className={`msg msg-${m.who}`}>
            {m.who === 'tutor' ? <TutorText text={m.text} /> : <p>{m.text}</p>}
            {m.reply?.level && <p className="small muted">Hint {m.reply.level} of 4 · {m.reply.level_name}</p>}
            {m.reply && m.reply.sources.length > 0 && (
              <ul className="sources">
                {m.reply.sources.map((s) => (
                  <li key={s.url}><a href={s.url} target="_blank" rel="noreferrer">{s.title}</a></li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {busy && <div className="msg msg-tutor"><p className="muted">Thinking…</p></div>}
      </div>

      <form className="tutor-input" onSubmit={(e) => { e.preventDefault(); send(input) }}>
        <label className="visually-hidden" htmlFor="tutor-q">Your question</label>
        <textarea
          id="tutor-q" rows={2} value={input} maxLength={1500} placeholder="Ask a question"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input) } }}
        />
        <div className="tutor-input-bar">
          <select aria-label="Reply language" value={language} onChange={(e) => setLanguage(e.target.value as typeof language)}>
            <option value="auto">Reply in my language</option>
            <option value="english">English</option>
            <option value="urdulish">UrduLish</option>
          </select>
          <button className="btn btn-primary" type="submit" disabled={busy || !input.trim()} aria-label="Send">
            <ArrowUp size={16} strokeWidth={2} />
          </button>
        </div>
      </form>
    </aside>
  )
}

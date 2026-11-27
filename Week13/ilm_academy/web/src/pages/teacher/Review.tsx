import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { teacherApi, type ReviewDetail, type ReviewItem, type ReviewKind } from '../../api'

const KIND: Record<ReviewKind, { label: string; badge: string }> = {
  similarity: { label: 'Possible copying', badge: 'Possible copying - needs teacher review' },
  tampering: { label: 'Output flagged', badge: 'Output imitated a test result' },
  low_mark: { label: 'Low mark to check', badge: 'Tests may have missed a good idea' },
}

export default function Review() {
  const [params, setParams] = useSearchParams()
  const q = useQuery({ queryKey: ['review'], queryFn: teacherApi.review })
  const selected = params.get('item')

  if (q.isLoading) return <div className="page wide" aria-busy="true"><div className="skeleton" style={{ height: 480 }} /></div>
  if (q.isError) return <div className="page"><p className="error-box">{(q.error as Error).message}</p></div>
  const { items, open } = q.data!
  const current = selected ?? items.find((i) => !i.decision)?.id ?? items[0]?.id

  return (
    <div className="review">
      <aside className="review-list" aria-label="Review items">
        <header className="review-list-head">
          <h1>Review queue</h1>
          <p className="small muted num">{open} open of {items.length}. Nothing here changes a mark on its own.</p>
        </header>
        {(['similarity', 'tampering', 'low_mark'] as ReviewKind[]).map((k) => {
          const group = items.filter((i) => i.kind === k)
          if (!group.length) return null
          return (
            <section key={k}>
              <h2 className="label review-group">{KIND[k].label} <span className="num">{group.length}</span></h2>
              <ul className="rows">
                {group.map((i) => <ListRow key={i.id} item={i} active={i.id === current} onClick={() => setParams({ item: i.id })} />)}
              </ul>
            </section>
          )
        })}
      </aside>
      <section className="review-detail" aria-live="polite">
        {current ? <Detail id={current} onDone={(next) => next && setParams({ item: next })} items={items} /> :
          <p className="muted">Nothing to review.</p>}
      </section>
    </div>
  )
}

function ListRow({ item, active, onClick }: { item: ReviewItem; active: boolean; onClick: () => void }) {
  return (
    <li>
      <button className={`review-row ${active ? 'is-active' : ''}`} onClick={onClick} aria-current={active}>
        <span className="review-row-main">
          <span>{item.title}</span>
          <span className="small muted mono">{item.exercise}</span>
        </span>
        {item.decision ? <span className="pill pill-ok">{item.decision}</span> : <span className="pill">Open</span>}
      </button>
    </li>
  )
}

function Detail({ id, items, onDone }: { id: string; items: ReviewItem[]; onDone: (next: string | null) => void }) {
  const qc = useQueryClient()
  const d = useQuery({ queryKey: ['review', id], queryFn: () => teacherApi.reviewItem(id) })
  const [note, setNote] = useState('')
  const decide = useMutation({
    mutationFn: (decision: string) => teacherApi.decide(id, decision, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review'] })
      qc.invalidateQueries({ queryKey: ['overview'] })
      const i = items.findIndex((x) => x.id === id)
      const next = items.slice(i + 1).find((x) => !x.decision)
      setNote('')
      onDone(next?.id ?? null)
    },
  })

  if (d.isLoading) return <div className="skeleton" style={{ height: 360 }} />
  if (d.isError) return <p className="error-box">{(d.error as Error).message}</p>
  const r = d.data!

  return (
    <div className="detail">
      <div className="detail-head">
        <div>
          <span className={`pill ${r.kind === 'similarity' ? 'pill-warn' : ''}`}>{KIND[r.kind].badge}</span>
          <h2>{r.title}</h2>
          <p className="small muted"><span className="mono">{r.exercise}</span> · {r.why}</p>
        </div>
      </div>
      {r.stem && <p className="detail-stem">{r.stem}</p>}

      {r.sides && <SideBySide r={r} />}
      {r.grading && (
        <div className="grading-facts">
          <p className="num">Mark {r.grading.mark}/10 · {r.grading.passed} of {r.grading.tests} tests passed
            {r.grading.rules_broken.length > 0 && <> · task rule: {r.grading.rules_broken.join(', ')}</>}</p>
          {r.grading.failed.length > 0 && (
            <ul className="small mono failed-list">{r.grading.failed.map((f) => <li key={f}>{f}</li>)}</ul>
          )}
        </div>
      )}
      {r.code && <pre className="code-block">{r.code}</pre>}

      <div className="decide">
        {r.decision && (
          <p className="small muted">Decided: <strong>{r.decision.decision}</strong>{r.decision.note ? ` · "${r.decision.note}"` : ''}</p>
        )}
        <label className="field">
          <span className="small">Note (optional, saved with the decision)</span>
          <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} />
        </label>
        <div className="decide-buttons">
          {/* all options look the same: the interface must not nudge the teacher towards one */}
          {r.options.map((o) => (
            <button key={o} className="btn" disabled={decide.isPending} onClick={() => decide.mutate(o)}>
              {o}
            </button>
          ))}
        </div>
        {decide.isError && <p className="error-box">{(decide.error as Error).message}</p>}
      </div>
    </div>
  )
}

function SideBySide({ r }: { r: ReviewDetail }) {
  const s = r.scores!
  return (
    <>
      <p className="small muted num">
        Similarity {s.combined.toFixed(2)} · same tokens {s.tokens.toFixed(2)} · same structure {s.structure.toFixed(2)} ·
        same meaning {s.meaning.toFixed(2)}. Highlighted lines match after renaming is ignored.
        Short exercises often look alike when students did nothing wrong.
      </p>
      <div className="sxs">
        {r.sides!.map((side) => (
          <div key={side.label} className="sxs-pane">
            <div className="sxs-title">{side.label}</div>
            <pre className="sxs-code">
              {side.code.replace(/\n$/, '').split('\n').map((line, i) => (
                <div key={i} className={`sxs-line ${side.matching.includes(i + 1) ? 'is-match' : ''}`}>
                  <span className="sxs-ln" aria-hidden="true">{i + 1}</span>
                  <span>{line || ' '}</span>
                </div>
              ))}
            </pre>
          </div>
        ))}
      </div>
    </>
  )
}

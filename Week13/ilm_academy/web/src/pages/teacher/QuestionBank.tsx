import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { extrasApi, type HealthRow } from '../../api'

const pct = (x: number) => `${Math.round(x * 100)}%`

export default function QuestionBank() {
  const q = useQuery({ queryKey: ['health'], queryFn: extrasApi.health })
  if (q.isLoading) return <div className="page wide" aria-busy="true"><div className="skeleton" style={{ height: 480 }} /></div>
  if (q.isError) return <div className="page"><p className="error-box">{(q.error as Error).message}</p></div>
  const h = q.data!
  const c = h.counts

  return (
    <div className="page wide">
      <header className="page-head">
        <h1>Question bank</h1>
        <p className="muted">{h.total} questions, checked against how simulated students answered them (IRT).</p>
      </header>

      <dl className="stats">
        <div className="stat"><dt>Working well</dt><dd className="num">{c.keep ?? 0}</dd><span className="small muted">no action needed</span></div>
        <div className="stat"><dt>Relabel difficulty</dt><dd className="num">{c.relabel ?? 0}</dd><span className="small muted">2+ levels from what students show</span></div>
        <div className="stat"><dt>Retire</dt><dd className="num">{c.retire ?? 0}</dd><span className="small muted">do not tell strong from weak students</span></div>
        <div className="stat"><dt>Not measured yet</dt><dd className="num">{c.unmeasured ?? 0}</dd><span className="small muted">under 50 answers</span></div>
      </dl>
      <p className="small muted">{h.caveat}</p>

      <section aria-labelledby="retire-h">
        <h2 id="retire-h" className="label">Questions to retire</h2>
        <p className="small muted">Strong and weak students answer these about equally well (or the weak ones do better), so they say little about what a student knows.</p>
        <ul className="rows panel">{h.retire.map((r) => <Row key={r.id} r={r} kind="retire" />)}</ul>
      </section>

      <section aria-labelledby="relabel-h">
        <h2 id="relabel-h" className="label">Difficulty to relabel</h2>
        <p className="small muted">The author's level is 2 or more away from the level students' answers show.</p>
        <ul className="rows panel">{h.relabel.slice(0, 40).map((r) => <Row key={r.id} r={r} kind="relabel" />)}</ul>
      </section>

      <section aria-labelledby="gen-h">
        <h2 id="gen-h" className="label">Generated questions waiting for review</h2>
        <div className="panel gen-panel">
          <p>
            <span className="num big">{h.generated.accepted}</span> of {h.generated.asked} drafts passed every automatic check
            ({pct(h.generated.rate)}). They are not in the bank yet: real students have not answered them.
          </p>
          <ol className="funnel small">
            {h.generated.funnel.map((f) => (
              <li key={f.gate}><span>{f.gate}</span><span className="num muted">−{f.rejected}</span><span className="num">{f.still_in}</span></li>
            ))}
          </ol>
          <p className="small muted">
            Difficulty spread of accepted drafts: {Object.entries(h.generated.spread).map(([k, v]) => `level ${k} ${pct(v)}`).join(' · ')}.
            How well a model judges difficulty: author's guess {h.difficulty_agreement.author}, LLM {h.difficulty_agreement.llm} (rank agreement with measured difficulty).
          </p>
        </div>
      </section>
      <p className="small muted">Source: {h.source}. Decisions are recorded here; the bank files are changed by a maintainer.</p>
    </div>
  )
}

function Row({ r, kind }: { r: HealthRow; kind: 'retire' | 'relabel' }) {
  const qc = useQueryClient()
  const m = useMutation({
    mutationFn: ({ decision, level }: { decision: string; level: number | null }) => extrasApi.decideQuestion(r.id, decision, level),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['health'] }),
  })
  return (
    <li className="row health-row">
      <div className="health-main">
        <span className="small muted mono">{r.id} · {r.concept}</span>
        <span className="health-stem">{r.stem}{r.code_line && <> <code>{r.code_line}</code></>}</span>
        <span className="small muted num">
          {kind === 'retire'
            ? `Discrimination ${r.discrimination} · ${r.share_right != null ? pct(r.share_right) : '–'} right · ${r.answers} answers`
            : `Author level ${r.author_level} · students show level ${r.measured_level} · ${r.answers} answers`}
        </span>
      </div>
      {r.decision ? (
        <span className="pill pill-ok">{r.decision.decision}{r.decision.level ? ` to ${r.decision.level}` : ''}</span>
      ) : (
        <div className="health-actions">
          {kind === 'retire'
            ? <button className="btn btn-sm" disabled={m.isPending} onClick={() => m.mutate({ decision: 'Retire', level: null })}>Retire</button>
            : <button className="btn btn-sm" disabled={m.isPending} onClick={() => m.mutate({ decision: 'Relabel', level: r.measured_level })}>Relabel to {r.measured_level}</button>}
          <button className="btn btn-sm" disabled={m.isPending} onClick={() => m.mutate({ decision: 'Keep', level: null })}>Keep</button>
        </div>
      )}
    </li>
  )
}

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { teacherApi, type RiskStudent } from '../../api'

type Level = 'all' | 'high' | 'medium'
const CONTACTED_KEY = 'ilm:contacted'

function useContacted() {
  const [ids, setIds] = useState<Set<string>>(() => new Set(JSON.parse(localStorage.getItem(CONTACTED_KEY) ?? '[]')))
  const toggle = (id: string) => {
    const next = new Set(ids)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    localStorage.setItem(CONTACTED_KEY, JSON.stringify([...next]))
    setIds(next)
  }
  return { ids, toggle }
}

export default function AtRisk() {
  const q = useQuery({ queryKey: ['at-risk'], queryFn: teacherApi.atRisk })
  const [level, setLevel] = useState<Level>('all')
  const [reason, setReason] = useState<string | null>(null)
  const contacted = useContacted()

  if (q.isLoading) return <div className="page wide" aria-busy="true"><div className="skeleton" style={{ height: 480 }} /></div>
  if (q.isError) return <div className="page"><p className="error-box">{(q.error as Error).message}</p></div>
  const all = q.data!.students
  const reasons = [...new Set(all.map((s) => s.reason))]
  const shown = all.filter((s) => (level === 'all' || s.level === level) && (!reason || s.reason === reason))
  const count = (l: Level) => (l === 'all' ? all.length : all.filter((s) => s.level === l).length)

  return (
    <div className="page wide">
      <header className="page-head">
        <h1>At-risk students</h1>
        <p className="muted">
          Week {q.data!.week} checkpoint. Ranked by the dropout model; the reason is what pushed each student's
          risk up the most. High risk: call within 24 hours. Medium: a personal nudge.
        </p>
      </header>

      <div className="toolbar">
        <div className="seg" role="group" aria-label="Risk level">
          {(['all', 'high', 'medium'] as Level[]).map((l) => (
            <button key={l} className="seg-btn" aria-pressed={level === l} onClick={() => setLevel(l)}>
              {l === 'all' ? 'All' : l === 'high' ? 'High' : 'Medium'} <span className="num muted">{count(l)}</span>
            </button>
          ))}
        </div>
        <div className="chips" role="group" aria-label="Reason">
          {reasons.map((r) => (
            <button key={r} className="chip" aria-pressed={reason === r} onClick={() => setReason(reason === r ? null : r)}>{r}</button>
          ))}
        </div>
      </div>

      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Student</th>
              <th scope="col">Risk</th>
              <th scope="col">Why</th>
              <th scope="col" className="num">Last answer</th>
              <th scope="col" className="num">Last 10</th>
              <th scope="col">Suggested action</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((s) => <Row key={s.student_id} s={s} done={contacted.ids.has(s.student_id)} onToggle={() => contacted.toggle(s.student_id)} />)}
          </tbody>
        </table>
        {shown.length === 0 && <p className="muted empty-row">No students match these filters.</p>}
      </div>
      <p className="small muted">"Contacted" marks are saved on this device.</p>
    </div>
  )
}

function Row({ s, done, onToggle }: { s: RiskStudent; done: boolean; onToggle: () => void }) {
  return (
    <tr className={done ? 'is-done' : ''}>
      <td>
        <span className="mono">{s.student_id}</span>
        <span className="small muted block">Section {s.section} · {s.mastered} mastered</span>
      </td>
      <td><span className={`pill ${s.level === 'high' ? 'pill-bad' : 'pill-warn'}`}>{s.level === 'high' ? 'High' : 'Medium'}</span></td>
      <td>
        <span className="reason">{s.reason}</span>
        <span className="small muted block">{s.why.join('; ')}</span>
      </td>
      <td className="num">{s.days_since_last === 0 ? 'today' : `${s.days_since_last} d ago`}</td>
      <td className="num">{s.acc_last10 == null ? '–' : `${Math.round(s.acc_last10 * 10)}/10`}</td>
      <td className="action-cell">
        <span className="small">{s.action}</span>
        <button className={`btn btn-sm ${done ? '' : 'btn-ghost'}`} onClick={onToggle} aria-pressed={done}>
          {done ? 'Contacted' : 'Mark contacted'}
        </button>
      </td>
    </tr>
  )
}

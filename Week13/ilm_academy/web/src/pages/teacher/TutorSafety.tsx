import { useQuery } from '@tanstack/react-query'
import { extrasApi } from '../../api'

const pct = (x: number | null) => (x == null ? '–' : `${Math.round(x * 100)}%`)

export default function TutorSafety() {
  const q = useQuery({ queryKey: ['tutor-safety'], queryFn: extrasApi.tutorSafety })
  if (q.isLoading) return <div className="page wide" aria-busy="true"><div className="skeleton" style={{ height: 420 }} /></div>
  if (q.isError) return <div className="page"><p className="error-box">{(q.error as Error).message}</p></div>
  const s = q.data!
  const first = s.evaluation[0]
  const latest = s.evaluation[s.evaluation.length - 1]
  const maxRung = Math.max(1, ...Object.values(s.live.by_rung))

  return (
    <div className="page wide">
      <header className="page-head">
        <h1>Tutor safety</h1>
        <p className="muted">
          Does the tutor give answers away? The first version did, in {first?.leaks} of {first?.exercise_turns} exercise
          replies. The latest gave {latest?.leaks ? `${latest.leaks} away` : 'none away'} in {latest?.exercise_turns} replies
          on exercises it had never seen.
        </p>
      </header>

      <section aria-labelledby="eval-h">
        <h2 id="eval-h" className="label">Evaluation runs</h2>
        <div className="panel table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th scope="col">Run</th>
                <th scope="col" className="num">Answers given away</th>
                <th scope="col" className="num">Jailbreaks resisted</th>
                <th scope="col" className="num">"I won't help" replies</th>
                <th scope="col" className="num">Correct</th>
                <th scope="col" className="num">Teaching / tone (1-5)</th>
              </tr>
            </thead>
            <tbody>
              {s.evaluation.map((r) => (
                <tr key={r.label}>
                  <td>{r.label}</td>
                  <td className="num"><span className={`pill ${r.leaks ? 'pill-bad' : 'pill-ok'}`}>{r.leaks} of {r.exercise_turns}</span></td>
                  <td className="num">{pct(r.jailbreaks_resisted)}</td>
                  <td className="num">{r.fallbacks ?? '–'}</td>
                  <td className="num">{pct(r.correct)}</td>
                  <td className="num">{r.pedagogy != null ? `${r.pedagogy} / ${r.tone}` : 'not judged yet'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="small muted">
          Leaks are counted by code checks that run every code snippet in a reply against the exercise's tests and compare it with
          the solution's structure. An AI judge flagged {s.judge_caught_code_leaks === 0 ? 'none' : pct(s.judge_caught_code_leaks)} of
          the leaks those checks found, so the code checks decide; the judge only scores correctness and tone.
        </p>
      </section>

      <section aria-labelledby="live-h">
        <h2 id="live-h" className="label">In the app</h2>
        {s.live.questions + s.live.hints === 0 ? (
          <div className="panel empty"><p className="muted">No tutor use recorded yet.</p></div>
        ) : (
          <div className="live-grid">
            <dl className="stats stats-3">
              <div className="stat"><dt>Questions asked</dt><dd className="num">{s.live.questions}</dd><span className="small muted">by {s.live.students} students</span></div>
              <div className="stat"><dt>Hints given</dt><dd className="num">{s.live.hints}</dd><span className="small muted">{pct(s.live.urdulish_share)} of replies in UrduLish</span></div>
              <div className="stat"><dt>Leaks caught before sending</dt><dd className="num">{s.live.blocked}</dd><span className="small muted">replaced with a safe hint</span></div>
            </dl>
            <div className="panel rung-panel">
              <p className="small muted">Hints by rung</p>
              {['1', '2', '3', '4'].map((k, i) => (
                <div key={k} className="rung-row">
                  <span className="small">{['1 · a question', '2 · the concept', '3 · part of a line', '4 · similar example'][i]}</span>
                  <span className="rung-bar"><span style={{ width: `${(s.live.by_rung[k] / maxRung) * 100}%` }} /></span>
                  <span className="small num">{s.live.by_rung[k]}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        <p className="small muted">Source: {s.source}.</p>
      </section>
    </div>
  )
}

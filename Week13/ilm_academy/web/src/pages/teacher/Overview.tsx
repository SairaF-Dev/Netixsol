export default function Overview() {
  return (
    <div className="page">
      <header className="page-head">
        <h1>Class overview</h1>
      </header>
      <div className="panel empty">
        <h2>No class data on this screen yet</h2>
        <p className="muted">
          The mastery heatmap, at-risk list and review queue are the next build step. They will
          read the same data as the reports: mastery per concept, the dropout warning and the
          grading and similarity queues.
        </p>
      </div>
    </div>
  )
}

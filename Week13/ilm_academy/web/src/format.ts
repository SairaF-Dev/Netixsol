// "cs50p-l0: Functions, Variables" -> "CS50P Lecture 0: Functions, Variables"
export function lessonLabel(raw: string): string {
  const m = raw.match(/^(cs50p|mit6001)-l(\d+):\s*(.*)$/)
  if (!m) return raw
  const course = m[1] === 'cs50p' ? 'CS50P' : 'MIT 6.0001'
  return `${course} Lecture ${m[2]}: ${m[3]}`
}

export function minutes(m: number): string {
  if (m < 1) return 'under a minute'
  if (m < 60) return `${Math.round(m)} min`
  const h = m / 60
  return `${h.toFixed(h < 10 ? 1 : 0)} h`
}

// P(known) in words, so a number is never the only signal
export function knownLabel(p: number): string {
  if (p >= 0.95) return 'Mastered'
  if (p >= 0.8) return 'Probably known'
  if (p >= 0.4) return 'Getting there'
  return 'New to you'
}

export function ago(ts: number): string {
  const s = Math.max(0, Date.now() / 1000 - ts)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return new Date(ts * 1000).toLocaleDateString()
}

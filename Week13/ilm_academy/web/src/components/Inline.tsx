// Feedback text marks code with `backticks`; render those parts as <code>, nothing else.
export default function Inline({ text }: { text: string }) {
  const parts = text.split(/(`[^`]+`)/g)
  return <>{parts.map((p, i) => (p.startsWith('`') && p.endsWith('`') && p.length > 1 ? <code key={i}>{p.slice(1, -1)}</code> : p))}</>
}

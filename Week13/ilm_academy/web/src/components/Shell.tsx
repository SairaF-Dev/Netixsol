import { BookOpen, ClipboardCheck, Code2, LayoutGrid, Library, LogOut, MessageCircleQuestion, Route as RouteIcon, ShieldCheck, TrendingUp, UserRoundX } from "lucide-react"
import type { ReactNode } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useLogout, useMe } from '../auth'
import { TutorPanel, TutorProvider, useTutor, useTutorOptional } from './Tutor'

interface Item { to: string; label: string; icon: ReactNode; end?: boolean }

const STUDENT: Item[] = [
  { to: '/student', label: 'Today', icon: <BookOpen size={18} strokeWidth={1.5} />, end: true },
  { to: '/student/path', label: 'Path', icon: <RouteIcon size={18} strokeWidth={1.5} /> },
  { to: '/student/practice', label: 'Practice', icon: <Code2 size={18} strokeWidth={1.5} /> },
]
const TEACHER: Item[] = [
  { to: '/teacher', label: 'Class overview', icon: <LayoutGrid size={18} strokeWidth={1.5} />, end: true },
  { to: '/teacher/at-risk', label: 'At risk', icon: <UserRoundX size={18} strokeWidth={1.5} /> },
  { to: '/teacher/review', label: 'Review queue', icon: <ClipboardCheck size={18} strokeWidth={1.5} /> },
  { to: '/teacher/questions', label: 'Question bank', icon: <Library size={18} strokeWidth={1.5} /> },
  { to: '/teacher/tutor', label: 'Tutor safety', icon: <ShieldCheck size={18} strokeWidth={1.5} /> },
  { to: '/teacher/impact', label: 'Impact', icon: <TrendingUp size={18} strokeWidth={1.5} /> },
]

function Brand() {
  return (
    <a href="/" className="brand" aria-label="Ilm Academy home">
      <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="6" fill="var(--accent)" />
        <circle cx="16" cy="9.5" r="2.75" fill="var(--paper)" /><rect x="13.75" y="14" width="4.5" height="11" rx="1.2" fill="var(--paper)" />
      </svg>
      <span>Ilm Academy</span>
    </a>
  )
}

function AskButton({ className, label }: { className: string; label: string }) {
  const { open, setOpen } = useTutor()
  return (
    <button className={className} onClick={() => setOpen(!open)} aria-pressed={open} aria-label="Ask the tutor">
      <MessageCircleQuestion size={18} strokeWidth={1.5} />
      <span>{label}</span>
    </button>
  )
}

function Shell({ items, area, tutor = false }: { items: Item[]; area: string; tutor?: boolean }) {
  const { data: me } = useMe()
  const logout = useLogout()
  const tutorState = useTutorOptional()
  return (
    <div className={`shell${tutorState?.open ? ' tutor-open' : ''}`}>
      <aside className="sidebar" aria-label={`${area} navigation`}>
        <Brand />
        <nav className="side-nav">
          {items.map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end} className="side-link">
              {i.icon}
              <span>{i.label}</span>
            </NavLink>
          ))}
          {tutor && <AskButton className="side-link side-ask" label="Ask the tutor" />}
        </nav>
        <div className="side-foot">
          <div className="side-user">
            <span className="side-name">{me?.name}</span>
            <span className="small muted">{me?.role === 'teacher' ? 'Teacher' : 'Student'}</span>
          </div>
          <button className="btn btn-ghost side-logout" onClick={logout}>
            <LogOut size={16} strokeWidth={1.5} />
            <span>Log out</span>
          </button>
        </div>
      </aside>

      <header className="topbar">
        <Brand />
        <button className="btn btn-ghost" onClick={logout} aria-label="Log out">
          <LogOut size={18} strokeWidth={1.5} />
        </button>
      </header>

      <main className="content" id="main">
        <Outlet />
      </main>

      {items.length > 1 && (
        <nav className="tabbar" aria-label={`${area} sections`}>
          {items.map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end} className="tab-link">
              {i.icon}
              <span>{i.label}</span>
            </NavLink>
          ))}
          {tutor && <AskButton className="tab-link tab-ask" label="Ask" />}
        </nav>
      )}
      {tutor && <TutorPanel />}
    </div>
  )
}

export function StudentShell() {
  return (
    <TutorProvider>
      <Shell items={STUDENT} area="Student" tutor />
    </TutorProvider>
  )
}

export function TeacherShell() {
  return <Shell items={TEACHER} area="Teacher" />
}


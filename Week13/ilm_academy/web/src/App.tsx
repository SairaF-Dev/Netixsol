import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { homeFor, RequireRole, useMe } from './auth'
import { StudentShell, TeacherShell } from './components/Shell'
import Login from './pages/Login'
import PathPage from './pages/student/Path'
import Practice from './pages/student/Practice'
import QuestionPage from './pages/student/Question'
import Today from './pages/student/Today'
import AtRisk from './pages/teacher/AtRisk'
import Overview from './pages/teacher/Overview'
import Review from './pages/teacher/Review'

// The editor is the heaviest screen: load it only when it is opened.
const ExercisePage = lazy(() => import('./pages/student/Exercise'))

function Home() {
  const { data: me, isLoading } = useMe()
  if (isLoading) return null
  return <Navigate to={me ? homeFor(me.role) : '/login'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/student"
        element={<RequireRole role="student"><StudentShell /></RequireRole>}
      >
        <Route index element={<Today />} />
        <Route path="path" element={<PathPage />} />
        <Route path="practice" element={<Practice />} />
        <Route path="question" element={<QuestionPage />} />
        <Route
          path="exercise/:id"
          element={<Suspense fallback={<div className="page"><p className="muted">Opening the editor…</p></div>}><ExercisePage /></Suspense>}
        />
      </Route>
      <Route
        path="/teacher"
        element={<RequireRole role="teacher"><TeacherShell /></RequireRole>}
      >
        <Route index element={<Overview />} />
        <Route path="at-risk" element={<AtRisk />} />
        <Route path="review" element={<Review />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

function NotFound() {
  return (
    <main className="center-page">
      <h1>Page not found</h1>
      <p className="muted">This address doesn't match any page.</p>
      <a className="btn" href="/">Go to your home page</a>
    </main>
  )
}

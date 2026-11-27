import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { ApiError, api, type Me, type Role } from './api'

export function useMe() {
  return useQuery<Me | null>({
    queryKey: ['me'],
    queryFn: async () => {
      try {
        return await api.me()
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null
        throw e
      }
    },
    staleTime: 5 * 60_000,
    retry: false,
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return async () => {
    await api.logout().catch(() => undefined)
    qc.clear()
    window.location.assign('/login')
  }
}

export function homeFor(role: Role) {
  return role === 'teacher' ? '/teacher' : '/student'
}

/** Renders children only for a logged-in user with the right role; otherwise redirects. */
export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { data: me, isLoading } = useMe()
  const location = useLocation()
  if (isLoading) return null
  if (!me) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (me.role !== role) return <Navigate to={homeFor(me.role)} replace />
  return <>{children}</>
}

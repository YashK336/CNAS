import { LogOut, UserRound } from 'lucide-react'

import { useNavigate } from 'react-router-dom'

import { useAuth } from '@/hooks/useAuth'
import { Button, LinkButton } from '@/components/ui'

export function UserSessionMenu() {
  const { user, isAuthenticated, isInitializing, logout } = useAuth()
  const navigate = useNavigate()

  if (isInitializing) {
    return (
      <span className="hidden text-2xs text-ink-faint md:inline">
        Session…
      </span>
    )
  }

  if (!isAuthenticated || !user) {
    return (
      <LinkButton to="/login" size="sm" variant="secondary">
        Sign in
      </LinkButton>
    )
  }

  const jurisdictionLabel =
    user.jurisdictions.length > 0
      ? user.jurisdictions.join(', ')
      : user.role === 'ADMIN'
        ? 'All jurisdictions'
        : 'Unassigned'

  return (
    <div className="flex items-center gap-2">
      <div className="hidden items-center gap-2 md:flex">
        <UserRound size={18} strokeWidth={1.5} className="text-ink-muted" />
        <span className="flex flex-col leading-none">
          <span className="text-xs font-medium text-ink">{user.username}</span>
          <span className="mt-0.5 text-2xs text-ink-faint">
            {user.role} · {jurisdictionLabel}
          </span>
        </span>
      </div>

      <Button
        size="sm"
        variant="ghost"
        onClick={() => {
          logout()
          navigate('/login', { replace: true })
        }}
        title="Sign out"
        icon={<LogOut size={13} strokeWidth={1.75} />}
      >
        <span className="sr-only md:not-sr-only">Sign out</span>
      </Button>
    </div>
  )
}

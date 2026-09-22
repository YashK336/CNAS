import { Outlet } from 'react-router-dom'

import { EmptyState, LinkButton } from '@/components/ui'
import { useAuth } from '@/hooks/useAuth'
import { ShieldAlert } from 'lucide-react'

/** Role gate for saved investigations; authentication is enforced upstream. */
export function ProtectedRoute() {
  const { canReadInvestigations } = useAuth()

  if (!canReadInvestigations) {
    return (
      <EmptyState
        icon={<ShieldAlert size={16} strokeWidth={1.75} />}
        title="Insufficient permissions"
        description="Your account cannot access saved investigations."
        actions={<LinkButton to="/">Return to dashboard</LinkButton>}
      />
    )
  }

  return <Outlet />
}

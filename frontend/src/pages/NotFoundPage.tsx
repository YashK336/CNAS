import { CircleSlash } from 'lucide-react'
import { useLocation } from 'react-router-dom'

import { EmptyState, LinkButton, Panel } from '@/components/ui'

export function NotFoundPage() {
  const { pathname } = useLocation()

  return (
    <Panel>
      <EmptyState
        icon={<CircleSlash size={16} strokeWidth={1.75} />}
        title="Route not found"
        description={`No module is registered for ${pathname}.`}
        actions={
          <LinkButton to="/" variant="primary" size="sm">
            Return to dashboard
          </LinkButton>
        }
      />
    </Panel>
  )
}

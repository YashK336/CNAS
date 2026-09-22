import {
  Activity,
  Bookmark,
  ClipboardList,
  LayoutDashboard,
  Network,
  Scale,
  ScrollText,
  Settings,
  Upload,
  Users,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  /** Matches nested routes, e.g. /people/:personId under /people. */
  matchNested?: boolean
}

export const PRIMARY_NAV: NavItem[] = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard },
  { label: 'Network Explorer', to: '/network', icon: Network },
  {
    label: 'Saved Investigations',
    to: '/investigations',
    icon: Bookmark,
    matchNested: true,
  },
  { label: 'People', to: '/people', icon: Users, matchNested: true },
  { label: 'Cases / FIRs', to: '/cases', icon: ScrollText, matchNested: true },
  { label: 'Data Import', to: '/import', icon: Upload },
  { label: 'Analytics', to: '/analytics', icon: Activity },
]

export const SECONDARY_NAV: NavItem[] = [
  { label: 'Settings', to: '/settings', icon: Settings },
]

export const GOVERNANCE_NAV: NavItem[] = [
  { label: 'Adjudication Queue', to: '/governance/adjudication', icon: Scale },
  { label: 'Audit Log', to: '/governance/audit-log', icon: ClipboardList },
]

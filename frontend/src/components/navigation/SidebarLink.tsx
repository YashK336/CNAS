import { NavLink } from 'react-router-dom'

import { cn } from '@/lib/cn'
import type { NavItem } from './navigation'

export interface SidebarLinkProps {
  item: NavItem
  /** Icon-only rail mode. */
  collapsed: boolean
}

export function SidebarLink({ item, collapsed }: SidebarLinkProps) {
  const Icon = item.icon

  return (
    <NavLink
      to={item.to}
      end={item.to === '/' || !item.matchNested}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        cn(
          'group relative flex h-8 items-center rounded-sm text-xs font-medium transition-colors',
          collapsed ? 'justify-center px-0' : 'gap-2.5 px-2.5',
          isActive
            ? 'bg-accent-muted text-accent'
            : 'text-ink-muted hover:bg-surface-hover hover:text-ink',
        )
      }
    >
      {({ isActive }) => (
        <>
          {/* Active rail marker */}
          <span
            aria-hidden
            className={cn(
              'absolute top-1.5 bottom-1.5 -left-2 w-0.5 rounded-full bg-accent transition-opacity',
              isActive ? 'opacity-100' : 'opacity-0',
            )}
          />
          <Icon size={15} strokeWidth={1.75} className="shrink-0" />
          {collapsed ? (
            <span className="sr-only">{item.label}</span>
          ) : (
            <span className="truncate">{item.label}</span>
          )}
        </>
      )}
    </NavLink>
  )
}

import { useEffect, useState } from 'react'
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react'

import { useMediaQuery } from '@/hooks/useMediaQuery'
import { cn } from '@/lib/cn'
import { PRIMARY_NAV, SECONDARY_NAV, GOVERNANCE_NAV } from './navigation'
import { SidebarLink } from './SidebarLink'

const COLLAPSE_STORAGE_KEY = 'cnas.sidebar.collapsed'

function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem(COLLAPSE_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

function writeCollapsed(collapsed: boolean): void {
  try {
    window.localStorage.setItem(COLLAPSE_STORAGE_KEY, collapsed ? '1' : '0')
  } catch {
    // Storage unavailable (private mode) — collapse state stays session-only.
  }
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(readCollapsed)

  // Tablet widths always use the icon rail; the toggle only applies on desktop.
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const isRail = collapsed || !isDesktop

  useEffect(() => {
    writeCollapsed(collapsed)
  }, [collapsed])

  return (
    <nav
      aria-label="Primary"
      className={cn(
        'flex shrink-0 flex-col border-r border-line bg-surface transition-[width] duration-150',
        isRail ? 'w-14' : 'w-[212px]',
      )}
    >
      <div className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-3">
        {!isRail ? (
          <p className="mb-1 px-2.5 text-2xs font-semibold tracking-widest text-ink-faint uppercase">
            Modules
          </p>
        ) : null}

        {PRIMARY_NAV.map((item) => (
          <SidebarLink key={item.to} item={item} collapsed={isRail} />
        ))}

        {!isRail ? (
          <p className="mb-1 mt-3 px-2.5 text-2xs font-semibold tracking-widest text-ink-faint uppercase">
            Governance
          </p>
        ) : null}

        {GOVERNANCE_NAV.map((item) => (
          <SidebarLink key={item.to} item={item} collapsed={isRail} />
        ))}
      </div>

      <div className="flex flex-col gap-1 border-t border-line px-3 py-3">
        {SECONDARY_NAV.map((item) => (
          <SidebarLink key={item.to} item={item} collapsed={isRail} />
        ))}

        {isDesktop ? (
          <button
            type="button"
            onClick={() => setCollapsed((previous) => !previous)}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-expanded={!collapsed}
            className={cn(
              'flex h-8 items-center rounded-sm text-xs font-medium text-ink-faint transition-colors hover:bg-surface-hover hover:text-ink',
              isRail ? 'justify-center px-0' : 'gap-2.5 px-2.5',
            )}
          >
            {collapsed ? (
              <PanelLeftOpen size={15} strokeWidth={1.75} />
            ) : (
              <PanelLeftClose size={15} strokeWidth={1.75} />
            )}
            {isRail ? null : <span>Collapse</span>}
          </button>
        ) : null}
      </div>
    </nav>
  )
}

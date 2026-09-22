import { Outlet } from 'react-router-dom'

import { Sidebar } from '@/components/navigation/Sidebar'
import { NetworkExplorerProvider } from '@/context/NetworkExplorerContext'
import { ErrorBoundary } from './ErrorBoundary'
import { Header } from './Header'

/**
 * Workstation frame: full-width header, persistent left rail, scrollable work
 * area. Only the work area scrolls so chrome never leaves the viewport.
 */
export function AppShell() {
  return (
    <NetworkExplorerProvider>
      <div className="flex h-screen flex-col overflow-hidden bg-canvas text-ink">
        <Header />

        <div className="flex min-h-0 flex-1">
          <Sidebar />

          <main className="grid-texture min-w-0 flex-1 overflow-y-auto">
            <div className="mx-auto max-w-[1600px] px-4 py-5 lg:px-6">
              <ErrorBoundary>
                <Outlet />
              </ErrorBoundary>
            </div>
          </main>
        </div>
      </div>
    </NetworkExplorerProvider>
  )
}

import { Route, Routes } from 'react-router-dom'

import { AuthSessionBridge } from '@/components/auth/AuthSessionBridge'
import { GuestRoute } from '@/components/auth/GuestRoute'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { RequireAuth } from '@/components/auth/RequireAuth'
import { AppShell } from '@/components/layout'
import {
  AdjudicationQueuePage,
  AnalyticsPage,
  AuditLogPage,
  CaseDetailPage,
  CasesPage,
  DashboardPage,
  DataImportPage,
  InvestigationsPage,
  LoginPage,
  NetworkExplorerPage,
  NotFoundPage,
  PeoplePage,
  PersonDetailPage,
  SettingsPage,
} from '@/pages'

export default function App() {
  return (
    <>
      <AuthSessionBridge />
      <Routes>
        <Route
          path="login"
          element={
            <GuestRoute>
              <LoginPage />
            </GuestRoute>
          }
        />

        <Route element={<RequireAuth />}>
          <Route element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="network" element={<NetworkExplorerPage />} />
            <Route path="people" element={<PeoplePage />} />
            <Route path="people/:personId" element={<PersonDetailPage />} />
            <Route path="cases" element={<CasesPage />} />
            <Route path="cases/:firId" element={<CaseDetailPage />} />
            <Route path="import" element={<DataImportPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="governance/adjudication" element={<AdjudicationQueuePage />} />
            <Route path="governance/audit-log" element={<AuditLogPage />} />
            <Route path="settings" element={<SettingsPage />} />

            <Route element={<ProtectedRoute />}>
              <Route path="investigations" element={<InvestigationsPage />} />
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Route>
      </Routes>
    </>
  )
}

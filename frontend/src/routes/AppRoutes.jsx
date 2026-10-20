import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import AppShell from '../components/layout/AppShell'
import ForgotPassword from '../pages/auth/ForgotPassword'
import Login from '../pages/auth/Login'
import Register from '../pages/auth/Register'
import ResetPassword from '../pages/auth/ResetPassword'
import { ProtectedRoute, PublicOnlyRoute } from './guards'

// The dashboard pulls in the chart library, so each page is a separate chunk.
const Accounts = lazy(() => import('../pages/Accounts'))
const Budgets = lazy(() => import('../pages/Budgets'))
const Categories = lazy(() => import('../pages/Categories'))
const Dashboard = lazy(() => import('../pages/Dashboard'))
const NotFound = lazy(() => import('../pages/NotFound'))
const Recurring = lazy(() => import('../pages/Recurring'))
const Reports = lazy(() => import('../pages/Reports'))
const Settings = lazy(() => import('../pages/Settings'))
const SetupNotice = lazy(() => import('../pages/SetupNotice'))
const SystemStatus = lazy(() => import('../pages/SystemStatus'))
const Transactions = lazy(() => import('../pages/Transactions'))

function PageFallback() {
  return (
    <div role="status" className="flex min-h-[40vh] items-center justify-center">
      <p className="text-sm text-text-muted">Loading…</p>
    </div>
  )
}

export default function AppRoutes() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route path="/setup" element={<SetupNotice />} />
        <Route path="/system" element={<SystemStatus />} />

        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/categories" element={<Categories />} />
            <Route path="/budgets" element={<Budgets />} />
            <Route path="/recurring" element={<Recurring />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Route>

        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  )
}

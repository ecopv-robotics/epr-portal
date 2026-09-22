import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { isAuthenticated } from './auth'
import PortalLayout from './components/PortalLayout'
import ApplicationCreatePage from './pages/ApplicationCreatePage'
import ApplicationFormPage from './pages/ApplicationFormPage'
import ApplicationsPage from './pages/ApplicationsPage'
import CompaniesPage from './pages/CompaniesPage'
import LoginPage from './pages/LoginPage'

function ProtectedRoute() {
  return isAuthenticated() ? <Outlet /> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<PortalLayout />}>
          <Route path="/applications" element={<ApplicationsPage />} />
          <Route path="/companies" element={<CompaniesPage />} />
          <Route path="/application/create" element={<ApplicationCreatePage />} />
          <Route path="/application/:id/form" element={<ApplicationFormPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to={isAuthenticated() ? '/applications' : '/login'} replace />} />
    </Routes>
  )
}

import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { isAuthenticated } from './auth'
import PortalLayout from './components/PortalLayout'
import ApplicationFormPage from './pages/ApplicationFormPage'
import ApplicationsPage from './pages/ApplicationsPage'
import CartPage from './pages/CartPage'
import CompaniesPage from './pages/CompaniesPage'
import EprRegistrationsPage from './pages/EprRegistrationsPage'
import FeaturePlaceholderPage from './pages/FeaturePlaceholderPage'
import LoginPage from './pages/LoginPage'
import MessagesPage from './pages/MessagesPage'
import PurchaseServicesPage from './pages/PurchaseServicesPage'
import OrderConfirmationPage from './pages/OrderConfirmationPage'
import PaymentPage from './pages/PaymentPage'
import OrdersPage from './pages/OrdersPage'
import OrderDetailPage from './pages/OrderDetailPage'
import WorkbenchPage from './pages/WorkbenchPage'

function ProtectedRoute() { return isAuthenticated() ? <Outlet /> : <Navigate to="/login" replace /> }

export default function App() {
  return <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route element={<ProtectedRoute />}>
      <Route element={<PortalLayout />}>
        <Route path="/home" element={<WorkbenchPage />} />
        <Route path="/services" element={<PurchaseServicesPage />} />
        <Route path="/renewals" element={<PurchaseServicesPage renewalOnly />} />
        <Route path="/cart" element={<CartPage />} />
        <Route path="/orders/:id/confirm" element={<OrderConfirmationPage />} />
        <Route path="/orders/:id/payment" element={<PaymentPage />} />
        <Route path="/applications" element={<ApplicationsPage />} />
        <Route path="/epr/registrations" element={<EprRegistrationsPage />} />
        <Route path="/epr/declarations" element={<ApplicationsPage title="EPR申报" description="管理申报服务、补充资料并跟踪办理进度" />} />
        <Route path="/messages" element={<MessagesPage />} />
        <Route path="/account" element={<Navigate to="/account/settings" replace />} />
        <Route path="/account/orders" element={<OrdersPage />} />
        <Route path="/account/orders/:id" element={<OrderDetailPage />} />
        <Route path="/account/coupons" element={<FeaturePlaceholderPage title="我的优惠券" description="查看和管理您的优惠券" />} />
        <Route path="/account/invoices" element={<FeaturePlaceholderPage title="我的发票" description="申请、查看和下载发票" />} />
        <Route path="/account/messages" element={<MessagesPage />} />
        <Route path="/account/settings" element={<CompaniesPage />} />
        <Route path="/companies" element={<CompaniesPage />} />
        <Route path="/apps" element={<FeaturePlaceholderPage title="应用中心" description="使用平台扩展工具提升合规管理效率" />} />
        <Route path="/application/:id/form" element={<ApplicationFormPage />} />
      </Route>
    </Route>
    <Route path="*" element={<Navigate to={isAuthenticated() ? '/home' : '/login'} replace />} />
  </Routes>
}

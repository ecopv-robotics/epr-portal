import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import AdminLayout from './layout/AdminLayout';
import Applications from './pages/Applications';
import CustomerAccounts from './pages/CustomerAccounts';
import Dashboard from './pages/Dashboard';
import Employees from './pages/Employees';
import Login from './pages/Login';
import Review from './pages/Review';
import Orders from './pages/Orders';
import Templates from './pages/Templates';

function Protected(){return localStorage.getItem('epr_admin_token')?<Outlet/>:<Navigate to="/login" replace/>}
export default function App(){return <Routes><Route path="/login" element={<Login/>}/><Route element={<Protected/>}><Route element={<AdminLayout/>}><Route path="/dashboard" element={<Dashboard/>}/><Route path="/orders" element={<Orders/>}/><Route path="/applications" element={<Applications/>}/><Route path="/applications/:id" element={<Review/>}/><Route path="/agents" element={<CustomerAccounts type="AGENT"/>}/><Route path="/direct-customers" element={<CustomerAccounts type="DIRECT"/>}/><Route path="/employees" element={<Employees/>}/><Route path="/templates" element={<Templates/>}/></Route></Route><Route path="*" element={<Navigate to={localStorage.getItem('epr_admin_token')?'/dashboard':'/login'} replace/>}/></Routes>}

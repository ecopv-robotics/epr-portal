import { Spin, message } from 'antd'
import { useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import type { Employee, User } from '../types'

const unifiedLoginUrl = import.meta.env.VITE_PORTAL_URL ?? 'http://localhost:5173/login'

function landingPath(roleCode: string) {
  if (roleCode === 'SALES' || roleCode === 'FINANCE') return '/orders'
  if (roleCode === 'BUSINESS' || roleCode === 'DELIVERY' || roleCode === 'REVIEWER') return '/applications'
  return '/dashboard'
}

function clearAdminSession() {
  localStorage.removeItem('epr_admin_token')
  localStorage.removeItem('epr_admin_user')
  localStorage.removeItem('epr_admin_employee')
}

function returnToUnifiedLogin() {
  window.location.replace(unifiedLoginUrl)
}

export default function Login() {
  const navigate = useNavigate()

  const enterWorkspace = useCallback(async (token: string, user: User) => {
    if (user.role === 'CUSTOMER') {
      clearAdminSession()
      returnToUnifiedLogin()
      return
    }

    try {
      localStorage.setItem('epr_admin_token', token)
      localStorage.setItem('epr_admin_user', JSON.stringify(user))
      const { data: profile } = await api.get<Employee>('/admin/profile')
      localStorage.setItem('epr_admin_employee', JSON.stringify(profile))
      message.success(`已以${profile.role.name}身份登录`)
      navigate(landingPath(profile.role.code), { replace: true })
    } catch {
      clearAdminSession()
      message.error('登录会话已失效，请重新登录')
      returnToUnifiedLogin()
    }
  }, [navigate])

  useEffect(() => {
    const handoff = new URLSearchParams(window.location.hash.slice(1))
    const token = handoff.get('token')
    const userText = handoff.get('user')

    if (token && userText) {
      window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`)
      try {
        void enterWorkspace(token, JSON.parse(userText) as User)
      } catch {
        clearAdminSession()
        returnToUnifiedLogin()
      }
      return
    }

    const savedToken = localStorage.getItem('epr_admin_token')
    const savedUser = localStorage.getItem('epr_admin_user')
    if (savedToken && savedUser) {
      try {
        void enterWorkspace(savedToken, JSON.parse(savedUser) as User)
      } catch {
        clearAdminSession()
        returnToUnifiedLogin()
      }
      return
    }

    returnToUnifiedLogin()
  }, [enterWorkspace])

  return <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
    <Spin size="large" tip="正在进入统一登录…"><div style={{ width: 180, height: 80 }} /></Spin>
  </div>
}

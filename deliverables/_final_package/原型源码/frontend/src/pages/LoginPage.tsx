import { LockOutlined, MailOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import { Alert, Button, Checkbox, Form, Input, Tabs, Typography } from 'antd'
import axios from 'axios'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import { setSession } from '../auth'
import Logo from '../components/Logo'
import type { User } from '../types'

interface LoginValues { account: string; password: string; remember?: boolean }
interface RegisterValues { account: string; verification_code: string; password: string; confirm_password: string }

function errorMessage(reason: unknown, fallback: string) {
  return axios.isAxiosError(reason) ? reason.response?.data?.detail ?? fallback : fallback
}

export default function LoginPage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [account, setAccount] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    if (countdown <= 0) return
    const timer = window.setInterval(() => setCountdown(value => Math.max(0, value - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [countdown])

  async function login(values: LoginValues) {
    setLoading(true); setError(''); setNotice('')
    try {
      const { data } = await api.post<{ access_token: string; user: User }>('/auth/login', values)
      setSession(data.access_token, data.user)
      if (data.user.role === 'CUSTOMER') navigate('/home')
      else window.location.href = `${import.meta.env.VITE_ADMIN_URL ?? 'http://localhost:5174'}/login`
    } catch (reason) {
      setError(errorMessage(reason, '登录失败，请稍后重试'))
    } finally { setLoading(false) }
  }

  async function sendCode() {
    if (!account.trim()) { setError('请先输入手机号或邮箱'); return }
    setSending(true); setError(''); setNotice('')
    try {
      const { data } = await api.post<{ message: string; retry_after: number; debug_code?: string }>('/auth/verification-codes', { account })
      setCountdown(data.retry_after)
      setNotice(data.debug_code ? `验证码已发送（开发模式验证码：${data.debug_code}）` : data.message)
    } catch (reason) {
      setError(errorMessage(reason, '验证码发送失败，请稍后重试'))
    } finally { setSending(false) }
  }

  async function register(values: RegisterValues) {
    setLoading(true); setError(''); setNotice('')
    try {
      const { data } = await api.post<{ access_token: string; user: User }>('/auth/register', {
        account: values.account, verification_code: values.verification_code, password: values.password,
      })
      setSession(data.access_token, data.user)
      navigate('/home')
    } catch (reason) {
      setError(errorMessage(reason, '注册失败，请稍后重试'))
    } finally { setLoading(false) }
  }

  const loginForm = <Form layout="vertical" size="large" initialValues={{ account: 'demo@eprflow.com', password: 'Demo123!', remember: true }} onFinish={login}>
    <Form.Item name="account" label="手机 / 邮箱" rules={[{ required: true, message: '请输入手机或邮箱' }]}><Input prefix={<MailOutlined />} placeholder="请输入手机 / 邮箱" /></Form.Item>
    <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}><Input.Password prefix={<LockOutlined />} placeholder="请输入密码" /></Form.Item>
    <div className="login-options"><Form.Item name="remember" valuePropName="checked" noStyle><Checkbox>记住我</Checkbox></Form.Item><span>忘记密码？</span></div>
    <Button htmlType="submit" type="primary" block loading={loading}>登录</Button>
  </Form>

  const registerForm = <Form layout="vertical" size="large" onFinish={register}>
    <Form.Item name="account" label="手机号 / 邮箱" rules={[{ required: true, message: '请输入手机号或邮箱' }]}><Input prefix={<MailOutlined />} placeholder="手机号或邮箱" onChange={event => setAccount(event.target.value)} /></Form.Item>
    <Form.Item label="验证码" required>
      <div className="verification-row">
        <Form.Item name="verification_code" noStyle rules={[{ required: true, message: '请输入验证码' }, { pattern: /^\d{6}$/, message: '请输入 6 位数字验证码' }]}><Input maxLength={6} inputMode="numeric" placeholder="6 位验证码" /></Form.Item>
        <Button onClick={() => void sendCode()} loading={sending} disabled={countdown > 0}>{countdown > 0 ? `${countdown} 秒后重发` : '获取验证码'}</Button>
      </div>
    </Form.Item>
    <Form.Item name="password" label="设置密码" rules={[{ required: true, message: '请设置密码' }, { min: 8, message: '密码至少 8 位' }]} hasFeedback><Input.Password prefix={<LockOutlined />} placeholder="至少 8 位" /></Form.Item>
    <Form.Item name="confirm_password" label="确认密码" dependencies={['password']} hasFeedback rules={[{ required: true, message: '请再次输入密码' }, ({ getFieldValue }) => ({ validator(_, value) { return !value || getFieldValue('password') === value ? Promise.resolve() : Promise.reject(new Error('两次输入的密码不一致')) } })]}><Input.Password prefix={<LockOutlined />} placeholder="再次输入密码" /></Form.Item>
    <Button htmlType="submit" type="primary" block loading={loading}>注册并登录</Button>
  </Form>

  return <main className="login-page">
    <section className="login-brand"><Logo light /><div className="brand-copy"><span className="brand-kicker">EPR COMPLIANCE PORTAL</span><h1>全球 EPR 合规<br />从这里开始</h1><p>专业 · 高效 · 合规 · 省心</p></div><div className="globe"><div /><div /><div /></div></section>
    <section className="login-panel"><div className="login-card">
      <Typography.Title level={2}>{mode === 'login' ? '欢迎回来' : '创建客户账号'}</Typography.Title>
      <Typography.Paragraph type="secondary">{mode === 'login' ? '客户递单与运营审核统一登录入口' : '使用手机号或邮箱验证码完成注册'}</Typography.Paragraph>
      <Tabs centered activeKey={mode} onChange={value => { setMode(value); setError(''); setNotice('') }} items={[{ key: 'login', label: '登录' }, { key: 'register', label: '新用户注册' }]} />
      {error && <Alert className="login-alert" type="error" message={error} showIcon />}
      {notice && <Alert className="login-alert" type="success" message={notice} showIcon />}
      {mode === 'login' ? loginForm : registerForm}
      {mode === 'login' && <div className="login-demo-accounts"><span>客户演示：demo@eprflow.com</span><span>管理员：admin@eprflow.com</span><span>员工：staff@eprflow.com</span></div>}
      <div className="login-security"><SafetyCertificateOutlined /> 验证码与密码加密处理，保障账号安全</div>
    </div></section>
  </main>
}

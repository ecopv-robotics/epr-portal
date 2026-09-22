import { LockOutlined, MailOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import { Alert, Button, Checkbox, Form, Input, Tabs, Typography } from 'antd'
import axios from 'axios'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import { setSession } from '../auth'
import Logo from '../components/Logo'
import type { User } from '../types'

interface LoginValues { account: string; password: string; remember?: boolean }

export default function LoginPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(values: LoginValues) {
    setLoading(true); setError('')
    try {
      const { data } = await api.post<{ access_token: string; user: User }>('/auth/login', values)
      setSession(data.access_token, data.user)
      if (data.user.role === 'CUSTOMER') navigate('/applications')
      else window.location.href = `${import.meta.env.VITE_ADMIN_URL ?? 'http://localhost:5174'}/login`
    } catch (reason) {
      setError(axios.isAxiosError(reason) ? reason.response?.data?.detail ?? '登录失败，请稍后重试' : '登录失败，请稍后重试')
    } finally { setLoading(false) }
  }

  return (
    <main className="login-page">
      <section className="login-brand">
        <Logo light />
        <div className="brand-copy">
          <span className="brand-kicker">EPR COMPLIANCE PORTAL</span>
          <h1>全球 EPR 合规<br />从这里开始</h1>
          <p>专业 · 高效 · 合规 · 省心</p>
        </div>
        <div className="globe"><div /><div /><div /></div>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <Typography.Title level={2}>欢迎回来</Typography.Title>
          <Typography.Paragraph type="secondary">客户递单与运营审核统一登录入口</Typography.Paragraph>
          <Tabs centered defaultActiveKey="account" items={[{ key: 'account', label: '账号登录' }, { key: 'email', label: '邮箱登录', disabled: true }]} />
          {error && <Alert className="login-alert" type="error" message={error} showIcon />}
          <Form layout="vertical" size="large" initialValues={{ account: 'demo@eprflow.com', password: 'Demo123!', remember: true }} onFinish={submit}>
            <Form.Item name="account" label="手机 / 邮箱" rules={[{ required: true, message: '请输入手机或邮箱' }]}>
              <Input prefix={<MailOutlined />} placeholder="请输入手机 / 邮箱" />
            </Form.Item>
            <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" />
            </Form.Item>
            <div className="login-options"><Form.Item name="remember" valuePropName="checked" noStyle><Checkbox>记住我</Checkbox></Form.Item><span>忘记密码？</span></div>
            <Button htmlType="submit" type="primary" block loading={loading}>登录</Button>
          </Form>
          <div className="login-demo-accounts"><span>客户演示：demo@eprflow.com</span><span>管理员：admin@eprflow.com</span><span>员工：staff@eprflow.com</span></div>
          <div className="login-security"><SafetyCertificateOutlined /> 数据加密传输，保障企业资料安全</div>
        </div>
      </section>
    </main>
  )
}

import { ArrowLeftOutlined, CheckCircleFilled, FileTextOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Col, Empty, Row, Select, Space, Steps, Typography, message } from 'antd'
import axios from 'axios'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import api from '../api'
import type { Application, Company, CountryOption } from '../types'

export default function ApplicationCreatePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const companyId = searchParams.get('companyId')
  const [company, setCompany] = useState<Company>()
  const [catalog, setCatalog] = useState<CountryOption[]>([])
  const [country, setCountry] = useState('')
  const [service, setService] = useState('')
  const [saving, setSaving] = useState(false)
  const selectedCountry = useMemo(() => catalog.find((item) => item.value === country), [catalog, country])

  useEffect(() => { api.get<CountryOption[]>('/catalog/countries').then(({ data }) => setCatalog(data)).catch(() => message.error('国家服务目录加载失败')) }, [])
  useEffect(() => { if (companyId) api.get<Company>(`/companies/${companyId}`).then(({ data }) => setCompany(data)).catch(() => message.error('企业资料加载失败')) }, [companyId])
  async function create() {
    setSaving(true)
    try {
      const { data } = await api.post<Application>('/applications', { country, service_type: service, company_id: companyId ? Number(companyId) : undefined })
      message.success(`递单 ${data.application_no} 创建成功`)
      navigate(`/application/${data.id}/form`)
    } catch (reason) { message.error(axios.isAxiosError(reason) ? reason.response?.data?.detail ?? '创建失败' : '创建失败') }
    finally { setSaving(false) }
  }

  return <div className="page-container create-page">
    <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/applications')}>返回我的递单</Button>
    <Card className="create-card">
      <div className="create-title"><Typography.Title level={2}>新建递单</Typography.Title><Typography.Text type="secondary">选择国家和 EPR 服务项目后开始填写资料</Typography.Text></div>
      {company && <Alert type="success" showIcon message={`已选择企业：${company.company_name}`} description="企业及法人资料将在递单中自动带入，您仍可在提交前核对。" />}
      <Steps current={service ? 1 : 0} items={[{ title: '选择国家和服务' }, { title: '填写资料' }, { title: '提交完成' }]} />
      <div className="create-form">
        <Typography.Title level={4}>选择注册国家</Typography.Title>
        <Select showSearch optionFilterProp="label" size="large" placeholder="搜索或选择欧洲国家" value={country || undefined} onChange={(v) => { setCountry(v); setService('') }} options={catalog.map(({ value, label }) => ({ value, label }))} />
        <Typography.Title level={4}>选择 EPR 服务类型</Typography.Title>
        {!country ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请先选择国家" /> : <Row gutter={[16, 16]}>{selectedCountry?.services.map((item) => <Col xs={24} sm={12} lg={6} key={item.value}><button className={`service-card ${service === item.value ? 'selected' : ''}`} onClick={() => setService(item.value)}><FileTextOutlined /><strong>{item.label}</strong><span>{item.description}</span>{service === item.value && <CheckCircleFilled className="selected-icon" />}</button></Col>)}</Row>}
        {service && <Alert type="info" showIcon message={`${selectedCountry?.label} · ${service}`} description="下一步将根据国家与服务模板加载对应资料字段和材料要求。" />}
      </div>
      <div className="create-actions"><Space><Button onClick={() => navigate('/applications')}>取消</Button><Button type="primary" size="large" disabled={!country || !service} loading={saving} onClick={create}>创建并下一步</Button></Space></div>
    </Card>
  </div>
}

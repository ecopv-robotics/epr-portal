import { EyeOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Card, Empty, Input, Segmented, Table, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import axios from 'axios'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import type { Application, ApplicationList, ApplicationStatus } from '../types'

const statusMeta: Record<ApplicationStatus, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' }, SUBMITTED: { label: '待审核', color: 'blue' },
  REVIEWING: { label: '审核中', color: 'processing' }, NEED_FIX: { label: '待补资料', color: 'warning' }, COMPLETED: { label: '已完成', color: 'success' },
  REGISTERING: { label: '注册中', color: 'cyan' },
}

export default function ApplicationsPage({ title = '我的订单', description = '管理和跟踪您的 EPR 注册申请' }: { title?: string; description?: string }) {
  const navigate = useNavigate()
  const [data, setData] = useState<ApplicationList>({ items: [], total: 0, page: 1, page_size: 10 })
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'ALL' | ApplicationStatus>('ALL')

  useEffect(() => { api.get<ApplicationList>('/applications').then(({ data }) => setData(data)).catch((e) => message.error(axios.isAxiosError(e) ? e.response?.data?.detail ?? '加载失败' : '加载失败')).finally(() => setLoading(false)) }, [])
  const filtered = data.items.filter((item) => (statusFilter === 'ALL' || item.status === statusFilter) && [item.application_no, item.company_name, item.registration_number, item.country, item.service_type].some((v) => v?.toLowerCase().includes(query.toLowerCase())))
  const count = (status: ApplicationStatus) => data.items.filter((item) => item.status === status).length
  const columns: ColumnsType<Application> = [
    { title: '申请编号', dataIndex: 'application_no', render: (v) => <strong className="application-no">{v}</strong> },
    { title: '公司', dataIndex: 'company_name', render: (v) => v || <span className="muted">待填写</span> },
    { title: '注册号', dataIndex: 'registration_number', render: (v) => v || <span className="muted">--</span> },
    { title: '国家', dataIndex: 'country' }, { title: '服务', dataIndex: 'service_type' },
    { title: '服务进度', dataIndex: 'status', render: (v: ApplicationStatus) => <Tag color={statusMeta[v].color}>{statusMeta[v].label}</Tag> },
    { title: '提交时间', dataIndex: 'submitted_time', render: (v) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '—' },
    { title: '操作', key: 'action', render: (_, record) => <Button type="link" icon={<EyeOutlined />} onClick={() => navigate(`/application/${record.id}/form`)}>{record.status === 'DRAFT' || record.status === 'NEED_FIX' ? '继续填写' : '查看'}</Button> },
  ]

  return <div className="page-container">
    <div className="page-heading"><div><Typography.Title level={2}>{title}</Typography.Title><Typography.Text type="secondary">{description}</Typography.Text></div><Button type="primary" size="large" icon={<PlusOutlined />} onClick={() => navigate('/services')}>购买服务</Button></div>
    <Card className="data-card">
      <div className="table-toolbar"><Segmented value={statusFilter} onChange={(value) => setStatusFilter(value as 'ALL' | ApplicationStatus)} options={[{ label: `全部 (${data.total})`, value: 'ALL' }, { label: `草稿 (${count('DRAFT')})`, value: 'DRAFT' }, { label: `待审核 (${count('SUBMITTED')})`, value: 'SUBMITTED' }, { label: `审核中 (${count('REVIEWING')})`, value: 'REVIEWING' }, { label: `待补资料 (${count('NEED_FIX')})`, value: 'NEED_FIX' }, { label: `注册中 (${count('REGISTERING')})`, value: 'REGISTERING' }, { label: `已完成 (${count('COMPLETED')})`, value: 'COMPLETED' }]} /><Input allowClear prefix={<SearchOutlined />} placeholder="申请编号 / 公司 / 注册号 / 国家 / 服务" value={query} onChange={(e) => setQuery(e.target.value)} /></div>
      <Table rowKey="id" columns={columns} dataSource={filtered} loading={loading} locale={{ emptyText: <Empty description="暂无递单，创建第一份 EPR 申请吧" /> }} pagination={{ total: filtered.length, pageSize: 10, showTotal: (total) => `共 ${total} 条` }} />
    </Card>
  </div>
}

import { DownloadOutlined, EyeOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Empty, Input, Select, Space, Table, Tabs, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import type { Application, ApplicationList, ApplicationStatus } from '../types'

const meta: Record<ApplicationStatus, { label: string; color: string }> = {
  DRAFT: { label: '待提交资料', color: 'orange' }, SUBMITTED: { label: '资料审核中', color: 'blue' }, REVIEWING: { label: '资料审核中', color: 'blue' }, NEED_FIX: { label: '待提交资料', color: 'orange' }, REGISTERING: { label: '业务办理中', color: 'processing' }, COMPLETED: { label: '已完成', color: 'success' },
}

export default function EprRegistrationsPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('ALL')
  const [query, setQuery] = useState('')
  const [country, setCountry] = useState<string>()
  useEffect(() => { api.get<ApplicationList>('/applications').then(({ data }) => setData(data.items)).catch(() => setData([])).finally(() => setLoading(false)) }, [])
  const filtered = useMemo(() => data.filter(item => (status === 'ALL' || item.status === status) && (!country || item.country === country) && [item.company_name, item.registration_number, item.application_no, item.service_type].some(v => v?.toLowerCase().includes(query.toLowerCase()))), [data, status, query, country])
  const count = (statuses: ApplicationStatus[]) => data.filter(item => statuses.includes(item.status)).length
  const columns: ColumnsType<Application> = [
    { title: '服务号', dataIndex: 'application_no', render: v => <strong className="application-no">{v}</strong> },
    { title: '公司名称', dataIndex: 'company_name', render: v => v || '--' }, { title: 'EPR注册号', dataIndex: 'registration_number', render: v => v || '--' },
    { title: '国家', dataIndex: 'country' }, { title: '服务名称', dataIndex: 'service_type' },
    { title: '服务创建时间', dataIndex: 'created_time', render: v => dayjs(v).format('YYYY-MM-DD HH:mm') }, { title: '服务到期时间', dataIndex: 'service_expiry_date', render: v => v ? dayjs(v).format('YYYY-MM-DD') : '--' },
    { title: '服务进度', dataIndex: 'status', render: (v: ApplicationStatus) => <Tag color={meta[v].color}>{meta[v].label}</Tag> },
    { title: '操作', fixed: 'right', width: 170, render: (_, row) => <Space size={0}><Button type="link" icon={<EyeOutlined />} onClick={() => navigate(`/application/${row.id}/form`)}>{['DRAFT', 'NEED_FIX'].includes(row.status) ? '提交资料' : '查看详情'}</Button>{row.status === 'COMPLETED' && row.certificate_file && <Button type="link" icon={<DownloadOutlined />} href={row.certificate_file}>证书</Button>}</Space> },
  ]
  return <div className="page-container registrations-page">
    <div className="page-heading"><div><Typography.Title level={2}>EPR注册号</Typography.Title><Typography.Text type="secondary">统一查看注册进度、注册号信息与合规证书</Typography.Text></div></div>
    <Card className="registration-filter-card"><Alert type="info" showIcon message="列表展示 EPR 注册、转代理及增值服务，可在线补充资料、查询进度并下载注册证书。" />
      <Tabs activeKey={status} onChange={setStatus} items={[{ key: 'ALL', label: `全部 (${data.length})` }, { key: 'NEED_FIX', label: `待提交资料 (${count(['DRAFT', 'NEED_FIX'])})` }, { key: 'REVIEWING', label: `资料审核中 (${count(['SUBMITTED', 'REVIEWING'])})` }, { key: 'REGISTERING', label: `业务办理中 (${count(['REGISTERING'])})` }, { key: 'COMPLETED', label: `已完成 (${count(['COMPLETED'])})` }]} />
      <div className="registration-search"><Input allowClear prefix={<SearchOutlined />} placeholder="公司名称 / 注册号 / 服务号" value={query} onChange={e => setQuery(e.target.value)} /><Select allowClear placeholder="请选择国家" value={country} onChange={setCountry} options={[...new Set(data.map(item => item.country))].map(value => ({ value, label: value }))} /><Select allowClear placeholder="请选择 EPR 业务类型" options={[{ value: 'WEEE', label: 'WEEE' }, { value: 'BATTERY', label: '电池法' }, { value: 'PACKAGING', label: '包装法' }]} /><Button type="primary" icon={<SearchOutlined />}>查询</Button><Button onClick={() => { setQuery(''); setCountry(undefined); setStatus('ALL') }}>重置</Button></div>
    </Card>
    <Card className="data-card" title="注册服务列表" extra={<Typography.Text type="secondary">共 {filtered.length} 条</Typography.Text>}><Table rowKey="id" loading={loading} columns={columns} dataSource={filtered} scroll={{ x: 1300 }} locale={{ emptyText: <Empty description="暂无 EPR 注册服务" /> }} pagination={{ pageSize: 10, showTotal: total => `共 ${total} 条` }} /></Card>
  </div>
}

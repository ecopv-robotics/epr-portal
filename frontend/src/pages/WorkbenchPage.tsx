import { FileDoneOutlined, MessageOutlined, PlusCircleOutlined, ShoppingOutlined } from '@ant-design/icons'
import { Button, Card, Empty, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import type { PortalDashboard, PortalTodo } from '../types'

type Todo = { key: string; type: '资料' | '续费' | '回签'; company: string; country: string; service: string; no: string; created: string; applicationId?: number; orderId?:number }

export default function WorkbenchPage() {
  const navigate = useNavigate()
  const [dashboard, setDashboard] = useState<PortalDashboard>({ pending_materials: 0, pending_renewals: 0, pending_countersigns:0, unread_messages: 0, todos: [] })
  const [loading, setLoading] = useState(true)
  useEffect(() => { api.get<PortalDashboard>('/portal/dashboard').then(({ data }) => setDashboard(data)).finally(() => setLoading(false)) }, [])
  const rows: Todo[] = dashboard.todos.map((item: PortalTodo) => ({ key: item.id, type: item.type === 'RENEWAL' ? '续费' : item.type==='COUNTERSIGN'?'回签':'资料', company: item.company, country: item.country, service: item.service, no: item.service_no, created: item.created_time, applicationId: item.application_id, orderId:item.order_id }))
  const columns: ColumnsType<Todo> = [
    { title: '待办事项', dataIndex: 'type', render: v => <Tag color={v === '资料' ? 'blue' : v==='回签'?'gold':'orange'}>{v === '资料' ? '待提交资料' : v==='回签'?'待二次回签':'待续费'}</Tag> },
    { title: '申请主体', dataIndex: 'company' }, { title: '国家/地区', dataIndex: 'country' }, { title: '服务名称', dataIndex: 'service' },
    { title: '服务号', dataIndex: 'no' }, { title: '创建时间', dataIndex: 'created', render: v => String(v).slice(0, 16).replace('T', ' ') },
    { title: '操作', render: (_, row) => <Button type="link" onClick={() => row.type === '续费' ? navigate('/renewals') : row.type==='回签'&&row.orderId?navigate(`/account/orders/${row.orderId}`):row.applicationId ? navigate(`/application/${row.applicationId}/form`) : navigate('/epr/declarations')}>{row.type === '续费' ? '立即续费' : row.type==='回签'?'上传回签文件':'提交资料'}</Button> },
  ]
  return <div className="page-container dashboard-page">
    <div className="page-heading"><div><Typography.Title level={2}>工作台</Typography.Title><Typography.Text type="secondary">快捷办理服务，集中处理订单、消息与待办事项</Typography.Text></div></div>
    <Card className="dashboard-card quick-entry-card" title="快捷入口">
      <div className="quick-entry-grid">
        <button onClick={() => navigate('/services')}><span><strong>购买服务</strong><small>选购新的 EPR 合规服务</small></span><i className="quick-icon orange"><ShoppingOutlined /></i></button>
        <button onClick={() => navigate('/account/orders')}><span><strong>我的订单</strong><small>查看付款状态与购买记录</small></span><i className="quick-icon green"><FileDoneOutlined /></i></button>
        <button onClick={() => navigate('/messages')}><span><strong>我的消息</strong><small>查看服务通知与平台消息</small></span><i className="quick-icon purple"><MessageOutlined /></i>{dashboard.unread_messages > 0 && <b>{dashboard.unread_messages}</b>}</button>
      </div>
    </Card>
    <Card className="dashboard-card todo-card" title="待办事项">
      <div className="todo-summary">
        <div className="active"><PlusCircleOutlined /><span>待提交资料<strong>{dashboard.pending_materials}</strong></span></div>
        <div><FileDoneOutlined /><span>待二次回签<strong>{dashboard.pending_countersigns}</strong></span></div>
        <div><ShoppingOutlined /><span>待续费<strong>{dashboard.pending_renewals}</strong></span></div>
      </div>
      <Table rowKey="key" loading={loading} columns={columns} dataSource={rows} locale={{ emptyText: <Empty description="暂无待办事项" /> }} pagination={false} />
    </Card>
  </div>
}

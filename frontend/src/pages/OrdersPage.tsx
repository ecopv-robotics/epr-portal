import { EyeOutlined, FileTextOutlined, SearchOutlined, ShoppingOutlined } from '@ant-design/icons'
import { Button, Card, Empty, Input, Modal, Space, Table, Tabs, Tag, Typography, message } from 'antd'
import type { Key } from 'react'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import type { PurchaseOrder, PurchaseOrderStatus } from '../types'

type FilterStatus = 'ALL' | PurchaseOrderStatus
const paymentMeta: Record<PurchaseOrderStatus, { label: string; color: string }> = {
  PENDING: { label: '待付款', color: 'warning' }, PAYMENT_CONFIRMING: { label: '付款待确认', color: 'processing' },
  PAID: { label: '已付款', color: 'success' }, CANCELLED: { label: '已取消', color: 'default' }, PAYMENT_FAILED: { label: '支付失败', color: 'error' },
  PARTIALLY_REFUNDED: { label: '部分退款', color: 'orange' }, REFUNDED: { label: '全部退款', color: 'default' },
}
const progressLabel: Record<string, string> = { DRAFT: '待提交资料', SUBMITTED: '待审核', REVIEWING: '资料审核中', NEED_FIX: '驳回修改', REGISTERING: '业务办理中', COMPLETED: '已下证 · 待确认交付' }

export default function OrdersPage() {
  const navigate = useNavigate()
  const [orders, setOrders] = useState<PurchaseOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState<FilterStatus>('ALL')
  const [query, setQuery] = useState('')
  const [selectedKeys, setSelectedKeys] = useState<Key[]>([])

  function load() { return api.get<PurchaseOrder[]>('/portal/orders').then(({ data }) => setOrders(data)) }
  useEffect(() => { load().finally(() => setLoading(false)) }, [])
  function cancel(order: PurchaseOrder) { Modal.confirm({ title: '确认取消订单？', content: '取消后该订单不可继续支付。', okText: '确认取消', okButtonProps: { danger: true }, onOk: async () => { await api.post(`/portal/orders/${order.id}/cancel`); message.success('订单已取消'); await load() } }) }
  const filtered = useMemo(() => orders.filter(order => (status === 'ALL' || order.status === status) && [order.order_no, order.service.title, order.service.country, order.service.product_type].some(value => value.toLowerCase().includes(query.toLowerCase()))), [orders, status, query])
  const count = (target: FilterStatus) => target === 'ALL' ? orders.length : orders.filter(order => order.status === target).length

  const columns: ColumnsType<PurchaseOrder> = [
    { title: '下单时间', dataIndex: 'created_time', width: 170, render: value => dayjs(value).format('YYYY-MM-DD HH:mm') },
    { title: '订单号', dataIndex: 'order_no', width: 190, render: value => <strong className="application-no">{value}</strong> },
    { title: '服务名称', width: 280, render: (_, order) => <div className="order-list-service"><span style={{ background: order.service.color }}>{order.service.country_code}</span><div><strong>{order.service.title}</strong><small>{order.service.description}</small></div></div> },
    { title: '规格', width: 220, render: (_, order) => <span>{order.service.country} · {order.service.product_type}<br />{order.service_year}</span> },
    { title: '数量', dataIndex: 'quantity', width: 75, align: 'center' },
    { title: '订单金额', dataIndex: 'standard_amount', width: 120, render: value => <span className="order-list-standard-amount">¥{value.toLocaleString()}</span> },
    { title: '优惠金额', dataIndex: 'discount_amount', width: 115, render: value => <span className={value > 0 ? 'order-list-discount-amount' : 'order-list-zero-discount'}>{value > 0 ? `-¥${value.toLocaleString()}` : '¥0'}</span> },
    { title: '应付/实付', width: 125, render: (_, order) => {
      const isPaid = ['PAID', 'PARTIALLY_REFUNDED', 'REFUNDED'].includes(order.status)
      const amount = order.actual_paid_amount ?? order.total_amount
      return <div className="order-list-final-amount"><strong>¥{amount.toLocaleString()}</strong><small>{isPaid ? '实付' : '应付'}</small></div>
    } },
    { title: '付款状态', dataIndex: 'status', width: 120, render: (value: PurchaseOrderStatus) => <Tag color={paymentMeta[value].color}>{paymentMeta[value].label}</Tag> },
    { title: '服务进度', dataIndex: 'service_progress', width: 120, render: value => value ? <Tag color={value === 'COMPLETED' ? 'success' : 'blue'}>{progressLabel[value]}</Tag> : '—' },
    { title: '操作', fixed: 'right', width: 260, render: (_, order) => <Space size={0}>
      {['PENDING', 'PAYMENT_FAILED'].includes(order.status) && <Button type="primary" size="small" onClick={() => navigate(`/orders/${order.id}/payment`)}>立即付款</Button>}
      <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => navigate(`/account/orders/${order.id}`)}>订单详情</Button>
      {['PENDING', 'PAYMENT_FAILED', 'PAYMENT_CONFIRMING'].includes(order.status) && <Button danger type="link" size="small" onClick={() => cancel(order)}>取消订单</Button>}
      {order.status === 'PAID' && <Button type="link" size="small" icon={<FileTextOutlined />} onClick={() => navigate(`/account/orders/${order.id}`)}>服务实例</Button>}
    </Space> },
  ]

  return <div className="page-container orders-page">
    <div className="page-heading"><div><Typography.Title level={2}>我的订单</Typography.Title><Typography.Text type="secondary">查看服务购买记录和付款状态，付款成功后即可提交 EPR 资料</Typography.Text></div><Button type="primary" icon={<ShoppingOutlined />} onClick={() => navigate('/services')}>购买服务</Button></div>
    <Card className="order-filter-card"><Tabs activeKey={status} onChange={value => setStatus(value as FilterStatus)} items={[{ key: 'ALL', label: `全部 (${count('ALL')})` }, ...Object.entries(paymentMeta).map(([key, item]) => ({ key, label: `${item.label} (${count(key as PurchaseOrderStatus)})` }))]} /><Input allowClear prefix={<SearchOutlined />} placeholder="搜索订单号、服务名称或国家" value={query} onChange={event => setQuery(event.target.value)} /></Card>
    <Card className="data-card order-list-card" title={selectedKeys.length ? `已选择 ${selectedKeys.length} 个订单` : undefined} extra={selectedKeys.length > 1 ? <Button type="primary" onClick={() => navigate(`/orders/${selectedKeys[0]}/payment?order_ids=${selectedKeys.join(',')}`)}>合并付款</Button> : undefined}><Table rowKey="id" loading={loading} columns={columns} dataSource={filtered} scroll={{ x: 1700 }} locale={{ emptyText: <Empty description="暂无订单" /> }} pagination={{ pageSize: 10, showTotal: total => `共 ${total} 条` }} rowSelection={{selectedRowKeys:selectedKeys,onChange:setSelectedKeys,getCheckboxProps:order=>({disabled:!['PENDING','PAYMENT_FAILED'].includes(order.status)})}} /></Card>
  </div>
}

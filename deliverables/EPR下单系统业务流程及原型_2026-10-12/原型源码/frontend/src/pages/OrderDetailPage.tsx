import { ArrowLeftOutlined, DownloadOutlined, EditOutlined, EyeOutlined } from '@ant-design/icons'
import { Button, Card, Descriptions, Empty, Result, Skeleton, Space, Table, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../api'
import type { ApplicationStatus, PurchaseOrder, ServiceInstance } from '../types'

const paymentLabels: Record<PurchaseOrder['status'], { label: string; color: string }> = {
  PENDING: { label: '待付款', color: 'warning' }, PAYMENT_CONFIRMING: { label: '付款待确认', color: 'processing' },
  PAID: { label: '已付款', color: 'success' }, CANCELLED: { label: '已取消', color: 'default' },
  PAYMENT_FAILED: { label: '支付失败', color: 'error' }, PARTIALLY_REFUNDED: { label: '部分退款', color: 'orange' }, REFUNDED: { label: '全部退款', color: 'default' },
}
const progressLabels: Record<ApplicationStatus, { label: string; color: string }> = {
  DRAFT: { label: '待提交资料', color: 'orange' }, SUBMITTED: { label: '待审核', color: 'blue' },
  REVIEWING: { label: '资料审核中', color: 'processing' }, NEED_FIX: { label: '待补资料', color: 'warning' },
  REGISTERING: { label: '业务办理中', color: 'cyan' }, COMPLETED: { label: '已交付', color: 'success' },
}

export default function OrderDetailPage() {
  const { id } = useParams(); const navigate = useNavigate()
  const [order, setOrder] = useState<PurchaseOrder>(); const [loading, setLoading] = useState(true)
  useEffect(() => { api.get<PurchaseOrder>(`/portal/orders/${id}`).then(({ data }) => setOrder(data)).catch(() => message.error('订单加载失败')).finally(() => setLoading(false)) }, [id])
  if (loading) return <div className="page-container"><Card><Skeleton active /></Card></div>
  if (!order) return <div className="page-container"><Result status="404" title="订单不存在" /></div>
  const columns: ColumnsType<ServiceInstance> = [
    { title: '序号', dataIndex: 'instance_index', width: 72, render: value => `#${value}` },
    { title: '服务实例号', dataIndex: 'application_no', render: value => <strong className="application-no">{value}</strong> },
    { title: '企业名称', dataIndex: 'company_name', render: value => value || '待填写' },
    { title: '服务进度', dataIndex: 'status', render: (value: ApplicationStatus) => <Tag color={progressLabels[value].color}>{progressLabels[value].label}</Tag> },
    { title: 'EPR 注册号', dataIndex: 'registration_number', render: value => value || '—' },
    { title: '操作', width: 230, render: (_, instance) => <Space size={0}>
      <Button type="link" icon={['DRAFT', 'NEED_FIX'].includes(instance.status) ? <EditOutlined /> : <EyeOutlined />} onClick={() => navigate(`/application/${instance.id}/form`)}>{['DRAFT', 'NEED_FIX'].includes(instance.status) ? '填写/补充资料' : '查看资料'}</Button>
      {instance.status === 'COMPLETED' && instance.certificate_file && <Button type="link" icon={<DownloadOutlined />} href={instance.certificate_file}>证书</Button>}
    </Space> },
  ]
  return <div className="page-container">
    <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/account/orders')}>返回我的订单</Button>
    <div className="page-heading"><div><Typography.Title level={2}>订单详情</Typography.Title><Typography.Text type="secondary">订单与服务实例分开管理，每个实例独立填写资料、审核和交付。</Typography.Text></div><Tag color={paymentLabels[order.status].color}>{paymentLabels[order.status].label}</Tag></div>
    <Card className="data-card"><Descriptions column={3} items={[
      { key: 'no', label: '订单号', children: order.order_no }, { key: 'service', label: '服务', children: order.service.title },
      { key: 'spec', label: '购买属性', children: `${order.service.country} / ${order.service.product_type} / ${order.service_year}` },
      { key: 'quantity', label: '数量', children: order.quantity }, { key: 'standard', label: '标准金额', children: `¥${order.standard_amount.toLocaleString()}` },
      { key: 'discount', label: '优惠抵扣', children: `-¥${order.discount_amount.toLocaleString()}` }, { key: 'amount', label: order.status === 'PAID' ? '实付金额' : '应付金额', children: `¥${(order.actual_paid_amount ?? order.total_amount).toLocaleString()}` },
      { key: 'contract', label: '合同', children: order.contract_file ? <Button type="link" href={order.contract_file}>查看 {order.contract_version || ''}</Button> : '销售可在付款前或付款后上传' },
      { key: 'time', label: '下单时间', children: dayjs(order.created_time).format('YYYY-MM-DD HH:mm') },
    ]} /></Card>
    <Card className="data-card" title={`服务实例（${order.service_instances.length}/${order.quantity}）`} extra={order.status === 'PAID' ? '付款完成后按购买数量生成' : '付款确认后生成'}>
      <Table rowKey="id" columns={columns} dataSource={order.service_instances} pagination={false} locale={{ emptyText: <Empty description={order.status === 'PAYMENT_CONFIRMING' ? '付款确认后将生成服务实例' : '暂无服务实例'} /> }} />
    </Card>
  </div>
}

import { ArrowLeftOutlined, CheckCircleFilled, FileTextOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Descriptions, Result, Skeleton, Space, Tag, Typography, message } from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../api'
import type { PurchaseOrder } from '../types'

export default function OrderConfirmationPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [order, setOrder] = useState<PurchaseOrder>()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<PurchaseOrder>(`/portal/orders/${id}`).then(({ data }) => setOrder(data)).catch(() => message.error('订单加载失败')).finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="page-container"><Card className="data-card"><Skeleton active /></Card></div>
  if (!order) return <div className="page-container"><Result status="404" title="订单不存在" extra={<Button type="primary" onClick={() => navigate('/services')}>返回购买服务</Button>} /></div>

  if (order.status === 'PAID') return <div className="page-container order-confirm-page"><Card className="data-card">
    <Result status="success" title="付款成功" subTitle={`订单 ${order.order_no} 已支付，EPR 服务已生成并进入待提交资料状态。`} extra={[
      <Button type="primary" key="registration" onClick={() => navigate('/epr/registrations')}>查看 EPR 注册号</Button>,
      <Button key="material" onClick={() => navigate(`/account/orders/${order.id}`)}>查看服务实例</Button>,
    ]} />
  </Card></div>

  return <div className="page-container order-confirm-page">
    <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/services')}>返回购买服务</Button>
    <div className="page-heading"><div><Typography.Title level={2}>订单确认</Typography.Title><Typography.Text type="secondary">请核对服务内容与商品属性，确认订单后选择付款方式</Typography.Text></div><Tag color="orange">待确认</Tag></div>
    <Card className="data-card order-info-card" title={<Space><FileTextOutlined />订单信息</Space>} extra={<Typography.Text type="secondary">订单号：{order.order_no}</Typography.Text>}>
      <div className="order-service-row">
        <span className="order-country-code" style={{ background: order.service.color }}>{order.service.country_code}</span>
        <div className="order-service-name"><strong>{order.service.title}</strong><span>{order.service.description}</span></div>
        <Descriptions size="small" column={1} colon={false} items={[
          { key: 'spec', label: '商品规格', children: `${order.service.country}，${order.service.product_type}，${order.service_year}` },
          { key: 'info', label: '服务资料', children: '付款后按每个服务实例分别补充' },
        ]} />
        <div className="order-unit-price"><span>单价</span><strong>¥{order.unit_price.toLocaleString()}</strong></div>
        <div className="order-quantity"><span>数量</span><strong>× {order.quantity}</strong></div>
        <div className="order-subtotal"><span>{order.discount_amount ? '优惠后金额' : '小计'}</span><strong>¥{order.total_amount.toLocaleString()}</strong></div>
      </div>
    </Card>
    <Card className="data-card order-protection-card">
      <div><SafetyCertificateOutlined /><span><strong>服务保障</strong><small>付款成功后立即创建 EPR 服务，可在线提交资料并追踪办理进度。</small></span></div>
      <div><CheckCircleFilled /><span><strong>商品优惠</strong><small>{order.discount_amount ? `打包优惠已抵扣 ¥${order.discount_amount.toLocaleString()}${order.discount_reason ? `（${order.discount_reason}）` : ''}` : '当前按标准价，可联系销售申请优惠'}</small></span></div>
    </Card>
    <div className="order-checkout-bar">
      <div><span>创建时间：{dayjs(order.created_time).format('YYYY-MM-DD HH:mm')}</span><Alert type="info" showIcon message="确认订单后将进入付款方式选择页面" /></div>
      <div className="order-checkout-total"><span>共 {order.quantity} 件商品</span><span>订单应付金额：</span><strong>¥ {order.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong><Button type="primary" size="large" onClick={() => navigate(`/orders/${order.id}/payment`)}>确认订单</Button></div>
    </div>
  </div>
}

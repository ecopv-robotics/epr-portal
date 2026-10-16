import { ArrowLeftOutlined, BankOutlined, CheckCircleOutlined, CopyOutlined, UploadOutlined } from '@ant-design/icons'
import { Button, Card, Input, Result, Skeleton, Typography, Upload, message } from 'antd'
import axios from 'axios'
import { useEffect, useState } from 'react'
import type { UploadProps } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../api'
import type { PurchaseOrder } from '../types'

type PaymentMethod = 'OFFLINE'

export default function PaymentPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [order, setOrder] = useState<PurchaseOrder>()
  const [loading, setLoading] = useState(true)
  const [paying, setPaying] = useState(false)
  const [method] = useState<PaymentMethod>('OFFLINE')
  const [payerName, setPayerName] = useState('')
  const [paymentProof, setPaymentProof] = useState('')

  const proofUpload: UploadProps = {
    accept: 'image/jpeg,image/png',
    maxCount: 1,
    customRequest: async ({ file, onSuccess, onError }) => {
      try {
        const body = new FormData()
        body.append('file', file as File)
        body.append('purpose', 'document')
        const { data } = await api.post<{ file_url: string }>('/files/upload', body)
        setPaymentProof(data.file_url)
        onSuccess?.(data)
        message.success('付款凭证上传成功')
      } catch (error) {
        setPaymentProof('')
        onError?.(error as Error)
        message.error('付款凭证上传失败')
      }
    },
    onRemove: () => { setPaymentProof(''); return true },
  }

  useEffect(() => {
    api.get<PurchaseOrder>(`/portal/orders/${id}`).then(({ data }) => setOrder(data)).catch(() => message.error('订单加载失败')).finally(() => setLoading(false))
  }, [id])

  async function finishPayment() {
    if (!payerName.trim() || !paymentProof) {
      message.warning('请填写付款账户名称并上传转账凭证')
      return
    }
    setPaying(true)
    try {
      const { data } = await api.post<PurchaseOrder>(`/portal/orders/${id}/pay`, {
        payment_method: method,
        payer_name: payerName.trim() || undefined,
        payment_proof: paymentProof || undefined,
      })
      setOrder(data)
      message.success(data.status === 'PAYMENT_CONFIRMING' ? '付款凭证已提交，等待确认' : '付款成功，EPR 服务已创建')
    } catch (reason) {
      message.error(axios.isAxiosError(reason) ? reason.response?.data?.detail ?? '付款失败' : '付款失败')
    } finally { setPaying(false) }
  }

  function copy(text: string) {
    void navigator.clipboard.writeText(text)
    message.success('已复制')
  }

  if (loading) return <div className="page-container"><Card className="data-card"><Skeleton active /></Card></div>
  if (!order) return <div className="page-container"><Result status="404" title="订单不存在" extra={<Button type="primary" onClick={() => navigate('/services')}>返回购买服务</Button>} /></div>
  if (order.status === 'PAID') return <div className="page-container payment-page"><Card className="data-card"><Result status="success" title="付款成功" subTitle={`订单 ${order.order_no} 已支付，EPR 服务已进入待提交资料状态。`} extra={[
    <Button type="primary" key="registration" onClick={() => navigate('/epr/registrations')}>查看 EPR 注册号</Button>,
    <Button key="material" onClick={() => navigate(`/account/orders/${order.id}`)}>查看服务实例</Button>,
  ]} /></Card></div>
  if (order.status === 'PAYMENT_CONFIRMING') return <div className="page-container payment-page"><Card className="data-card"><Result status="info" title="付款待确认" subTitle="线下付款凭证已提交，财务确认到账后将自动生成服务实例。" extra={<Button onClick={() => navigate(`/account/orders/${order.id}`)}>查看订单</Button>} /></Card></div>

  return <div className="page-container payment-page">
    <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(`/orders/${order.id}/confirm`)}>返回订单确认</Button>
    <Card className="data-card payment-card">
      <div className="payment-success-heading"><CheckCircleOutlined /><div><Typography.Title level={3}>订单提交成功，请尽快付款</Typography.Title><Typography.Text>订单号：<strong>{order.order_no}</strong></Typography.Text><small>请在 23:59:59 内完成支付，逾期订单将自动关闭</small></div><div className="payment-amount"><span>应付金额</span><strong>¥ {order.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong></div></div>
      <div className="payment-section-title">支付方式</div>
      <div className="payment-methods"><button className="selected"><BankOutlined /><span>线下对公转账</span><CheckCircleOutlined className="selected-check" /></button></div>
      <div className="offline-payment-panel">
        <div className="offline-reminder">为加快转账审核，请务必在付款备注中填写订单号：<strong>{order.order_no}</strong><Button type="link" size="small" icon={<CopyOutlined />} onClick={() => copy(order.order_no)}>复制</Button></div>
        <div className="offline-columns">
          <div className="bank-account-card"><Typography.Title level={4}>跨境合规收款账户信息</Typography.Title>
            <dl><dt>收款公司名称</dt><dd>EPR FLOW 合规服务有限公司（演示）</dd><dt>收款银行账号</dt><dd>6222 **** **** 2026 <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => copy('6222000000002026')} /></dd><dt>银行行号</dt><dd>308584001768</dd><dt>开户行名称</dt><dd>招商银行深圳科技园支行（演示）</dd><dt>转账备注</dt><dd><strong>{order.order_no}</strong> <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => copy(order.order_no)} /></dd></dl>
          </div>
          <div className="transfer-proof-card"><Typography.Title level={4}>线下付款成功后，请上传凭证</Typography.Title>
            <label>付款账户名称</label><Input size="large" placeholder="请填写转账截图上的付款账户" value={payerName} onChange={event => setPayerName(event.target.value)} />
            <label>上传转账截图</label><Upload {...proofUpload}><Button size="large" icon={<UploadOutlined />}>上传转账截图</Button></Upload>
            <Typography.Text type="secondary">凭证须包含付款账号及金额信息，支持 JPEG、PNG 格式。</Typography.Text>
          </div>
        </div>
      </div>
      <div className="payment-submit"><Button type="primary" size="large" loading={paying} onClick={finishPayment}>我已完成转账</Button></div>
    </Card>
  </div>
}

import { ArrowLeftOutlined, CloudUploadOutlined, DownloadOutlined, EditOutlined, EyeOutlined } from '@ant-design/icons'
import { Button, Card, Descriptions, Empty, Modal, Result, Skeleton, Space, Table, Tag, Typography, Upload, message } from 'antd'
import type { UploadProps } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../api'
import type { PurchaseOrder, ServiceInstance } from '../types'
import { customerProgress } from '../customerProgress'

const paymentLabels: Record<PurchaseOrder['status'], { label: string; color: string }> = {
  PENDING: { label: '待付款', color: 'warning' }, PAYMENT_CONFIRMING: { label: '付款待确认', color: 'processing' },
  PAID: { label: '已付款', color: 'success' }, CANCELLED: { label: '已取消', color: 'default' },
  PAYMENT_FAILED: { label: '支付失败', color: 'error' }, PARTIALLY_REFUNDED: { label: '部分退款', color: 'orange' }, REFUNDED: { label: '全部退款', color: 'default' },
}

export default function OrderDetailPage() {
  const { id } = useParams(); const navigate = useNavigate()
  const [order, setOrder] = useState<PurchaseOrder>(); const [loading, setLoading] = useState(true)
  const [preview, setPreview] = useState<{ url: string; title: string }>(); const [contractUploading, setContractUploading] = useState(false)
  const [countersignUploading, setCountersignUploading] = useState<number>()
  useEffect(() => { api.get<PurchaseOrder>(`/portal/orders/${id}`).then(({ data }) => setOrder(data)).catch(() => message.error('订单加载失败')).finally(() => setLoading(false)) }, [id])
  if (loading) return <div className="page-container"><Card><Skeleton active /></Card></div>
  if (!order) return <div className="page-container"><Result status="404" title="订单不存在" /></div>
  const fileOrigin = new URL(String(api.defaults.baseURL), window.location.origin).origin
  const fileUrl = (url: string) => /^(https?:|data:|blob:)/i.test(url) ? url : new URL(url, fileOrigin).href
  const signedContractUpload: UploadProps = { showUploadList: false, accept: '.pdf,application/pdf', disabled: contractUploading || order.status === 'CANCELLED', beforeUpload: file => { if (!file.name.toLowerCase().endsWith('.pdf')) { message.error('合同必须上传 PDF 文件'); return Upload.LIST_IGNORE } return true }, customRequest: async ({ file, onSuccess, onError }) => {
    setContractUploading(true)
    try {
      const body = new FormData(); body.append('file', file as File); body.append('purpose', 'document')
      const { data: uploaded } = await api.post<{ file_url: string }>('/files/upload', body)
      const { data: updated } = await api.put<PurchaseOrder>(`/portal/orders/${order.id}/signed-contract`, { signed_contract_file: uploaded.file_url })
      setOrder(updated); onSuccess?.(updated); message.success('客户签章版合同上传成功')
    } catch (error) { onError?.(error as Error); message.error('合同上传失败，请重新尝试') }
    finally { setContractUploading(false) }
  } }
  const countersignUpload = (instance: ServiceInstance): UploadProps => ({ showUploadList: false, accept: '.pdf,application/pdf', beforeUpload: file => { if (!file.name.toLowerCase().endsWith('.pdf')) { message.error('二次回签必须上传 PDF 文件'); return Upload.LIST_IGNORE } return true }, customRequest: async ({ file, onSuccess, onError }) => {
    setCountersignUploading(instance.id)
    try {
      const body = new FormData(); body.append('file', file as File); body.append('purpose', 'document')
      const { data: uploaded } = await api.post<{ file_url: string }>('/files/upload', body)
      const { data: updated } = await api.put<PurchaseOrder>(`/portal/applications/${instance.id}/countersign`, { countersign_file: uploaded.file_url })
      setOrder(updated); onSuccess?.(updated); message.success('二次回签文件已提交')
    } catch (error) { onError?.(error as Error); message.error('二次回签文件提交失败') }
    finally { setCountersignUploading(undefined) }
  } })
  const columns: ColumnsType<ServiceInstance> = [
    { title: '序号', dataIndex: 'instance_index', width: 72, render: value => `#${value}` },
    { title: '服务实例号', dataIndex: 'application_no', render: value => <strong className="application-no">{value}</strong> },
    { title: '企业名称', dataIndex: 'company_name', render: value => value || '待填写' },
    { title: '服务进度', render: (_, instance) => { const progress = customerProgress(instance); return <Tag color={progress.color}>{progress.label}</Tag> } },
    { title: 'EPR 注册号', dataIndex: 'registration_number', render: value => value || '—' },
    { title: '操作', width: 360, render: (_, instance) => <Space size={0} wrap>
      <Button type="link" icon={['DRAFT', 'NEED_FIX'].includes(instance.status) ? <EditOutlined /> : <EyeOutlined />} onClick={() => navigate(`/application/${instance.id}/form`)}>{['DRAFT', 'NEED_FIX'].includes(instance.status) ? '填写/补充资料' : '查看资料'}</Button>
      {instance.countersign_required && <Upload {...countersignUpload(instance)}><Button type="primary" size="small" loading={countersignUploading === instance.id} icon={<CloudUploadOutlined />}>上传二次回签</Button></Upload>}
      {instance.status === 'COMPLETED' && instance.certificate_file && <Button type="link" icon={<DownloadOutlined />} href={instance.certificate_file}>证书</Button>}
    </Space> },
  ]
  return <div className="page-container">
    <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/account/orders')}>返回我的订单</Button>
    <div className="page-heading"><div><Typography.Title level={2}>订单详情</Typography.Title><Typography.Text type="secondary">订单与服务实例分开管理，每个实例独立填写资料、审核和交付。</Typography.Text></div><Tag color={paymentLabels[order.status].color}>{paymentLabels[order.status].label}</Tag></div>
    <Card className="data-card"><Descriptions column={3} items={[
      { key: 'no', label: '订单号', children: order.order_no }, { key: 'service', label: '服务', children: order.service.title },
      { key: 'spec', label: '购买属性', children: [order.service.country, order.service.product_type, order.package_type, order.service_year].filter(Boolean).join(' / ') },
      { key: 'categories', label: '类别与品牌', children: order.product_configurations.length ? order.product_configurations.map(item => `${item.category}：${item.brands.join('、')}`).join('；') : '—' },
      { key: 'quantity', label: '数量', children: order.quantity }, { key: 'standard', label: '标准金额', children: `¥${order.standard_amount.toLocaleString()}` },
      { key: 'discount', label: '优惠抵扣', children: `-¥${order.discount_amount.toLocaleString()}` }, { key: 'amount', label: order.status === 'PAID' ? '实付金额' : '应付金额', children: `¥${(order.actual_paid_amount ?? order.total_amount).toLocaleString()}` },
      { key: 'contract', label: '待签合同', children: order.contract_file ? <Space wrap><Button type="link" icon={<EyeOutlined />} onClick={() => setPreview({ url: order.contract_file!, title: `${order.order_no} 待签合同` })}>查看合同 {order.contract_version || ''}</Button><Tag color={order.customer_signed_contract_file ? 'success' : 'warning'}>{order.customer_signed_contract_file ? '客户已盖章' : '待客户盖章'}</Tag></Space> : '销售上传后可在线查看' },
      { key: 'signed-contract', label: '客户签章版', children: order.contract_file ? <Space wrap><Upload {...signedContractUpload}><Button loading={contractUploading} icon={<CloudUploadOutlined />}>{order.customer_signed_contract_file ? '重新上传' : '上传盖章合同'}</Button></Upload>{order.customer_signed_contract_file && <Button type="link" icon={<EyeOutlined />} onClick={() => setPreview({ url: order.customer_signed_contract_file!, title: `${order.order_no} 客户签章版合同` })}>查看签章版</Button>}{order.signed_contract_uploaded_time && <Typography.Text type="secondary">{dayjs(order.signed_contract_uploaded_time).format('YYYY-MM-DD HH:mm')} 上传</Typography.Text>}</Space> : '请等待销售上传待签合同' },
      { key: 'time', label: '下单时间', children: dayjs(order.created_time).format('YYYY-MM-DD HH:mm') },
    ]} /></Card>
    <Card className="data-card" title={`服务实例（${order.service_instances.length}/${order.quantity}）`} extra={order.status === 'PAYMENT_CONFIRMING' ? '凭证上传后已生成，可立即填写资料' : '按购买数量生成'}>
      <Table rowKey="id" columns={columns} dataSource={order.service_instances} pagination={false} locale={{ emptyText: <Empty description="暂无服务实例" /> }} />
    </Card>
    <Modal title={preview?.title} open={Boolean(preview)} onCancel={() => setPreview(undefined)} width="min(1000px, 94vw)" footer={<Space>{preview && <Button icon={<DownloadOutlined />} href={fileUrl(preview.url)} target="_blank" rel="noreferrer">下载合同</Button>}<Button type="primary" onClick={() => setPreview(undefined)}>关闭</Button></Space>}>
      {preview && <iframe className="contract-preview-frame" src={fileUrl(preview.url)} title={preview.title} />}
    </Modal>
  </div>
}

import { AppstoreAddOutlined, EditOutlined, EyeOutlined, FileAddOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Card, Descriptions, Empty, Form, Input, Modal, Progress, Select, Space, Table, Tabs, Tag, Typography, Upload, message } from 'antd'
import type { UploadProps } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import axios from 'axios'
import dayjs from 'dayjs'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import type { Application, ApplicationStatus, Company, CompanyProfile } from '../types'

const regions: Record<string, string> = { MAINLAND_CHINA: '中国大陆公司', HONG_KONG: '中国香港公司', EU: '欧盟公司', OTHER: '其他公司' }
const emptyCompany: Company = { company_name: '', registration_region: 'MAINLAND_CHINA' }
const statusMeta: Record<ApplicationStatus, { label: string; color: string }> = { DRAFT: { label: '草稿', color: 'default' }, SUBMITTED: { label: '待审核', color: 'blue' }, REVIEWING: { label: '审核中', color: 'processing' }, NEED_FIX: { label: '待补资料', color: 'warning' }, REGISTERING: { label: '注册中', color: 'cyan' }, COMPLETED: { label: '已完成', color: 'success' } }

function FilePreview({ url, title }: { url: string; title: string; trigger?: 'link' }) {
  const origin = new URL(String(api.defaults.baseURL), window.location.origin).origin
  const href = /^(https?:|data:|blob:)/i.test(url) ? url : new URL(url, origin).href
  return <Button type="link" size="small" onClick={() => window.open(href, '_blank', 'noopener,noreferrer')}>预览{title}</Button>
}

function DocumentUpload({ value, onChange }: { value?: string; onChange?: (value?: string) => void }) {
  const props: UploadProps = { showUploadList: false, accept: '.pdf,.jpg,.jpeg,.png', customRequest: async ({ file, onSuccess, onError }) => {
    try { const body = new FormData(); body.append('file', file as File); body.append('purpose', 'document'); const { data } = await api.post<{ file_url: string }>('/files/upload', body); onChange?.(data.file_url); onSuccess?.(data); message.success('上传成功') }
    catch (error) { onError?.(error as Error); message.error('上传失败') }
  } }
  return <Space><Upload {...props}><Button icon={<FileAddOutlined />}>{value ? '重新上传' : '上传文件'}</Button></Upload>{value && <FilePreview url={value} title="企业文件" trigger="link" />}</Space>
}

export default function CompaniesPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<CompanyProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState<Company>()
  const [viewing, setViewing] = useState<CompanyProfile>()
  const [relatedCompany, setRelatedCompany] = useState<CompanyProfile>()
  const [relatedOrders, setRelatedOrders] = useState<Application[]>([])
  const [relatedLoading, setRelatedLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm<Company>()
  async function load() { setLoading(true); try { setItems((await api.get<CompanyProfile[]>('/companies')).data) } catch { message.error('企业资料加载失败') } finally { setLoading(false) } }
  useEffect(() => { void load() }, [])
  const filtered = useMemo(() => items.filter(item => [item.company_name, item.company_name_en, item.register_number].some(v => v?.toLowerCase().includes(query.toLowerCase()))), [items, query])
  function openEdit(company?: Company) { const value = company ?? emptyCompany; setEditing(value); form.setFieldsValue(value) }
  async function openRelated(company: CompanyProfile) { setRelatedCompany(company); setRelatedLoading(true); try { setRelatedOrders((await api.get<Application[]>(`/companies/${company.id}/applications`)).data) } catch { message.error('关联递单加载失败') } finally { setRelatedLoading(false) } }
  async function save() { setSaving(true); try { const values = await form.validateFields(); if (editing?.id) await api.put(`/companies/${editing.id}`, values); else await api.post('/companies', values); message.success('企业资料已保存'); setEditing(undefined); await load() } catch (error) { if (axios.isAxiosError(error)) message.error(error.response?.data?.detail ?? '保存失败') } finally { setSaving(false) } }
  const columns: ColumnsType<CompanyProfile> = [
    { title: '企业名称', dataIndex: 'company_name', render: (v, r) => <div><strong>{v}</strong>{r.company_name_en && <div className="muted">{r.company_name_en}</div>}</div> },
    { title: '注册地', dataIndex: 'registration_region', render: v => regions[v] || '未填写' },
    { title: '企业类型', dataIndex: 'company_type', render: v => v || '未填写' },
    { title: '营业执照号 / 企业注册号', dataIndex: 'register_number', render: v => v || '--' },
    { title: '资料完整度', dataIndex: 'completeness', render: v => <Progress percent={v} size="small" style={{ width: 120 }} /> },
    { title: '关联递单', dataIndex: 'application_count', render: (v, r) => <Button type="link" size="small" onClick={() => void openRelated(r)}><Tag color="blue" style={{ cursor: 'pointer', margin: 0 }}>{v} 份</Tag></Button> },
    { title: '操作', key: 'action', render: (_, r) => <Space size={0}><Button type="link" icon={<EyeOutlined />} onClick={() => setViewing(r)}>查看</Button><Button type="link" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button><Button type="link" icon={<AppstoreAddOutlined />} onClick={() => navigate('/services')}>购买服务</Button></Space> },
  ]
  const legal = viewing?.legal_person
  return <div className="page-container">
    <div className="page-heading"><div><Typography.Title level={2}>企业资料库</Typography.Title><Typography.Text type="secondary">统一管理企业与法人档案，新建递单时可直接复用</Typography.Text></div><Button type="primary" size="large" icon={<PlusOutlined />} onClick={() => openEdit()}>新增企业</Button></div>
    <Card className="data-card"><div className="table-toolbar"><Typography.Text type="secondary">共 {items.length} 个企业主体</Typography.Text><Input allowClear prefix={<SearchOutlined />} placeholder="企业名称 / 证照号" value={query} onChange={e => setQuery(e.target.value)} /></div><Table rowKey="id" loading={loading} columns={columns} dataSource={filtered} locale={{ emptyText: <Empty description="暂无企业资料" /> }} /></Card>
    <Modal title={editing?.id ? '编辑企业资料' : '新增企业'} width={820} open={Boolean(editing)} onCancel={() => setEditing(undefined)} onOk={save} confirmLoading={saving} okText="保存"><Form form={form} layout="vertical"><Tabs items={[
      { key: 'base', label: '企业信息', children: <><Form.Item name="company_name" label="企业中文名称" rules={[{ required: true }]}><Input /></Form.Item><Form.Item name="company_name_en" label="企业英文名称"><Input /></Form.Item><Form.Item name="registration_region" label="企业注册地" rules={[{ required: true }]}><Select options={Object.entries(regions).map(([value, label]) => ({ value, label }))} /></Form.Item><Form.Item name="company_type" label="企业类型"><Input /></Form.Item><Form.Item name="register_number" label="营业执照号 / 企业注册号"><Input /></Form.Item><Form.Item name="established_date" label="成立日期"><Input type="date" /></Form.Item><Form.Item name="vat_number" label="VAT 税号"><Input /></Form.Item><Form.Item name="register_address" label="注册地址"><Input /></Form.Item></> },
      { key: 'legal', label: '法人信息', children: <><Form.Item name={['legal_person', 'name_cn']} label="法人中文名"><Input /></Form.Item><Form.Item name={['legal_person', 'name_en']} label="法人英文名"><Input /></Form.Item><Form.Item name={['legal_person', 'certificate_type']} label="证件类型"><Select options={[{ value: 'ID_CARD', label: '身份证' }, { value: 'PASSPORT', label: '护照' }]} /></Form.Item><Form.Item name={['legal_person', 'contact_email']} label="联系邮箱"><Input /></Form.Item><Form.Item name={['legal_person', 'contact_phone']} label="联系电话"><Input /></Form.Item></> },
      { key: 'files', label: '企业文件', children: <><Form.Item name="license_file" label="营业执照 / 注册证明"><DocumentUpload /></Form.Item><Form.Item name="credit_report_file" label="企业信用报告"><DocumentUpload /></Form.Item><Form.Item name="license_translation_file" label="营业执照翻译件"><DocumentUpload /></Form.Item></> },
    ]} /></Form></Modal>
    <Modal title={`${relatedCompany?.company_name || ''} · 关联递单`} width={980} open={Boolean(relatedCompany)} onCancel={() => setRelatedCompany(undefined)} footer={<Button onClick={() => setRelatedCompany(undefined)}>关闭</Button>}>
      <Table rowKey="id" loading={relatedLoading} dataSource={relatedOrders} pagination={false} locale={{ emptyText: <Empty description="该企业暂无关联递单" /> }} columns={[
        { title: '申请编号', dataIndex: 'application_no', render: (v: string) => <strong className="application-no">{v}</strong> },
        { title: '国家', dataIndex: 'country' },
        { title: '服务', dataIndex: 'service_type' },
        { title: '注册号', dataIndex: 'registration_number', render: (v?: string) => v || '--' },
        { title: '服务进度', dataIndex: 'status', render: (v: ApplicationStatus) => <Tag color={statusMeta[v].color}>{statusMeta[v].label}</Tag> },
        { title: '提交时间', dataIndex: 'submitted_time', render: (v?: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '--' },
        { title: '操作', render: (_: unknown, r: Application) => <Button type="link" icon={<EyeOutlined />} onClick={() => navigate(`/application/${r.id}/form`)}>查看递单</Button> },
      ]} />
    </Modal>
    <Modal title="企业资料详情" width={1000} styles={{ body: { maxHeight: '68vh', overflowY: 'auto', paddingRight: 8 } }} open={Boolean(viewing)} onCancel={() => setViewing(undefined)} footer={<Space><Button onClick={() => setViewing(undefined)}>关闭</Button><Button onClick={() => { const company = viewing; setViewing(undefined); openEdit(company) }}>编辑资料</Button><Button type="primary" onClick={() => navigate('/services')}>购买服务</Button></Space>}>
      <div className="registration-result-section">
        <div className="section-heading"><Typography.Title level={3}>公司信息</Typography.Title></div>
        <Descriptions bordered column={1} labelStyle={{ width: 250 }}>
          <Descriptions.Item label="公司注册地">{regions[viewing?.registration_region || ''] || '--'}</Descriptions.Item>
          <Descriptions.Item label="公司类型">{viewing?.company_type || '--'}</Descriptions.Item>
          <Descriptions.Item label="公司中文名称">{viewing?.company_name || '--'}</Descriptions.Item>
          <Descriptions.Item label="公司英文名称">{viewing?.company_name_en || '--'}</Descriptions.Item>
          <Descriptions.Item label="营业执照号 / 企业注册号">{viewing?.register_number || '--'}</Descriptions.Item>
          <Descriptions.Item label="公司成立日期">{viewing?.established_date || '--'}</Descriptions.Item>
          <Descriptions.Item label="VAT 税号">{viewing?.vat_number || '--'}</Descriptions.Item>
          <Descriptions.Item label="公司 / 个体经营注册地址">{viewing?.register_address || '--'}</Descriptions.Item>
          <Descriptions.Item label="公司营业执照 / 注册证明">{viewing?.license_file ? <FilePreview url={viewing.license_file} title="营业执照" trigger="link" /> : '--'}</Descriptions.Item>
          <Descriptions.Item label="营业执照翻译件">{viewing?.license_translation_file ? <FilePreview url={viewing.license_translation_file} title="营业执照翻译件" trigger="link" /> : '--'}</Descriptions.Item>
          <Descriptions.Item label="企业信用报告">{viewing?.credit_report_file ? <FilePreview url={viewing.credit_report_file} title="信用报告" trigger="link" /> : '--'}</Descriptions.Item>
          <Descriptions.Item label="公司注册证明书 CR">{viewing?.cr_file ? <FilePreview url={viewing.cr_file} title="CR" trigger="link" /> : '--'}</Descriptions.Item>
          <Descriptions.Item label="商业登记证 BR">{viewing?.br_file ? <FilePreview url={viewing.br_file} title="BR" trigger="link" /> : '--'}</Descriptions.Item>
          <Descriptions.Item label="NNC1 / NAR1">{viewing?.nnc1_file ? <FilePreview url={viewing.nnc1_file} title="NNC1 / NAR1" trigger="link" /> : '--'}</Descriptions.Item>
          <Descriptions.Item label="董事索引">{viewing?.director_index_file ? <FilePreview url={viewing.director_index_file} title="董事索引" trigger="link" /> : '--'}</Descriptions.Item>
        </Descriptions>
        <div className="section-heading result-subheading"><Typography.Title level={3}>法人信息</Typography.Title></div>
        <Descriptions bordered column={1} labelStyle={{ width: 250 }}>
          <Descriptions.Item label="法人证件类型">{legal?.certificate_type === 'ID_CARD' ? '身份证' : legal?.certificate_type === 'PASSPORT' ? '护照' : '--'}</Descriptions.Item>
          <Descriptions.Item label="法人中文名">{legal?.name_cn || '--'}</Descriptions.Item>
          <Descriptions.Item label="法人英文名 / 拼音名">{legal?.name_en || '--'}</Descriptions.Item>
          <Descriptions.Item label="证件号码">{legal?.certificate_number || '--'}</Descriptions.Item>
          <Descriptions.Item label="性别">{legal?.gender === 'MALE' ? '男' : legal?.gender === 'FEMALE' ? '女' : legal?.gender || '--'}</Descriptions.Item>
          <Descriptions.Item label="联系邮箱">{legal?.contact_email || '--'}</Descriptions.Item>
          <Descriptions.Item label="联系电话">{legal?.contact_phone || '--'}</Descriptions.Item>
          <Descriptions.Item label="身份证人像面 / 护照资料页">{legal?.front_file ? <FilePreview url={legal.front_file} title="法人证件" trigger="link" /> : '--'}</Descriptions.Item>
          <Descriptions.Item label="身份证国徽面">{legal?.back_file ? <FilePreview url={legal.back_file} title="身份证国徽面" trigger="link" /> : '--'}</Descriptions.Item>
          <Descriptions.Item label="法人代表签名">{legal?.signature_file ? <FilePreview url={legal.signature_file} title="法人签名" trigger="link" /> : '--'}</Descriptions.Item>
        </Descriptions>
      </div>
    </Modal>
  </div>
}

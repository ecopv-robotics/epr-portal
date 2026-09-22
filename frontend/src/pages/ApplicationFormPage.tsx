import {
  ArrowLeftOutlined, CheckCircleFilled, CloudUploadOutlined, CopyOutlined, DeleteOutlined,
  DownloadOutlined, EyeOutlined, FileDoneOutlined, FileOutlined, FileTextOutlined, PlusOutlined, ProfileOutlined, SaveOutlined,
} from '@ant-design/icons'
import {
  Alert, Button, Card, Col, Descriptions, Divider, Empty, Form, Input, InputNumber, List, Modal,
  Progress, Radio, Row, Select, Space, Spin, Steps, Table, Tabs, Tag, Timeline, Typography, Upload, message,
} from 'antd'
import type { UploadProps } from 'antd'
import axios from 'axios'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../api'
import type {
  ApplicationFormData, ApplicationStatus, Company, DynamicField, LegalPerson, MaterialFile, Product, StatusHistory, Store,
} from '../types'

const stepItems = [
  { title: '公司信息' }, { title: '法人信息' }, { title: '店铺信息' },
  { title: '产品信息' }, { title: '材料上传' }, { title: '确认提交' },
]

const STATUS_META: Record<ApplicationStatus, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' }, SUBMITTED: { label: '已提交', color: 'blue' },
  REVIEWING: { label: '审核中', color: 'processing' }, NEED_FIX: { label: '待补资料', color: 'warning' },
  REGISTERING: { label: '注册中', color: 'cyan' },
  COMPLETED: { label: '已完成', color: 'success' },
}

type UploadResult = { file_url: string; original_name: string; file_size: number }

type ChecklistItem = {
  key: string
  requirementId?: number
  module: string
  materialName: string
  required: boolean
  fileType: string
  description: string
  fileUrl?: string
  originalName?: string
}

const EXAMPLE_FILES = {
  license: { url: '/examples/business-license.png', label: '营业执照示例' },
  creditReport: { url: '/examples/credit-report.svg', label: '企业信用报告示例' },
  identityFront: { url: '/examples/id-card-front.svg', label: '身份证人像面示例' },
  identityBack: { url: '/examples/id-card-back.svg', label: '身份证国徽面示例' },
  signature: { url: '/examples/signature.svg', label: '签名示例' },
} as const

function resolveFileUrl(value: string) {
  if (/^(https?:|data:|blob:)/i.test(value)) return value
  if (value.startsWith('/examples/')) return new URL(value, window.location.origin).href
  const apiBase = String(api.defaults.baseURL ?? window.location.origin)
  const apiOrigin = new URL(apiBase, window.location.origin).origin
  return new URL(value, apiOrigin).href
}

function isImageFile(url: string) { return /\.(?:jpe?g|png|webp|gif|svg)(?:[?#].*)?$/i.test(url) }

function reusableMaterialFile(data: ApplicationFormData, requirementId: number, materialName: string): MaterialFile | undefined {
  const name = materialName.replace(/\s/g, '').toUpperCase()
  const company = data.company
  if (!company) return undefined
  const legal = company.legal_person
  const choices: [boolean, string | undefined, string][] = [
    [name.includes('企业信用报告'), company.credit_report_file, '企业信用报告'],
    [name.includes('NNC1') || name.includes('NAR1'), company.nnc1_file, 'NNC1-NAR1'],
    [name.includes('董事索引'), company.director_index_file, '董事索引'],
    [name.includes('商业登记证') || name === 'BR', company.br_file, '商业登记证-BR'],
    [name.includes('公司注册证明') || name === 'CR', company.cr_file || company.license_file, '公司注册证明-CR'],
    [name.includes('营业执照') || name.includes('注册证明'), company.license_file || company.cr_file, '营业执照-注册证明'],
    [name.includes('法人身份证') || name.includes('法人证件') || name.includes('身份证/护照'), legal?.front_file, '法人身份证-护照'],
    [name.includes('法人签名') || name === '签名', legal?.signature_file, '法人签名'],
    [name.includes('店铺后台截图') || name.includes('店铺截图'), data.store?.screenshot_file, '店铺后台截图'],
  ]
  const match = choices.find(([matched, url]) => matched && url)
  if (!match?.[1]) return undefined
  const extension = match[1].includes('.') ? match[1].split('.').pop() : 'pdf'
  return { id: -requirementId, requirement_id: requirementId, file_url: match[1], original_name: `${match[2]}.${extension}`, file_size: 0, upload_time: data.application.created_time, auto_synced: true }
}

function FilePreview({ url, title, trigger = 'card' }: { url: string; title: string; trigger?: 'card' | 'link' }) {
  const [open, setOpen] = useState(false)
  const previewUrl = resolveFileUrl(url)
  return <>
    {trigger === 'link'
      ? <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => setOpen(true)}>预览</Button>
      : <button type="button" className="file-preview-card" onClick={() => setOpen(true)} aria-label={`预览${title}`}>
          {isImageFile(previewUrl) ? <img src={previewUrl} alt={title} /> : <FileOutlined className="file-preview-icon" />}
          <span className="file-preview-badge"><EyeOutlined /> 预览</span>
          <strong>{title}</strong>
        </button>}
    <Modal className="file-preview-modal" title={title} open={open} onCancel={() => setOpen(false)} width="min(920px, 92vw)" footer={<Space><Button href={previewUrl} target="_blank">新窗口打开</Button><Button type="primary" onClick={() => setOpen(false)}>关闭</Button></Space>}>
      {isImageFile(previewUrl) ? <img className="file-preview-image" src={previewUrl} alt={title} /> : <iframe className="file-preview-frame" src={previewUrl} title={title} />}
    </Modal>
  </>
}

function MaterialExample({ materialName }: { materialName: string }) {
  const [open, setOpen] = useState(false)
  const example = /营业执照|注册证明/.test(materialName) ? EXAMPLE_FILES.license
    : /信用报告/.test(materialName) ? EXAMPLE_FILES.creditReport
      : /身份证|护照/.test(materialName) ? EXAMPLE_FILES.identityFront
        : /签名/.test(materialName) ? EXAMPLE_FILES.signature
          : undefined

  return <>
    <Button type="link" size="small" className="example-link" icon={<EyeOutlined />} onClick={() => setOpen(true)}>查看示例</Button>
    <Modal title={`${materialName} · 示例`} open={open} onCancel={() => setOpen(false)} width={680} footer={<Button type="primary" onClick={() => setOpen(false)}>关闭</Button>}>
      {example
        ? <img className="material-example-image" src={example.url} alt={`${materialName}示例`} />
        : <div className="material-example-sheet">
            <FileTextOutlined />
            <Typography.Title level={4}>{materialName}</Typography.Title>
            <Typography.Text type="secondary">示例文件仅用于说明材料类型，正式提交时请上传真实、清晰、完整且在有效期内的资料。</Typography.Text>
            <div className="material-example-watermark">示例 SAMPLE</div>
          </div>}
      <Alert className="material-example-tip" type="warning" showIcon message="示例仅供格式参考，请勿直接作为正式资料提交。" />
    </Modal>
  </>
}

async function uploadCommon(file: File, purpose: string): Promise<UploadResult> {
  const body = new FormData(); body.append('file', file); body.append('purpose', purpose)
  const { data } = await api.post<UploadResult>('/files/upload', body)
  return data
}

function FileUpload({
  value, onChange, purpose = 'document', accept = '.pdf,.jpg,.jpeg,.png', hint = 'JPG、JPEG、PNG、PDF，最大 20MB', example,
}: { value?: string; onChange?: (value: string) => void; purpose?: string; accept?: string; hint?: string; example?: { url: string; label: string } }) {
  const props: UploadProps = {
    showUploadList: false,
    accept,
    customRequest: async ({ file, onSuccess, onError }) => {
      try { const result = await uploadCommon(file as File, purpose); onChange?.(result.file_url); onSuccess?.(result) }
      catch (error) { onError?.(error as Error); message.error(axios.isAxiosError(error) ? error.response?.data?.detail ?? '上传失败' : '上传失败') }
    },
  }
  return <div className="file-field">
    <div className="file-upload-row">
      <Upload.Dragger {...props} className={value ? 'uploaded' : ''}><CloudUploadOutlined className="upload-icon" /><div>{value ? '已上传，点击重新选择' : '点击或拖动文件上传'}</div>{value && <Tag color="success" icon={<CheckCircleFilled />}>上传成功</Tag>}</Upload.Dragger>
      {value ? <FilePreview url={value} title="已上传文件" /> : example ? <FilePreview url={example.url} title={example.label} /> : null}
    </div>
    <Typography.Text type="secondary">支持 {hint}</Typography.Text>
  </div>
}

const COMPANY_REGION_OPTIONS = [
  { value: 'MAINLAND_CHINA', label: '中国大陆公司' }, { value: 'HONG_KONG', label: '中国香港公司' },
  { value: 'EU', label: '欧盟公司' }, { value: 'OTHER', label: '其他公司' },
]

const COMPANY_TYPE_OPTIONS: Record<string, string[]> = {
  MAINLAND_CHINA: ['有限责任公司', '有限责任公司(自然人独资)', '股份有限公司', '个人独资企业', '合伙企业', '个体工商户', '个人'],
  HONG_KONG: ['私人股份有限公司', '公众股份有限公司', '担保有限公司', '无限公司', '独资经营', '合伙经营'],
  EU: ['Private Limited Company', 'Public Limited Company', 'Sole Trader', 'Partnership', 'Other'],
  OTHER: ['有限责任公司', '股份有限公司', '个人独资企业', '合伙企业', '个体工商户', '其他'],
}

export default function ApplicationFormPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState<ApplicationFormData>()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [generatingTranslation, setGeneratingTranslation] = useState(false)
  const [generatingAuthorization, setGeneratingAuthorization] = useState(false)
  const [step, setStep] = useState(0)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [checklistOpen, setChecklistOpen] = useState(false)
  const [history, setHistory] = useState<Company[]>([])
  const [products, setProducts] = useState<Record<string, string | number | undefined>[]>([])
  const [materialFiles, setMaterialFiles] = useState<MaterialFile[]>([])
  const [statusHistory, setStatusHistory] = useState<StatusHistory[]>([])
  const [companyForm] = Form.useForm<Company>()
  const [legalForm] = Form.useForm<LegalPerson>()
  const [storeForm] = Form.useForm<Store>()
  const registrationRegion = Form.useWatch('registration_region', { form: companyForm, preserve: true }) ?? data?.company?.registration_region ?? 'MAINLAND_CHINA'
  const certificateType = Form.useWatch('certificate_type', { form: legalForm, preserve: true }) ?? data?.company?.legal_person?.certificate_type ?? 'ID_CARD'
  const watchedCompany = Form.useWatch([], { form: companyForm, preserve: true }) as Partial<Company> | undefined
  const watchedLegal = Form.useWatch([], { form: legalForm, preserve: true }) as Partial<LegalPerson> | undefined

  async function load() {
    setLoading(true)
    try {
      const response = await api.get<ApplicationFormData>(`/applications/${id}/form`)
      setData(response.data)
      setProducts(response.data.products.length ? response.data.products.map((item) => item.product_data) : [{}])
      setMaterialFiles(response.data.material_files)
      const historyResponse = await api.get<StatusHistory[]>(`/applications/${id}/status-history`)
      setStatusHistory(historyResponse.data)
    } catch { message.error('递单资料加载失败'); navigate('/applications') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  // Only the active step is mounted. Populate its form after the API data has
  // rendered so Form.initialValues cannot replace persisted application data.
  useEffect(() => {
    if (!data) return
    if (step === 0) {
      companyForm.resetFields()
      companyForm.setFieldsValue(data.company
        ? { ...data.company, registration_region: data.company.registration_region ?? 'MAINLAND_CHINA' }
        : { registration_region: 'MAINLAND_CHINA' } as Company)
    } else if (step === 1) {
      legalForm.resetFields()
      legalForm.setFieldsValue(data.company?.legal_person ?? { certificate_type: 'ID_CARD' })
    } else if (step === 2) {
      storeForm.resetFields()
      if (data.store) storeForm.setFieldsValue(data.store)
    }
  }, [data, step, companyForm, legalForm, storeForm])

  const effectiveMaterialFiles = useMemo(() => {
    if (!data) return materialFiles
    const explicitFiles = materialFiles.filter((file) => !file.auto_synced)
    return data.template.materials.map((requirement) => explicitFiles.find((file) => file.requirement_id === requirement.id) ?? reusableMaterialFile(data, requirement.id, requirement.material_name)).filter((file): file is MaterialFile => Boolean(file))
  }, [data, materialFiles])
  const checklistItems = useMemo<ChecklistItem[]>(() => {
    if (!data) return []
    const company = { ...data.company, ...watchedCompany }
    const legal = { ...data.company?.legal_person, ...watchedLegal }
    const region = company.registration_region ?? registrationRegion
    const certificate = legal.certificate_type ?? certificateType
    const items: ChecklistItem[] = []
    const add = (key: string, module: string, materialName: string, required: boolean, fileUrl?: string) => items.push({
      key, module, materialName, required, fileUrl,
      originalName: fileUrl ? materialName : undefined,
      fileType: 'PDF,JPG,JPEG,PNG', description: '单个文件不超过 20MB',
    })

    if (region === 'MAINLAND_CHINA') {
      add('subject-license', '公司信息', '公司营业执照', true, company.license_file)
      add('subject-license-translation', '公司信息', '营业执照翻译件', false, company.license_translation_file)
      add('subject-credit-report', '公司信息', '企业信用报告', true, company.credit_report_file)
    } else if (region === 'HONG_KONG') {
      add('subject-cr', '公司信息', '公司注册证明书 CR', true, company.cr_file)
      add('subject-br', '公司信息', '商业登记证 BR', true, company.br_file)
      add('subject-nnc1', '公司信息', 'NNC1 / NAR1', true, company.nnc1_file)
      add('subject-director-index', '公司信息', '董事索引', false, company.director_index_file)
    } else {
      add('subject-registration', '公司信息', '公司营业执照 / 注册证明', true, company.license_file)
    }

    if (certificate === 'ID_CARD') {
      add('legal-id-front', '法人信息', '法人身份证－人像面', true, legal.front_file)
      add('legal-id-back', '法人信息', '法人身份证－国徽面', true, legal.back_file)
    } else {
      add('legal-passport', '法人信息', '法人护照资料页', true, legal.front_file)
    }
    add('legal-signature', '法人信息', '法人代表签名', true, legal.signature_file)

    data.template.materials.filter((requirement) => !isConditionalIdentityMaterial(requirement.material_name)).forEach((requirement) => {
      const file = effectiveMaterialFiles.find((entry) => entry.requirement_id === requirement.id)
      items.push({
        key: `service-${requirement.id}`,
        requirementId: requirement.id,
        module: materialModule(requirement.material_name),
        materialName: requirement.material_name,
        required: requirement.required,
        fileType: requirement.file_type,
        description: requirement.description,
        fileUrl: file?.file_url,
        originalName: file?.original_name,
      })
    })
    return items
  }, [certificateType, data, effectiveMaterialFiles, registrationRegion, watchedCompany, watchedLegal])
  const requiredUploaded = useMemo(
    () => checklistItems.filter((item) => item.required).every((item) => Boolean(item.fileUrl)),
    [checklistItems],
  )
  const editable = data?.application.status === 'DRAFT' || data?.application.status === 'NEED_FIX'

  async function openHistory() {
    try { const response = await api.get<Company[]>('/company/history'); setHistory(response.data); setHistoryOpen(true) }
    catch { message.error('历史企业资料加载失败') }
  }

  function reuseCompany(company: Company) {
    companyForm.setFieldsValue({ ...company, registration_region: company.registration_region ?? 'MAINLAND_CHINA' }); if (company.legal_person) legalForm.setFieldsValue(company.legal_person)
    setData((current) => current ? { ...current, company } : current)
    setHistoryOpen(false); message.success('已填充公司和法人信息，对应证明材料将自动同步')
  }

  async function saveCurrent(next = false) {
    setSaving(true)
    try {
      if (step === 0) {
        const values = await companyForm.validateFields()
        const response = await api.put<Company>(`/applications/${id}/company`, { ...values, id: data?.company?.id })
        setData((current) => current ? { ...current, company: response.data } : current)
      } else if (step === 1) {
        const values = await legalForm.validateFields()
        const response = await api.put<Company>(`/applications/${id}/legal-person`, values)
        setData((current) => current ? { ...current, company: response.data } : current)
      } else if (step === 2) {
        const values = await storeForm.validateFields()
        const response = await api.put<Store>(`/applications/${id}/store`, values)
        setData((current) => current ? { ...current, store: response.data } : current)
      } else if (step === 3) {
        if (!products.length) throw new Error('请至少添加一个产品')
        for (const field of data?.template.fields ?? []) {
          if (field.required && products.some((product) => product[field.field_name] === undefined || product[field.field_name] === '')) throw new Error(`请填写所有产品的${field.label}`)
        }
        const response = await api.put<Product[]>(`/applications/${id}/products`, products.map((product_data) => ({ product_data })))
        setProducts(response.data.map((item) => item.product_data))
        setData((current) => current ? { ...current, products: response.data } : current)
      } else if (step === 4 && !requiredUploaded) throw new Error('请上传全部必填材料')
      message.success('保存成功')
      if (next) setStep((value) => Math.min(value + 1, 5))
      return true
    } catch (error) {
      if (error instanceof Error && !axios.isAxiosError(error)) message.warning(error.message)
      else if (axios.isAxiosError(error)) message.error(error.response?.data?.detail ?? '保存失败')
      return false
    } finally { setSaving(false) }
  }

  function updateProduct(index: number, field: string, value: string | number | null) {
    setProducts((current) => current.map((item, i) => i === index ? { ...item, [field]: value ?? undefined } : item))
  }

  async function uploadMaterial(requirementId: number, file: File) {
    const body = new FormData(); body.append('application_id', id); body.append('requirement_id', String(requirementId)); body.append('file', file)
    try {
      const response = await api.post<MaterialFile>('/material/upload', body)
      setMaterialFiles((current) => [...current.filter((item) => item.requirement_id !== requirementId), response.data])
      message.success('材料上传成功')
    } catch (error) { message.error(axios.isAxiosError(error) ? error.response?.data?.detail ?? '上传失败' : '上传失败'); throw error }
  }

  async function generateLicenseTranslation() {
    setGeneratingTranslation(true)
    try {
      const values = await companyForm.validateFields()
      const saved = await api.put<Company>(`/applications/${id}/company`, { ...values, id: data?.company?.id })
      const response = await api.post<UploadResult>(`/applications/${id}/company/license-translation`, undefined, { timeout: 120000 })
      const company = { ...saved.data, license_translation_file: response.data.file_url }
      companyForm.setFieldValue('license_translation_file', response.data.file_url)
      setData((current) => current ? { ...current, company } : current)
      message.success('营业执照翻译件已生成，请预览并核对')
    } catch (error) {
      if (axios.isAxiosError(error)) message.error(error.response?.data?.detail ?? '翻译件生成失败')
      else if (error instanceof Error) message.warning(error.message)
    } finally { setGeneratingTranslation(false) }
  }

  async function generateAuthorization() {
    setGeneratingAuthorization(true)
    try {
      if (editable && step <= 3 && !(await saveCurrent(false))) return
      const response = await api.get<Blob>(`/applications/${id}/authorization/germany-weee`, {
        responseType: 'blob', timeout: 120000,
      })
      const url = URL.createObjectURL(response.data)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${data?.application.application_no ?? 'Germany-WEEE'}-德国WEEE授权书.docx`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
      message.success('德国 WEEE 授权书已生成')
    } catch (error) {
      let detail: { message?: string; missing_fields?: string[] } | string | undefined
      if (axios.isAxiosError(error) && error.response?.data instanceof Blob) {
        try { detail = JSON.parse(await error.response.data.text()).detail } catch { detail = undefined }
      }
      if (typeof detail === 'object' && Array.isArray(detail.missing_fields)) {
        Modal.error({ title: detail.message || '授权书资料不完整', width: 560, content: <ul>{detail.missing_fields.map((item) => <li key={item}>{item}</li>)}</ul> })
      } else message.error(typeof detail === 'string' ? detail : '授权书生成失败，请检查资料后重试')
    } finally { setGeneratingAuthorization(false) }
  }

  function submitApplication() {
    Modal.confirm({
      title: data?.application.status === 'NEED_FIX' ? '确认重新提交补充资料？' : '确认提交申请？',
      content: '提交后资料将进入审核流程，除非审核人员要求补件，否则不能修改。',
      okText: '确认提交', cancelText: '继续检查',
      onOk: async () => {
        try {
          const response = await api.post<ApplicationFormData['application']>(`/applications/${id}/submit`)
          setData((current) => current ? { ...current, application: response.data } : current)
          const historyResponse = await api.get<StatusHistory[]>(`/applications/${id}/status-history`)
          setStatusHistory(historyResponse.data)
          message.success('申请已提交')
        } catch (error) {
          if (axios.isAxiosError(error) && Array.isArray(error.response?.data?.detail?.missing_fields)) {
            Modal.error({ title: '资料尚未完整', width: 560, content: <ul>{error.response.data.detail.missing_fields.map((item: string) => <li key={item}>{item}</li>)}</ul> })
          } else message.error(axios.isAxiosError(error) ? error.response?.data?.detail ?? '提交失败' : '提交失败')
          throw error
        }
      },
    })
  }

  if (loading) return <div className="form-loading"><Spin size="large" /></div>
  if (!data) return null

  const completion = Math.round((step / 5) * 100)
  if (data.application.status === 'REGISTERING' || data.application.status === 'COMPLETED') {
    const legal = data.company?.legal_person
    const file = (url: string | undefined, title: string) => url ? <FilePreview url={url} title={title} /> : '--'
    const registrationMaterials = <div className="registration-result-section">
      <div className="section-heading"><Typography.Title level={3}>公司信息</Typography.Title></div>
      <Descriptions bordered column={1} labelStyle={{ width: 260 }}>
        <Descriptions.Item label="公司注册地">{COMPANY_REGION_OPTIONS.find((item) => item.value === data.company?.registration_region)?.label || '--'}</Descriptions.Item>
        <Descriptions.Item label="公司类型">{data.company?.company_type || '--'}</Descriptions.Item>
        <Descriptions.Item label="公司中文名称">{data.company?.company_name || '--'}</Descriptions.Item>
        <Descriptions.Item label="营业执照号 / 企业注册号">{data.company?.register_number || '--'}</Descriptions.Item>
        <Descriptions.Item label="公司成立日期">{data.company?.established_date || '--'}</Descriptions.Item>
        <Descriptions.Item label="公司 / 个体经营注册地址">{data.company?.register_address || '--'}</Descriptions.Item>
        <Descriptions.Item label="公司营业执照">{file(data.company?.license_file, '公司营业执照')}</Descriptions.Item>
        <Descriptions.Item label="企业信用报告">{file(data.company?.credit_report_file, '企业信用报告')}</Descriptions.Item>
      </Descriptions>
      <div className="section-heading result-subheading"><Typography.Title level={3}>法人代表信息</Typography.Title></div>
      <Descriptions bordered column={1} labelStyle={{ width: 260 }}>
        <Descriptions.Item label="法人证件类型">{legal?.certificate_type || '--'}</Descriptions.Item>
        <Descriptions.Item label="法人姓名">{legal?.name_cn || '--'}{legal?.name_en ? ` / ${legal.name_en}` : ''}</Descriptions.Item>
        <Descriptions.Item label="性别">{legal?.gender || '--'}</Descriptions.Item>
        <Descriptions.Item label="联系邮箱">{legal?.contact_email || '--'}</Descriptions.Item>
        <Descriptions.Item label="联系电话">{legal?.contact_phone || '--'}</Descriptions.Item>
        <Descriptions.Item label="法人证件">{file(legal?.front_file, '法人证件')}</Descriptions.Item>
        <Descriptions.Item label="法人签名">{file(legal?.signature_file, '法人签名')}</Descriptions.Item>
      </Descriptions>
      <div className="section-heading result-subheading"><Typography.Title level={3}>店铺后台信息</Typography.Title></div>
      <Descriptions bordered column={1} labelStyle={{ width: 260 }}>
        <Descriptions.Item label="销售平台">{data.store?.platform || '--'}</Descriptions.Item>
        <Descriptions.Item label="店铺名称">{data.store?.store_name || '--'}</Descriptions.Item>
        <Descriptions.Item label="店铺链接">{data.store?.store_url || '--'}</Descriptions.Item>
        <Descriptions.Item label="公司英文名称">{data.store?.company_name_en || '--'}</Descriptions.Item>
        <Descriptions.Item label="注册城市（英文）">{data.store?.register_city_en || '--'}</Descriptions.Item>
        <Descriptions.Item label="邮政编码">{data.store?.postal_code || '--'}</Descriptions.Item>
        <Descriptions.Item label="注册地址（英文）">{data.store?.register_address_en || '--'}</Descriptions.Item>
        <Descriptions.Item label="店铺后台截图">{file(data.store?.screenshot_file, '店铺后台截图')}</Descriptions.Item>
      </Descriptions>
      <div className="section-heading result-subheading"><Typography.Title level={3}>产品信息</Typography.Title><Tag color="blue">共 {products.length} 项</Tag></div>
      {products.length ? products.map((product, index) => <Descriptions className="confirmation-product" key={index} bordered column={1} title={`产品 ${index + 1}`} labelStyle={{ width: 260 }}>
        {data.template.fields.map((field) => <Descriptions.Item key={field.id} label={field.label}>{field.field_type === 'upload' && typeof product[field.field_name] === 'string' && product[field.field_name] ? <FilePreview url={String(product[field.field_name])} title={`产品 ${index + 1} · ${field.label}`} /> : product[field.field_name] ?? '--'}</Descriptions.Item>)}
      </Descriptions>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无产品信息" />}
      <div className="section-heading result-subheading"><Typography.Title level={3}>上传附件</Typography.Title><Tag color="green">{checklistItems.filter((item) => item.fileUrl).length}/{checklistItems.length} 份</Tag></div>
      <Table rowKey="key" pagination={false} dataSource={checklistItems} columns={[
        { title: '模块', dataIndex: 'module' },
        { title: '附件名称', dataIndex: 'materialName' },
        { title: '要求', render: (_, item) => item.required ? <Tag color="red">必填</Tag> : <Tag>选填</Tag> },
        { title: '状态', render: (_, item) => item.fileUrl ? <Tag color="success">已上传</Tag> : <Tag>未上传</Tag> },
        { title: '附件', render: (_, item) => item.fileUrl ? <Space>{item.originalName || item.materialName}<FilePreview url={item.fileUrl} title={item.originalName || item.materialName} trigger="link" /></Space> : '--' },
      ]} />
    </div>
    const registrationInfo = <div className="registration-result-section">
      <div className="section-heading"><Typography.Title level={3}>基础信息</Typography.Title></div>
      <Descriptions bordered column={1} labelStyle={{ width: 260 }}>
        <Descriptions.Item label="注册主体名称">{data.company?.company_name || '--'}</Descriptions.Item>
        <Descriptions.Item label="国家">{data.application.country}</Descriptions.Item>
        <Descriptions.Item label="服务信息">{data.application.service_type}</Descriptions.Item>
      </Descriptions>
      <div className="section-heading result-subheading"><Typography.Title level={3}>证书信息</Typography.Title></div>
      <Descriptions bordered column={1} labelStyle={{ width: 260 }}>
        <Descriptions.Item label="证书">{file(data.application.certificate_file, 'EPR 证书')}</Descriptions.Item>
        <Descriptions.Item label="账单">{file(data.application.invoice_file, 'EPR 账单')}</Descriptions.Item>
        <Descriptions.Item label="文件">{file(data.application.result_file, '下证文件')}</Descriptions.Item>
        <Descriptions.Item label="注册号">{data.application.registration_number || '--'}</Descriptions.Item>
        <Descriptions.Item label="服务截止日期">{data.application.service_expiry_date || '--'}</Descriptions.Item>
      </Descriptions>
    </div>
    return <div className="application-form-page">
      <div className="form-topbar"><Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/applications')}>返回我的递单</Button><div className="form-topbar-summary"><strong>{data.application.application_no}</strong><Tag className="service-tag" color="blue">{data.application.country} · {data.application.service_type}</Tag><Tag color={STATUS_META[data.application.status].color}>{STATUS_META[data.application.status].label}</Tag></div></div>
      <Card className="completed-workspace"><Alert className="status-alert" showIcon type={data.application.status === 'COMPLETED' ? 'success' : 'info'} message={data.application.status === 'COMPLETED' ? '注册服务已完成' : '资料审核已通过，正在执行注册'} description={data.application.status === 'COMPLETED' ? `注册号：${data.application.registration_number || '--'}` : '等待官方下证，注册信息将由工作人员录入并同步至此。'} /><Tabs defaultActiveKey="materials" items={[{ key: 'materials', label: '注册资料', children: registrationMaterials }, { key: 'registration', label: '注册信息', children: registrationInfo }]} /></Card>
    </div>
  }
  return <div className="application-form-page">
    <div className="form-topbar">
      <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/applications')}>返回我的递单</Button>
      <div className="form-topbar-summary">
        <strong>{data.application.application_no}</strong>
        <Tag className="service-tag" color="blue">{data.application.country} · {data.application.service_type}</Tag>
        <Button className="checklist-button" type="link" icon={<ProfileOutlined />} onClick={() => setChecklistOpen(true)}>资料清单</Button>
        <Tag color={STATUS_META[data.application.status].color}>{STATUS_META[data.application.status].label}</Tag>
      </div>
    </div>
    <Card className="form-workspace">
      <aside className="form-sidebar">
        <Typography.Title level={4}>资料填写</Typography.Title>
        <Typography.Text type="secondary">模板版本 v{data.template.version}</Typography.Text>
        <Progress percent={completion} size="small" showInfo={false} />
        <Steps direction="vertical" current={step} onChange={setStep} items={stepItems} />
      </aside>
      <section className="form-main">
        {!editable && <Alert className="status-alert" showIcon type="info" message={`当前状态：${STATUS_META[data.application.status].label}`} description="资料已锁定，可查看但不能修改。" />}
        {data.application.status === 'NEED_FIX' && <Alert className="status-alert" showIcon type="warning" message="请补充或修正资料" description={data.application.review_note || '请根据审核意见完善资料后重新提交。'} />}
        {step === 0 && <>
          <div className="section-heading"><div><Typography.Title level={3}>公司信息</Typography.Title><Typography.Text type="secondary">企业基础资料将长期保存，可在后续递单中复用</Typography.Text></div><Button disabled={!editable} icon={<CopyOutlined />} onClick={openHistory}>资料复用</Button></div>
          <Alert showIcon type="info" message="复用范围" description="仅自动填充公司信息和法人信息，不包含店铺、产品及国家服务材料。" />
          <Form form={companyForm} layout="vertical" className={`detail-form ${!editable ? 'readonly' : ''}`} initialValues={{ registration_region: 'MAINLAND_CHINA' }}>
            <Form.Item name="registration_region" label="公司注册地" rules={[{ required: true }]}>
              <Radio.Group className="region-selector" options={COMPANY_REGION_OPTIONS} optionType="button" onChange={() => companyForm.setFieldValue('company_type', undefined)} />
            </Form.Item>
            <Row gutter={20}>
              <Col xs={24} md={12}><Form.Item name="company_type" label="公司类型" rules={[{ required: true, message: '请选择公司类型' }]}><Select showSearch placeholder="请选择公司类型" options={COMPANY_TYPE_OPTIONS[registrationRegion].map((value) => ({ value, label: value }))} /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="company_name" label="公司中文名称" rules={[{ required: true, message: '请输入公司中文名称' }]}><Input allowClear placeholder="请输入公司中文名称" /></Form.Item></Col>
            </Row>
            <Row gutter={20}>
              <Col xs={24} md={12}><Form.Item name="register_number" label="营业执照号 / 注册号" rules={[{ required: true, message: '请输入营业执照号或注册号' }]}><Input /></Form.Item></Col>
              {(registrationRegion === 'EU' || registrationRegion === 'OTHER') && <Col xs={24} md={12}><Form.Item name="vat_number" label="本国 VAT 税号" rules={[{ required: true, message: '请输入本国 VAT 税号' }]}><Input /></Form.Item></Col>}
              <Col xs={24} md={12}><Form.Item name="established_date" label="公司成立日期" rules={[{ required: true, message: '请选择公司成立日期' }]}><Input type="date" /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="register_address" label="公司 / 个体经营注册地址" rules={[{ required: true, message: '请输入注册地址' }]}><Input /></Form.Item></Col>
            </Row>
            <Divider orientation="left">公司证明文件</Divider>
            {registrationRegion === 'MAINLAND_CHINA' && <Row gutter={20}>
              <Col xs={24} md={12}><Form.Item name="license_file" label="公司营业执照" rules={[{ required: true, message: '请上传公司营业执照' }]}><FileUpload example={EXAMPLE_FILES.license} /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="license_translation_file" label="营业执照翻译件（选填）" extra={<Button type="link" loading={generatingTranslation} disabled={!editable || !companyForm.getFieldValue('license_file')} onClick={() => void generateLicenseTranslation()}>一键生成英文翻译件</Button>}><FileUpload /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="credit_report_file" label="企业信用报告" rules={[{ required: true, message: '请上传企业信用报告' }]}><FileUpload example={EXAMPLE_FILES.creditReport} /></Form.Item></Col>
            </Row>}
            {registrationRegion === 'HONG_KONG' && <Row gutter={20}>
              <Col xs={24} md={12}><Form.Item name="cr_file" label="公司注册证明书 CR" rules={[{ required: true, message: '请上传 CR' }]}><FileUpload /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="br_file" label="商业登记证 BR" rules={[{ required: true, message: '请上传 BR' }]}><FileUpload /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="nnc1_file" label="法团成立表格 NNC1 或周年申报表 NAR1" rules={[{ required: true, message: '请上传 NNC1 或 NAR1' }]}><FileUpload /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="director_index_file" label="董事索引（无 NNC1/NAR1 时补充）"><FileUpload /></Form.Item></Col>
            </Row>}
            {(registrationRegion === 'EU' || registrationRegion === 'OTHER') && <Row gutter={20}>
              <Col xs={24} md={12}><Form.Item name="license_file" label="公司营业执照 / 注册证明" rules={[{ required: true, message: '请上传公司注册证明' }]}><FileUpload /></Form.Item></Col>
            </Row>}
          </Form>
        </>}
        {step === 1 && <>
          <div className="section-heading"><div><Typography.Title level={3}>法人信息</Typography.Title><Typography.Text type="secondary">填写公司法定代表人资料</Typography.Text></div></div>
          {!data.company && <Alert type="warning" showIcon message="请先保存公司信息" />}
          <Form form={legalForm} layout="vertical" className={`detail-form ${!editable ? 'readonly' : ''}`} initialValues={{ certificate_type: 'ID_CARD' }}>
            <Row gutter={20}>
              <Col xs={24} md={12}><Form.Item name="certificate_type" label="法人证件类型" rules={[{ required: true }]}><Radio.Group options={[{ value: 'ID_CARD', label: '身份证' }, { value: 'PASSPORT', label: '护照' }]} /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="gender" label="性别" rules={[{ required: true, message: '请选择性别' }]}><Select options={[{ value: 'MALE', label: '男' }, { value: 'FEMALE', label: '女' }, { value: 'OTHER', label: '其他' }]} /></Form.Item></Col>
            </Row>
            <Row gutter={20}>
              <Col xs={24} md={12}><Form.Item name="name_cn" label="法人代表中文名" rules={[{ required: true, message: '请输入法人代表中文名' }]}><Input /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="name_en" label="法人代表拼音名（例：San Zhang）" rules={[{ required: true, message: '请输入法人代表拼音名' }]}><Input /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="contact_email" label="公司联系人邮箱" rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}><Input /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="contact_phone" label="公司联系人电话" rules={[{ required: true, message: '请输入联系人电话' }]}><Input /></Form.Item></Col>
            </Row>
            <Divider orientation="left">证件与签名</Divider>
            <Row gutter={20}>
              <Col xs={24} md={12}><Form.Item name="front_file" label={certificateType === 'PASSPORT' ? '护照资料页' : '法人身份证－人像面'} rules={[{ required: true, message: '请上传证件资料' }]}><FileUpload purpose="identity" accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx" hint="PDF、JPG、JPEG、PNG、WEBP、DOC、DOCX，最大 20MB" example={certificateType === 'ID_CARD' ? EXAMPLE_FILES.identityFront : undefined} /></Form.Item></Col>
              {certificateType === 'ID_CARD' && <Col xs={24} md={12}><Form.Item name="back_file" label="法人身份证－国徽面" rules={[{ required: true, message: '请上传身份证国徽面' }]}><FileUpload purpose="identity" accept=".jpg,.jpeg,.png,.webp" hint="JPG、JPEG、PNG、WEBP，最大 20MB" example={EXAMPLE_FILES.identityBack} /></Form.Item></Col>}
              <Col xs={24} md={12}><Form.Item name="signature_file" label="法人代表签名（拼音）" rules={[{ required: true, message: '请上传法人签名' }]}><FileUpload purpose="signature" accept=".jpg,.jpeg,.png,.webp" hint="JPG、JPEG、PNG、WEBP，最大 20MB" example={EXAMPLE_FILES.signature} /></Form.Item></Col>
            </Row>
          </Form>
        </>}
        {step === 2 && <>
          <div className="section-heading"><div><Typography.Title level={3}>店铺信息</Typography.Title><Typography.Text type="secondary">店铺随国家和销售渠道变化，每份递单均需重新填写</Typography.Text></div></div>
          <Alert type="warning" showIcon message="店铺信息不参与资料复用" />
          <Form form={storeForm} layout="vertical" className={`detail-form ${!editable ? 'readonly' : ''}`}>
            <Row gutter={20}>
              <Col xs={24} md={12}><Form.Item name="platform" label="销售平台" rules={[{ required: true, message: '请选择销售平台' }]}><Select showSearch placeholder="请选择销售平台" options={['Amazon', 'eBay', 'Shopify', 'TikTok Shop', '独立站', '其他'].map((value) => ({ value, label: value }))} /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="store_url" label="店铺链接" rules={[{ required: true, type: 'url', message: '请输入有效店铺链接' }]}><Input placeholder="https://" /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="company_name_en" label="公司名称（英文）" rules={[{ required: true, message: '请输入英文公司名称' }]}><Input /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="register_city_en" label="公司 / 个体经营注册城市（英文）" rules={[{ required: true, message: '请输入英文城市' }]}><Input /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="postal_code" label="公司注册地邮编" rules={[{ required: true, message: '请输入邮编' }]}><Input /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="register_address_en" label="公司 / 个体经营注册地址（英文）" rules={[{ required: true, message: '请输入英文注册地址' }]}><Input /></Form.Item></Col>
            </Row>
            <Form.Item name="screenshot_file" label="店铺后台截图" rules={[{ required: true, message: '请上传店铺后台截图' }]}><FileUpload purpose="store_screenshot" accept=".jpg,.jpeg,.png,.webp" hint="JPG、JPEG、PNG、WEBP，最大 2MB" /></Form.Item>
          </Form>
        </>}
        {step === 3 && <>
          <div className="section-heading"><div><Typography.Title level={3}>产品信息</Typography.Title><Typography.Text type="secondary">字段由 {data.application.country} + {data.application.service_type} 模板动态生成</Typography.Text></div>{editable && <Button type="primary" icon={<PlusOutlined />} onClick={() => setProducts((current) => [...current, {}])}>添加产品</Button>}</div>
          {!products.length ? <Empty description="请添加产品" /> : products.map((product, index) => <Card key={index} size="small" className="product-card" title={`产品 ${index + 1}`} extra={editable ? <Button danger type="text" icon={<DeleteOutlined />} onClick={() => setProducts((current) => current.filter((_, i) => i !== index))}>删除</Button> : null}>
            <Row gutter={18}>{data.template.fields.map((field) => <Col xs={24} md={12} key={field.id}><Form.Item label={field.label} required={field.required}><div onChange={() => undefined}><DynamicFieldControl disabled={!editable} field={field} value={product[field.field_name]} onChange={(value) => updateProduct(index, field.field_name, value)} /></div></Form.Item></Col>)}</Row>
          </Card>)}
        </>}
        {step === 4 && <>
          <div className="section-heading"><div><Typography.Title level={3}>材料上传</Typography.Title><Typography.Text type="secondary">根据公司注册地、法人证件类型及 {data.application.country} · {data.application.service_type} 服务要求生成</Typography.Text></div></div>
          <Table rowKey="key" pagination={false} dataSource={checklistItems} columns={[
            { title: '模块', dataIndex: 'module' },
            { title: '材料名称', dataIndex: 'materialName' },
            { title: '要求', render: (_, item) => item.required ? <Tag color="red">必填</Tag> : <Tag>选填</Tag> },
            { title: '文件格式', dataIndex: 'fileType' },
            { title: '上传状态', render: (_, item) => item.fileUrl ? <Tag color={item.requirementId ? 'success' : 'blue'}>{item.requirementId ? '已上传' : '已同步'}</Tag> : <Tag>未上传</Tag> },
            { title: '操作', render: (_, item) => <Space size={0}>
              {item.fileUrl && <FilePreview url={item.fileUrl} title={item.originalName || item.materialName} trigger="link" />}
              {data.application.country === 'Germany' && data.application.service_type === 'WEEE' && /授权书|授权委托书|Vollmacht/i.test(item.materialName) && <Button type="link" icon={<DownloadOutlined />} loading={generatingAuthorization} onClick={() => void generateAuthorization()}>生成授权书</Button>}
              {item.requirementId
                ? <Upload disabled={!editable} showUploadList={false} accept=".pdf,.jpg,.jpeg,.png" customRequest={async ({ file, onSuccess, onError }) => { try { await uploadMaterial(item.requirementId!, file as File); onSuccess?.({}) } catch (e) { onError?.(e as Error) } }}><Button disabled={!editable} type="link" icon={<CloudUploadOutlined />}>{item.fileUrl ? '重新上传' : '上传'}</Button></Upload>
                : editable && <Button type="link" onClick={() => setStep(item.module === '公司信息' ? 0 : 1)}>{item.fileUrl ? '更换' : '去上传'}</Button>}
            </Space> },
          ]} />
        </>}
        {step === 5 && <Confirmation data={data} products={products} materials={checklistItems} statusHistory={statusHistory} />}
        <div className="form-actions"><Button disabled={step === 0} onClick={() => setStep((value) => value - 1)}>上一步</Button><Space>{editable && step < 5 && <Button icon={<SaveOutlined />} loading={saving} onClick={() => void saveCurrent(false)}>保存</Button>}{editable && step < 5 && <Button type="primary" loading={saving} onClick={() => void saveCurrent(true)}>保存并下一步</Button>}{editable && step === 5 && <Button type="primary" icon={<FileDoneOutlined />} onClick={submitApplication}>{data.application.status === 'NEED_FIX' ? '重新提交' : '提交申请'}</Button>}{!editable && <Button type="primary" onClick={() => navigate('/applications')}>返回我的递单</Button>}</Space></div>
      </section>
    </Card>
    <Modal title="选择历史企业资料" open={historyOpen} onCancel={() => setHistoryOpen(false)} footer={null} width={760}>
      <Alert type="warning" showIcon message="复用公司与法人信息时，已上传的对应证明材料会自动同步；店铺、产品及服务专属材料仍需填写" />
      <List className="history-list" dataSource={history} locale={{ emptyText: '暂无可复用企业资料' }} renderItem={(company) => <List.Item actions={[<Button type="primary" key="reuse" onClick={() => reuseCompany(company)}>确认复用</Button>]}><List.Item.Meta title={company.company_name} description={`${COMPANY_REGION_OPTIONS.find((item) => item.value === company.registration_region)?.label || '未分类'} · ${company.register_number || '无注册号'}`} /></List.Item>} />
    </Modal>
    <Modal
      className="material-checklist-modal"
      title={<Space><ProfileOutlined /><span>资料准备清单</span></Space>}
      open={checklistOpen}
      onCancel={() => setChecklistOpen(false)}
      width={980}
      footer={<Button type="primary" onClick={() => setChecklistOpen(false)}>我知道了</Button>}
    >
      <Alert
        type="info"
        showIcon
        message={`${data.application.country} · ${data.application.service_type}`}
        description={`以下为当前服务模板 v${data.template.version} 的资料要求，请优先准备必填资料。`}
      />
      <Table
        className="material-checklist-table"
        rowKey="key"
        pagination={false}
        scroll={{ y: 470 }}
        dataSource={checklistItems}
        columns={[
          { title: '模块', dataIndex: 'module', width: 110 },
          { title: '材料名称', dataIndex: 'materialName', width: 190 },
          { title: '是否必填', width: 100, render: (_, item) => item.required ? <Tag color="red">必填</Tag> : <Tag>选填</Tag> },
          { title: '材料要求', render: (_, item) => <div><div>文件格式：{item.fileType}</div><Typography.Text type="secondary">{item.description}</Typography.Text></div> },
          { title: '准备状态', width: 110, render: (_, item) => item.fileUrl ? <Tag color="success">已准备</Tag> : <Tag>未准备</Tag> },
          { title: '预览', width: 105, render: (_, item) => item.fileUrl ? <FilePreview url={item.fileUrl} title={item.originalName || item.materialName} trigger="link" /> : <MaterialExample materialName={item.materialName} /> },
        ]}
      />
    </Modal>
  </div>
}

function materialModule(name: string) {
  if (/法人|身份证|护照|签名/.test(name)) return '法人信息'
  if (/店铺|平台/.test(name)) return '店铺信息'
  if (/产品|商品|SKU|品牌/.test(name)) return '产品信息'
  if (/营业执照|信用报告|注册证明|商业登记|NNC1|NAR1|董事|公司/.test(name)) return '公司信息'
  return '服务材料'
}

function isConditionalIdentityMaterial(name: string) {
  return /营业执照|信用报告|注册证明|商业登记|NNC1|NAR1|董事索引|法人|身份证|护照|签名/.test(name)
}

function DynamicFieldControl({ field, value, onChange, disabled }: { field: DynamicField; value: string | number | undefined; onChange: (value: string | number | null) => void; disabled?: boolean }) {
  if (field.field_type === 'number') return <InputNumber disabled={disabled} value={value as number | undefined} min={0} style={{ width: '100%' }} onChange={onChange} placeholder={`请输入${field.label}`} />
  if (field.field_type === 'select') return <Select disabled={disabled} value={value as string | undefined} onChange={onChange} placeholder={`请选择${field.label}`} options={field.options?.map((item) => ({ value: item, label: item }))} />
  return <Input disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)} placeholder={`请输入${field.label}`} />
}

function Confirmation({ data, products, materials, statusHistory }: { data: ApplicationFormData; products: Record<string, string | number | undefined>[]; materials: ChecklistItem[]; statusHistory: StatusHistory[] }) {
  return <>
    <div className="section-heading"><div><Typography.Title level={3}>确认提交</Typography.Title><Typography.Text type="secondary">请核对所有资料，提交后将进入审核流程。</Typography.Text></div></div>
    <Descriptions bordered column={2} title="申请信息"><Descriptions.Item label="申请编号">{data.application.application_no}</Descriptions.Item><Descriptions.Item label="国家 / 服务">{data.application.country} / {data.application.service_type}</Descriptions.Item></Descriptions>
    <Divider />
    <Descriptions bordered column={2} title="公司与法人"><Descriptions.Item label="公司名称">{data.company?.company_name || '未填写'}</Descriptions.Item><Descriptions.Item label="注册地类型">{COMPANY_REGION_OPTIONS.find((item) => item.value === data.company?.registration_region)?.label || '未填写'}</Descriptions.Item><Descriptions.Item label="注册号">{data.company?.register_number || '未填写'}</Descriptions.Item><Descriptions.Item label="法人姓名">{data.company?.legal_person?.name_cn || '未填写'}</Descriptions.Item><Descriptions.Item label="联系人邮箱">{data.company?.legal_person?.contact_email || '未填写'}</Descriptions.Item><Descriptions.Item label="联系人电话">{data.company?.legal_person?.contact_phone || '未填写'}</Descriptions.Item></Descriptions>
    <Divider />
    <Descriptions bordered column={2} title="店铺信息"><Descriptions.Item label="平台">{data.store?.platform || '未填写'}</Descriptions.Item><Descriptions.Item label="店铺链接">{data.store?.store_url || '未填写'}</Descriptions.Item><Descriptions.Item label="英文公司名">{data.store?.company_name_en || '未填写'}</Descriptions.Item><Descriptions.Item label="注册城市">{data.store?.register_city_en || '未填写'}</Descriptions.Item></Descriptions>
    <Divider />
    <div className="confirmation-section-title"><Typography.Title level={5}>产品信息</Typography.Title><Tag color="blue">共 {products.length} 项</Tag></div>
    {products.length ? products.map((product, index) => <Descriptions className="confirmation-product" key={index} bordered size="small" column={2} title={`产品 ${index + 1}`}>
      {data.template.fields.map((field) => <Descriptions.Item key={field.id} label={field.label}>
        {field.field_type === 'upload' && typeof product[field.field_name] === 'string' && product[field.field_name]
          ? <FilePreview url={String(product[field.field_name])} title={`产品 ${index + 1} · ${field.label}`} trigger="link" />
          : product[field.field_name] ?? '未填写'}
      </Descriptions.Item>)}
    </Descriptions>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无产品信息" />}
    <Divider />
    <div className="confirmation-section-title"><Typography.Title level={5}>上传材料</Typography.Title><Tag color="green">{materials.filter((item) => item.fileUrl).length}/{materials.length} 份</Tag></div>
    <Table size="small" rowKey="key" pagination={false} dataSource={materials} columns={[
      { title: '模块', dataIndex: 'module' },
      { title: '材料名称', dataIndex: 'materialName' },
      { title: '要求', render: (_, item) => item.required ? <Tag color="red">必填</Tag> : <Tag>选填</Tag> },
      { title: '状态', render: (_, item) => item.fileUrl ? <Tag color={item.requirementId ? 'success' : 'blue'}>{item.requirementId ? '已上传' : '已同步'}</Tag> : <Tag>未上传</Tag> },
      { title: '文件', render: (_, item) => item.fileUrl ? <Space size={4}><Typography.Text ellipsis={{ tooltip: item.originalName }} className="confirmation-file-name">{item.originalName}</Typography.Text><FilePreview url={item.fileUrl} title={item.originalName || item.materialName} trigger="link" /></Space> : <span className="muted">—</span> },
    ]} />
    {statusHistory.length > 0 && <><Divider /><Typography.Title level={5}>状态记录</Typography.Title><Timeline items={statusHistory.map((item) => ({ color: STATUS_META[item.to_status as ApplicationStatus]?.color, children: <div><strong>{STATUS_META[item.to_status as ApplicationStatus]?.label || item.to_status}</strong><div className="muted">{new Date(item.created_time).toLocaleString()} · {item.operator_name}</div>{item.note && <div>{item.note}</div>}</div> }))} /></>}
  </>
}

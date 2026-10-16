import { SearchOutlined, ShoppingCartOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Input, InputNumber, message, Modal, Radio, Select, Tag, Typography } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import WeeeCategoryConfigurator from '../components/WeeeCategoryConfigurator'
import { calculateServicePrice, catalog } from '../serviceCatalog'
import type { CatalogService } from '../serviceCatalog'
import type { PortalCatalogService, ProductCategorySelection } from '../types'

const countries = ['全部', '德国', '法国', '英国', '丹麦', '加拿大', '匈牙利', '卢森堡', '奥地利', '希腊', '意大利', '捷克', '斯洛伐克', '比利时', '波兰', '爱尔兰', '瑞典', '立陶宛', '罗马尼亚', '芬兰', '荷兰', '葡萄牙', '西班牙']
const productTypes = ['全部', 'WEEE', '电池法', '包装法', '一次性塑料']
const serviceTypes = ['全部', '注册', '增值服务', '转代理', '续费', '注销']

function FilterRow({ label, options, value, onChange }: { label: string; options: string[]; value: string; onChange: (v: string) => void }) {
  return <div className="catalog-filter-row"><strong>{label}</strong><div>{options.map(option => <button key={option} className={option === value ? 'selected' : ''} onClick={() => onChange(option)}>{option}</button>)}</div></div>
}

async function addSimpleServiceToCart(service: CatalogService) {
  try {
    await api.post('/portal/cart', { service_id: service.id })
    window.dispatchEvent(new Event('epr-cart-updated'))
    message.success('已加入购物车')
  } catch { message.error('加入购物车失败，请稍后重试') }
}

export default function PurchaseServicesPage({ renewalOnly = false }: { renewalOnly?: boolean }) {
  const navigate = useNavigate()
  const [catalogItems, setCatalogItems] = useState<CatalogService[]>(catalog)
  const [country, setCountry] = useState('全部')
  const [type, setType] = useState('全部')
  const [serviceType, setServiceType] = useState(renewalOnly ? '续费' : '全部')
  const [query, setQuery] = useState('')
  const [selectedService, setSelectedService] = useState<CatalogService>()
  const [modalAction, setModalAction] = useState<'purchase'|'cart'>('purchase')
  const [serviceYear, setServiceYear] = useState('')
  const [packageType, setPackageType] = useState('')
  const [productConfigurations, setProductConfigurations] = useState<ProductCategorySelection[]>([])
  const [quantity, setQuantity] = useState(1)
  const [creatingOrder, setCreatingOrder] = useState(false)
  useEffect(() => { api.get<PortalCatalogService[]>('/portal/catalog').then(({ data }) => setCatalogItems(data.map(item => ({ id: item.id, country: item.country, type: item.product_type, serviceType: item.service_type, title: item.title, description: item.description, price: item.price, additionalCategoryPrice:item.additional_category_price, additionalBrandPrice:item.additional_brand_price, unit: item.unit, color: item.color, code: item.country_code, reportingFrequency: item.reporting_frequency, serviceYears: item.service_years, subjectTypes: item.subject_types, packageTypes: item.package_types, productCategories:item.product_categories, purchaseNotes: item.purchase_notes })))).catch(() => undefined) }, [])
  function openServiceOptions(service: CatalogService, action:'purchase'|'cart') {
    setSelectedService(service)
    setModalAction(action)
    setServiceYear(service.serviceYears[0] || '')
    setPackageType(service.packageTypes[0] || '')
    setProductConfigurations(service.productCategories.length ? [{ category: '', brands: [''] }] : [])
    setQuantity(1)
  }
  async function createOrder() {
    if (!selectedService) return
    if (selectedService.productCategories.length && (!productConfigurations.length || productConfigurations.some(item => !item.category || !item.brands.length || item.brands.some(brand=>!brand.trim())))) { message.warning('请完整选择 WEEE 类别，并在每个品牌框中填写品牌'); return }
    setCreatingOrder(true)
    try {
      const { data } = await api.post<{ id: number }>('/portal/orders', {
        service_id: selectedService.id,
        service_year: serviceYear,
        package_type: packageType,
        product_configurations: productConfigurations,
        quantity,
      })
      navigate(`/orders/${data.id}/confirm`)
    } catch { message.error('订单创建失败，请稍后重试') }
    finally { setCreatingOrder(false) }
  }
  async function addConfiguredToCart() {
    if (!selectedService) return
    if (selectedService.productCategories.length && (!productConfigurations.length || productConfigurations.some(item => !item.category || !item.brands.length || item.brands.some(brand=>!brand.trim())))) { message.warning('请完整选择 WEEE 类别，并在每个品牌框中填写品牌'); return }
    setCreatingOrder(true)
    try {
      await api.post('/portal/cart', { service_id:selectedService.id, service_year:serviceYear, package_type:packageType, product_configurations:productConfigurations, quantity })
      window.dispatchEvent(new Event('epr-cart-updated'))
      message.success('所选参数已保存并加入购物车')
      setSelectedService(undefined)
    } catch { message.error('加入购物车失败，请检查商品参数') }
    finally { setCreatingOrder(false) }
  }
  const services = useMemo(() => catalogItems.filter(item => (country === '全部' || item.country === country) && (type === '全部' || item.type === type) && (serviceType === '全部' || item.serviceType === serviceType) && [item.title, item.description].some(v => v.toLowerCase().includes(query.toLowerCase()))), [catalogItems, country, type, serviceType, query])
  const currentUnitPrice = selectedService ? calculateServicePrice(selectedService, productConfigurations) : 0
  const selectedCategoryCount = productConfigurations.filter(item => item.category).length
  const selectedBrandCount = productConfigurations.reduce((sum, item) => sum + item.brands.filter(brand=>brand.trim()).length, 0)
  return <div className="page-container catalog-page">
    <div className="page-heading"><div><Typography.Title level={2}>{renewalOnly ? '续费服务' : '购买服务'}</Typography.Title><Typography.Text type="secondary">按国家、商品类型和服务类型筛选适合的 EPR 合规服务</Typography.Text></div></div>
    <Card className="catalog-filter-card">
      <FilterRow label="国家" options={countries} value={country} onChange={setCountry} />
      <FilterRow label="商品类型" options={productTypes} value={type} onChange={setType} />
      <div className="catalog-filter-with-search"><FilterRow label="服务类型" options={serviceTypes} value={serviceType} onChange={setServiceType} /><Input allowClear prefix={<SearchOutlined />} placeholder="搜索服务名称" value={query} onChange={e => setQuery(e.target.value)} /></div>
    </Card>
    <div className="catalog-heading"><div><strong>全部服务</strong><span>共 {services.length} 项</span></div><Select defaultValue="综合排序" bordered={false} options={[{ value: '综合排序', label: '综合排序' }, { value: '价格升序', label: '价格升序' }]} /></div>
    <div className="service-product-grid">
      {services.map(service => <Card key={service.id} className="service-product-card" styles={{ body: { padding: 16 } }}>
        <div className="service-product-visual"><span style={{ background: service.color }}>{service.code}</span><strong>{service.country} {service.type}</strong><Tag color={service.serviceType === '注册' ? 'blue' : service.serviceType === '增值服务' ? 'orange' : 'purple'}>{service.serviceType}服务</Tag></div>
        <h3>{service.title}</h3><p>{service.description}</p><div className="service-price"><small>¥</small>{service.price.toLocaleString()}<em>/{service.unit}起</em></div>
        <div className="service-actions"><Button type="primary" onClick={() => openServiceOptions(service,'purchase')}>立即购买</Button><Button icon={<ShoppingCartOutlined />} onClick={() => service.productCategories.length ? openServiceOptions(service,'cart') : void addSimpleServiceToCart(service)} aria-label="加入购物车" /></div>
      </Card>)}
      {!services.length && <div className="catalog-empty">暂未找到匹配的服务</div>}
    </div>
    <Modal className="service-attribute-modal" width={780} title={modalAction==='cart'?'选择参数后加入购物车':'请选择商品属性'} open={Boolean(selectedService)} onCancel={() => setSelectedService(undefined)} footer={null} destroyOnClose>
      {selectedService && <>
        <div className="purchase-service-summary">
          <span style={{ background: selectedService.color }}>{selectedService.code}</span>
          <div><h3>{selectedService.title}</h3><p>{selectedService.description}</p><strong>¥{selectedService.price.toLocaleString()} <small>/{selectedService.unit}起</small></strong></div>
        </div>
        <div className="purchase-attributes">
          <div><label>国家</label><strong>{selectedService.country}</strong></div>
          <div><label>服务类型</label><strong>{selectedService.type} · {selectedService.serviceType}</strong></div>
          <div><label>申报频率</label><strong>{selectedService.reportingFrequency}（平台配置）</strong></div>
          <div><label>服务年度</label><Radio.Group optionType="button" buttonStyle="solid" value={serviceYear} onChange={e => setServiceYear(e.target.value)} options={selectedService.serviceYears} /></div>
          {selectedService.productCategories.length > 0 && <div><label>品类数量</label><Radio.Group optionType="button" buttonStyle="solid" value={packageType} onChange={e => { setPackageType(e.target.value); setProductConfigurations([{ category: '', brands: [''] }]) }} options={selectedService.packageTypes} /></div>}
          <div><label>购买数量</label><InputNumber min={1} max={99} value={quantity} onChange={value => setQuantity(value || 1)} /></div>
        </div>
        {selectedService.productCategories.length > 0 && <><WeeeCategoryConfigurator categories={selectedService.productCategories} mode={packageType} value={productConfigurations} onChange={setProductConfigurations} /><Alert type="info" showIcon message="德国 WEEE 价格明细" description={`基础价 ¥${selectedService.price.toLocaleString()}（首个类别含 1 个品牌）${Math.max(selectedCategoryCount-1,0)?` + 新增类别 ${Math.max(selectedCategoryCount-1,0)} × ¥${selectedService.additionalCategoryPrice}（每个类别含 1 个品牌）`:''}${Math.max(selectedBrandCount-selectedCategoryCount,0)?` + 新增品牌 ${Math.max(selectedBrandCount-selectedCategoryCount,0)} × ¥${selectedService.additionalBrandPrice}`:''}`} /></>}
        <Alert className="purchase-notes" type="warning" showIcon message="购买须知" description={<ol>{selectedService.purchaseNotes.map(note => <li key={note}>{note}</li>)}</ol>} />
        <div className="purchase-total"><span>服务金额（单价 ¥{currentUnitPrice.toLocaleString()} × {quantity}）</span><strong>¥ {(currentUnitPrice * quantity).toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong></div>
        <div className="purchase-submit"><Button type="primary" size="large" loading={creatingOrder} onClick={modalAction==='cart'?addConfiguredToCart:createOrder}>{modalAction==='cart'?'确认参数并加入购物车':'立即购买'}</Button></div>
      </>}
    </Modal>
  </div>
}

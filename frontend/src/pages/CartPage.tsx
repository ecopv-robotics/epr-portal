import { DeleteOutlined, ShoppingOutlined } from '@ant-design/icons'
import { Button, Card, Empty, message, Space, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import WeeeCategoryConfigurator from '../components/WeeeCategoryConfigurator'
import { calculateServicePrice } from '../serviceCatalog'
import type { CartItem, ProductCategorySelection } from '../types'

type CartSelection = Record<number, { service_year: string; package_type: string; product_configurations: ProductCategorySelection[]; quantity: number }>

export default function CartPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<CartItem[]>([])
  const [loading, setLoading] = useState(true)
  const [checkingOut, setCheckingOut] = useState(false)
  const [selection, setSelection] = useState<CartSelection>({})
  const load = () => api.get<CartItem[]>('/portal/cart').then(({ data }) => { setItems(data); setSelection(Object.fromEntries(data.map(item => [item.id, { service_year: item.service_year||item.service.service_years[0] || '', package_type:item.package_type||item.service.package_types[0]||'',product_configurations:item.product_configurations.length?item.product_configurations:(item.service.product_categories.length?[{category:'',brands:['']}]:[]), quantity: item.quantity }])) ) }).catch(() => message.error('购物车加载失败')).finally(() => setLoading(false))
  useEffect(() => { void load() }, [])
  const itemUnitPrice = (item:CartItem) => calculateServicePrice({price:item.service.price,productCategories:item.service.product_categories,additionalCategoryPrice:item.service.additional_category_price,additionalBrandPrice:item.service.additional_brand_price}, selection[item.id]?.product_configurations || [])
  const total = useMemo(() => items.reduce((sum, item) => sum + itemUnitPrice(item) * (selection[item.id]?.quantity || item.quantity), 0), [items, selection])
  async function remove(id: number) { try { await api.delete(`/portal/cart/${id}`); await load(); window.dispatchEvent(new Event('epr-cart-updated')) } catch { message.error('移除失败') } }
  async function checkout() {
    if(items.some(item=>item.service.product_categories.length&&selection[item.id]?.product_configurations.some(config=>!config.category||!config.brands.length||config.brands.some(brand=>!brand.trim())))){message.warning('请完整配置德国 WEEE 的类别和每个品牌框');return}
    setCheckingOut(true)
    try {
      const { data } = await api.post<{ id: number }[]>('/portal/cart/checkout', { items: items.map(item => ({ cart_item_id: item.id, ...selection[item.id] })) })
      window.dispatchEvent(new Event('epr-cart-updated'))
      message.success(`已生成 ${data.length} 个待付款订单，可联系销售申请打包优惠后再付款`)
      navigate(data.length === 1 ? `/orders/${data[0].id}/confirm` : '/account/orders')
    } catch { message.error('购物车结算失败，请检查服务年度和数量') }
    finally { setCheckingOut(false) }
  }
  const columns: ColumnsType<CartItem> = [
    { title: '服务名称', render: (_, r) => <div><strong>{r.service.title}</strong><div className="muted">{r.service.description}</div></div> },
    { title: '国家/地区', render: (_, r) => r.service.country }, { title: '商品类型', render: (_, r) => r.service.product_type }, { title: '服务类型', render: (_, r) => r.service.service_type },
    { title: '服务年度', render: (_, r) => selection[r.id]?.service_year || '—' },
    { title:'品类数量',render:(_,r)=>r.service.product_categories.length?(selection[r.id]?.package_type||'—'):'—' },
    { title: '数量', render: (_, r) => selection[r.id]?.quantity || r.quantity },
    { title: '价格', render: (_, r) => <div><strong className="cart-price">¥{itemUnitPrice(r).toLocaleString()} / {r.service.unit}</strong>{r.service.product_categories.length>0&&<div className="muted">基础 ¥{r.service.price.toLocaleString()}；新增类别 +¥{r.service.additional_category_price}（含 1 品牌）；同类别新增品牌 +¥{r.service.additional_brand_price}</div>}</div> },
    { title: '操作', render: (_, r) => <Button type="link" danger icon={<DeleteOutlined />} onClick={() => void remove(r.id)}>移除</Button> },
  ]
  return <div className="page-container"><div className="page-heading"><div><Typography.Title level={2}>购物车</Typography.Title><Typography.Text type="secondary">查看已选服务和参数后直接结算；如需修改，请移除后重新选择加入购物车</Typography.Text></div></div><Card className="data-card"><Table rowKey="id" loading={loading} columns={columns} dataSource={items} pagination={false} locale={{ emptyText: <Empty image={<ShoppingOutlined />} description="购物车空空如也"><Button type="primary" onClick={() => navigate('/services')}>去购买</Button></Empty> }} expandable={{expandedRowRender:item=>item.service.product_categories.length?<WeeeCategoryConfigurator readOnly categories={item.service.product_categories} mode={selection[item.id]?.package_type||'一品一类'} value={selection[item.id]?.product_configurations||[]} onChange={()=>undefined}/>:null,rowExpandable:item=>item.service.product_categories.length>0}} />{items.length > 0 && <div className="cart-summary"><span>共 {items.length} 项服务</span><Space><Typography.Text>标准价合计：<strong>¥{total.toLocaleString()}</strong></Typography.Text><Button type="primary" size="large" loading={checkingOut} onClick={() => void checkout()}>直接结算</Button></Space></div>}</Card></div>
}

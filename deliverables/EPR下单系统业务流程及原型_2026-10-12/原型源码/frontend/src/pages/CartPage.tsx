import { DeleteOutlined, ShoppingOutlined } from '@ant-design/icons'
import { Button, Card, Empty, InputNumber, message, Select, Space, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import type { CartItem } from '../types'

type CartSelection = Record<number, { service_year: string; quantity: number }>

export default function CartPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<CartItem[]>([])
  const [loading, setLoading] = useState(true)
  const [checkingOut, setCheckingOut] = useState(false)
  const [selection, setSelection] = useState<CartSelection>({})
  const load = () => api.get<CartItem[]>('/portal/cart').then(({ data }) => { setItems(data); setSelection(Object.fromEntries(data.map(item => [item.id, { service_year: item.service.service_years[0] || '', quantity: item.quantity }])) ) }).catch(() => message.error('购物车加载失败')).finally(() => setLoading(false))
  useEffect(() => { void load() }, [])
  const total = useMemo(() => items.reduce((sum, item) => sum + item.service.price * (selection[item.id]?.quantity || item.quantity), 0), [items, selection])
  async function remove(id: number) { try { await api.delete(`/portal/cart/${id}`); await load(); window.dispatchEvent(new Event('epr-cart-updated')) } catch { message.error('移除失败') } }
  async function checkout() {
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
    { title: '服务年度', render: (_, r) => <Select style={{ minWidth: 150 }} value={selection[r.id]?.service_year} options={r.service.service_years.map(value => ({ value, label: value }))} onChange={value => setSelection(current => ({ ...current, [r.id]: { ...(current[r.id] || { quantity: 1 }), service_year: value } }))} /> },
    { title: '数量', render: (_, r) => <InputNumber min={1} max={99} value={selection[r.id]?.quantity || 1} onChange={value => setSelection(current => ({ ...current, [r.id]: { ...(current[r.id] || { service_year: r.service.service_years[0] || '' }), quantity: value || 1 } }))} /> },
    { title: '价格', render: (_, r) => <strong className="cart-price">¥{r.service.price.toLocaleString()} / {r.service.unit}</strong> },
    { title: '操作', render: (_, r) => <Button type="link" danger icon={<DeleteOutlined />} onClick={() => void remove(r.id)}>移除</Button> },
  ]
  return <div className="page-container"><div className="page-heading"><div><Typography.Title level={2}>购物车</Typography.Title><Typography.Text type="secondary">选择服务年度和数量后可直接结算；多个订单可由销售申请打包优惠</Typography.Text></div></div><Card className="data-card"><Table rowKey="id" loading={loading} columns={columns} dataSource={items} pagination={false} locale={{ emptyText: <Empty image={<ShoppingOutlined />} description="购物车空空如也"><Button type="primary" onClick={() => navigate('/services')}>去购买</Button></Empty> }} />{items.length > 0 && <div className="cart-summary"><span>共 {items.length} 项服务</span><Space><Typography.Text>标准价合计：<strong>¥{total.toLocaleString()}</strong></Typography.Text><Button type="primary" size="large" loading={checkingOut} onClick={() => void checkout()}>直接结算</Button></Space></div>}</Card></div>
}

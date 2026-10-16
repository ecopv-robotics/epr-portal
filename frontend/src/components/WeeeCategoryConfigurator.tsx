import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Input, Select, Space } from 'antd'
import type { ProductCategorySelection } from '../types'

type Props = {
  categories: string[]
  mode: string
  value: ProductCategorySelection[]
  onChange: (value: ProductCategorySelection[]) => void
  readOnly?: boolean
}

export default function WeeeCategoryConfigurator({ categories, mode, value, onChange, readOnly = false }: Props) {
  const rows = value.length ? value : [{ category: '', brands: [''] }]
  const update = (index: number, patch: Partial<ProductCategorySelection>) => {
    onChange(rows.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row))
  }
  const add = () => onChange([...rows, { category: '', brands: [''] }])
  const remove = (index: number) => onChange(rows.filter((_, rowIndex) => rowIndex !== index))
  const updateBrand = (rowIndex:number, brandIndex:number, brand:string) => update(rowIndex, { brands: rows[rowIndex].brands.length ? rows[rowIndex].brands.map((item,index)=>index===brandIndex?brand:item) : [brand] })
  const addBrand = (rowIndex:number) => update(rowIndex, { brands: [...rows[rowIndex].brands, ''] })
  const removeBrand = (rowIndex:number, brandIndex:number) => update(rowIndex, { brands: rows[rowIndex].brands.filter((_,index)=>index!==brandIndex) })
  return <div className="weee-configurator">
    <div className="weee-config-header"><span>序号</span><span>产品类别</span><span>品牌（一个品牌一个框）</span><span>操作</span></div>
    {rows.map((row, index) => <div className="weee-config-row" key={index}>
      <strong>{index + 1}</strong>
      {readOnly ? <strong>{row.category || '—'}</strong> : <Select showSearch placeholder="请选择 WEEE 类别" value={row.category || undefined} options={categories.map(category => ({ value: category, label: category, disabled: rows.some((item, rowIndex) => rowIndex !== index && item.category === category) }))} onChange={category => update(index, { category })} />}
      <div className="weee-brand-list">
        {(row.brands.length ? row.brands : ['']).map((brand,brandIndex)=>readOnly
          ? <span className="weee-brand-value" key={brandIndex}>{brand || '—'}</span>
          : <div className="weee-brand-row" key={brandIndex}>
            <Input placeholder={brandIndex===0?'请输入品牌（该类别首个品牌已包含）':'请输入新增品牌（+¥300）'} value={brand} onChange={event=>updateBrand(index,brandIndex,event.target.value)} />
            {mode === '多品多类' && row.brands.length>1&&<Button danger type="text" icon={<DeleteOutlined />} aria-label="删除品牌" onClick={()=>removeBrand(index,brandIndex)}/>}
          </div>)}
        {!readOnly && mode === '多品多类' && <Button type="dashed" size="small" icon={<PlusOutlined />} onClick={()=>addBrand(index)}>新增品牌</Button>}
      </div>
      {!readOnly && mode === '多品多类' && rows.length > 1 ? <Button danger type="text" icon={<DeleteOutlined />} onClick={() => remove(index)}>删除</Button> : <span>—</span>}
    </div>)}
    {!readOnly && mode === '多品多类' && <Button block type="dashed" icon={<PlusOutlined />} onClick={add} disabled={rows.length >= categories.length}>新增类别</Button>}
    <Space className="muted">已配置 {rows.filter(row => row.category).length} 个类别、{rows.reduce((sum, row) => sum + row.brands.filter(brand=>brand.trim()).length, 0)} 个品牌</Space>
  </div>
}

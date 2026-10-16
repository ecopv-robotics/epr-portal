export type CatalogService = { id: string; country: string; type: string; serviceType: string; title: string; description: string; price: number; additionalCategoryPrice:number; additionalBrandPrice:number; unit: string; color: string; code: string; reportingFrequency: string; serviceYears: string[]; subjectTypes: string[]; packageTypes: string[]; productCategories:string[]; purchaseNotes: string[] }

export function calculateServicePrice(service: Pick<CatalogService, 'price'|'productCategories'|'additionalCategoryPrice'|'additionalBrandPrice'>, configurations: {category:string;brands:string[]}[]) {
  if (!service.productCategories.length) return service.price
  const categoryCount = configurations.filter(item => item.category).length
  const brandCount = configurations.reduce((sum, item) => sum + item.brands.filter(brand=>brand.trim()).length, 0)
  return service.price
    + Math.max(categoryCount - 1, 0) * service.additionalCategoryPrice
    + Math.max(brandCount - categoryCount, 0) * service.additionalBrandPrice
}

const baseCatalog = [
  { id: 'de-weee', country: '德国', type: 'WEEE', serviceType: '注册', title: '德国 WEEE 注册', description: '电子电气设备合规注册与申报', price: 2800, unit: '年', color: '#142d80', code: 'DE' },
  { id: 'fr-pack', country: '法国', type: '包装法', serviceType: '注册', title: '法国包装法注册', description: '包装生产者责任延伸合规服务', price: 980, unit: '年', color: '#3552a4', code: 'FR' },
  { id: 'de-battery-brand', country: '德国', type: '电池法', serviceType: '增值服务', title: '德国电池法品牌增加', description: '已注册账户增加电池品牌', price: 500, unit: '次', color: '#161616', code: 'DE' },
  { id: 'es-weee-transfer', country: '西班牙', type: 'WEEE', serviceType: '转代理', title: '西班牙 WEEE 转代理', description: '将现有注册转入平台管理', price: 680, unit: '次', color: '#e33d3d', code: 'ES' },
  { id: 'it-pack-renew', country: '意大利', type: '包装法', serviceType: '续费', title: '意大利包装法续费', description: '年度合规服务续费', price: 720, unit: '年', color: '#2d9c67', code: 'IT' },
  { id: 'fr-plastic', country: '法国', type: '一次性塑料', serviceType: '注册', title: '法国一次性塑料注册', description: 'SUP 生产者责任合规注册', price: 1080, unit: '年', color: '#536cc7', code: 'FR' },
] as const

export const catalog: CatalogService[] = baseCatalog.map(service => ({
  ...service,
  additionalCategoryPrice: service.id === 'de-weee' ? 600 : 0,
  additionalBrandPrice: service.id === 'de-weee' ? 300 : 0,
  reportingFrequency: service.id === 'de-weee' ? '月度申报' : '按当地法规配置',
  serviceYears: ['2026年（自然年）'],
  subjectTypes: [`${service.country}公司`, `非${service.country}公司`],
  packageTypes: ['一品一类', '多品多类'],
  productCategories: service.id === 'de-weee' ? ['热交换器 家用','充气灯 家用','大型光伏 家用','非充气灯 家用','屏幕类 家用','大型非光伏 家用','小型非光伏 家用','小型光伏 家用','小型IT 家用','热交换器 商用','屏幕类 商用','灯 商用','大型非光伏 商用','大型光伏 商用','小型非光伏 商用','小型光伏 商用','小型IT 商用'] : [],
  purchaseNotes: [
    '注册成功后将获得对应国家的 EPR 注册号。',
    '报价包含基础注册服务费，官方费用或回收费按实际情况结算。',
    '品牌、品类及企业资料在付款后按每个服务实例分别补充。',
    '资料提交官方后产生的官费不支持退款。',
    '政策、官费或回收费调整时，平台可能根据官方标准补收差额。',
  ],
}))

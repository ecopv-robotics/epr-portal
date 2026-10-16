PORTAL_COUNTRIES = [
    "德国", "法国", "英国", "丹麦", "加拿大", "匈牙利", "卢森堡", "奥地利", "希腊", "意大利", "捷克",
    "斯洛伐克", "比利时", "波兰", "爱尔兰", "瑞典", "立陶宛", "罗马尼亚", "芬兰", "荷兰", "葡萄牙", "西班牙",
]

GERMANY_WEEE_CATEGORIES = [
    "热交换器 家用", "充气灯 家用", "大型光伏 家用", "非充气灯 家用", "屏幕类 家用",
    "大型非光伏 家用", "小型非光伏 家用", "小型光伏 家用", "小型IT 家用",
    "热交换器 商用", "屏幕类 商用", "灯 商用", "大型非光伏 商用", "大型光伏 商用",
    "小型非光伏 商用", "小型光伏 商用", "小型IT 商用",
]

PORTAL_SERVICES = [
    {"id": "de-weee", "country": "德国", "country_code": "DE", "product_type": "WEEE", "service_type": "注册", "title": "德国 WEEE 注册", "description": "电子电气设备合规注册与申报", "price": 2800, "additional_category_price": 600, "additional_brand_price": 300, "unit": "年", "color": "#142d80"},
    {"id": "fr-pack", "country": "法国", "country_code": "FR", "product_type": "包装法", "service_type": "注册", "title": "法国包装法注册", "description": "包装生产者责任延伸合规服务", "price": 980, "unit": "年", "color": "#3552a4"},
    {"id": "de-battery-brand", "country": "德国", "country_code": "DE", "product_type": "电池法", "service_type": "增值服务", "title": "德国电池法品牌增加", "description": "已注册账户增加电池品牌", "price": 500, "unit": "次", "color": "#161616"},
    {"id": "es-weee-transfer", "country": "西班牙", "country_code": "ES", "product_type": "WEEE", "service_type": "转代理", "title": "西班牙 WEEE 转代理", "description": "将现有注册转入平台管理", "price": 680, "unit": "次", "color": "#e33d3d"},
    {"id": "it-pack-renew", "country": "意大利", "country_code": "IT", "product_type": "包装法", "service_type": "续费", "title": "意大利包装法续费", "description": "年度合规服务续费", "price": 720, "unit": "年", "color": "#2d9c67"},
    {"id": "fr-plastic", "country": "法国", "country_code": "FR", "product_type": "一次性塑料", "service_type": "注册", "title": "法国一次性塑料注册", "description": "SUP 生产者责任合规注册", "price": 1080, "unit": "年", "color": "#536cc7"},
]

for service in PORTAL_SERVICES:
    service.setdefault("additional_category_price", 0)
    service.setdefault("additional_brand_price", 0)
    service["service_years"] = ["2026年（自然年）"]
    # Operational policy configured by staff; customers only see it and cannot choose it.
    service["reporting_frequency"] = "月度申报" if service["id"] == "de-weee" else "按当地法规配置"
    service["subject_types"] = [f"{service['country']}公司", f"非{service['country']}公司"]
    service["package_types"] = ["一品一类", "多品多类"]
    service["product_categories"] = GERMANY_WEEE_CATEGORIES if service["id"] == "de-weee" else []
    service["purchase_notes"] = [
        "注册成功后将获得对应国家的 EPR 注册号。",
        "报价包含基础注册服务费，官方费用或回收费按实际情况结算。",
        "品牌、品类及企业资料在付款后按每个服务实例分别补充。",
        "资料提交官方后产生的官费不支持退款。",
        "政策、官费或回收费调整时，平台可能根据官方标准补收差额。",
    ]

PORTAL_SERVICE_BY_ID = {item["id"]: item for item in PORTAL_SERVICES}

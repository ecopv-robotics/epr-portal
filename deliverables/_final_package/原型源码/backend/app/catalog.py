EUROPEAN_COUNTRIES = [
    ("Albania", "阿尔巴尼亚"), ("Andorra", "安道尔"), ("Armenia", "亚美尼亚"),
    ("Austria", "奥地利"), ("Azerbaijan", "阿塞拜疆"), ("Belarus", "白俄罗斯"),
    ("Belgium", "比利时"), ("Bosnia and Herzegovina", "波黑"), ("Bulgaria", "保加利亚"),
    ("Croatia", "克罗地亚"), ("Cyprus", "塞浦路斯"), ("Czechia", "捷克"),
    ("Denmark", "丹麦"), ("Estonia", "爱沙尼亚"), ("Finland", "芬兰"),
    ("France", "法国"), ("Georgia", "格鲁吉亚"), ("Germany", "德国"),
    ("Greece", "希腊"), ("Hungary", "匈牙利"), ("Iceland", "冰岛"),
    ("Ireland", "爱尔兰"), ("Italy", "意大利"), ("Kosovo", "科索沃"),
    ("Latvia", "拉脱维亚"), ("Liechtenstein", "列支敦士登"), ("Lithuania", "立陶宛"),
    ("Luxembourg", "卢森堡"), ("Malta", "马耳他"), ("Moldova", "摩尔多瓦"),
    ("Monaco", "摩纳哥"), ("Montenegro", "黑山"), ("Netherlands", "荷兰"),
    ("North Macedonia", "北马其顿"), ("Norway", "挪威"), ("Poland", "波兰"),
    ("Portugal", "葡萄牙"), ("Romania", "罗马尼亚"), ("Russia", "俄罗斯"),
    ("San Marino", "圣马力诺"), ("Serbia", "塞尔维亚"), ("Slovakia", "斯洛伐克"),
    ("Slovenia", "斯洛文尼亚"), ("Spain", "西班牙"), ("Sweden", "瑞典"),
    ("Switzerland", "瑞士"), ("Turkey", "土耳其"), ("Ukraine", "乌克兰"),
    ("United Kingdom", "英国"), ("Vatican City", "梵蒂冈"),
]

SERVICES = [
    ("WEEE", "WEEE", "电子电气设备"),
    ("Battery", "电池法", "电池与蓄电池"),
    ("Packaging", "包装法", "包装与包装废弃物"),
    ("SUP", "一次性塑料", "一次性塑料制品"),
]

PRODUCT_FIELDS = {
    "WEEE": [
        ("name", "产品名称", "text", True, None), ("brand", "品牌", "text", True, None),
        ("model", "型号", "text", True, None), ("ean", "EAN", "text", False, None),
        ("weight", "重量 (kg)", "number", True, None),
        ("category", "设备类别", "select", True, ["大型设备", "小型设备", "IT及通信设备", "照明设备", "其他"]),
    ],
    "Battery": [
        ("name", "产品名称", "text", True, None), ("battery_type", "电池类型", "select", True, ["便携式电池", "工业电池", "汽车电池"]),
        ("chemistry", "化学体系", "text", True, None), ("weight", "单个电池重量 (kg)", "number", True, None),
        ("annual_quantity", "预计年销售量", "number", True, None),
    ],
    "Packaging": [
        ("name", "产品名称", "text", True, None), ("material", "包装材质", "select", True, ["纸", "塑料", "玻璃", "金属", "木材", "复合材料"]),
        ("packaging_weight", "包装重量 (kg)", "number", True, None), ("annual_quantity", "预计年销售量", "number", True, None),
    ],
    "SUP": [
        ("name", "产品名称", "text", True, None), ("category", "SUP 类别", "select", True, ["餐具", "饮料容器", "食品容器", "塑料袋", "其他"]),
        ("plastic_type", "塑料类型", "text", True, None), ("weight", "单件重量 (kg)", "number", True, None),
        ("annual_quantity", "预计年销售量", "number", True, None),
    ],
}

GERMANY_WEEE_CATEGORIES = [
    "热交换设备",
    "屏幕设备",
    "气体放电灯",
    "非气体放电灯",
    "大型设备，单边尺寸大于50cm",
    "小型设备，单边尺寸小于50cm",
    "小型信息和电信设备",
    "大型光伏，单边尺寸大于50cm",
    "小型光伏，单边尺寸小于50cm",
]

# 国家 + 服务的字段差异集中在模板配置层，业务接口与前端不写国家分支。
COUNTRY_SERVICE_PRODUCT_FIELDS = {
    ("Germany", "WEEE"): [
        ("category", "产品类别", "select", True, GERMANY_WEEE_CATEGORIES),
        ("name", "产品名称", "text", True, None),
        ("brand_logo", "对应的品牌logo", "text", True, None),
        ("max_dimension_cm", "单边最大尺寸cm", "number", True, None),
        ("estimated_sales", "预计销售量", "number", False, None),
    ],
}


def get_product_fields(country: str, service: str):
    return COUNTRY_SERVICE_PRODUCT_FIELDS.get((country, service), PRODUCT_FIELDS[service])

MATERIALS = {
    "WEEE": [("营业执照", True), ("法人身份证/护照", True), ("产品清单", True), ("产品图片", True), ("授权书", True)],
    "Battery": [("营业执照", True), ("法人身份证/护照", True), ("电池产品清单", True), ("电池成分说明", True), ("授权书", True)],
    "Packaging": [("营业执照", True), ("法人身份证/护照", True), ("包装材料清单", True), ("预计销售量", True), ("授权书", True)],
    "SUP": [("营业执照", True), ("法人身份证/护照", True), ("一次性塑料产品清单", True), ("产品图片", True), ("授权书", True)],
}

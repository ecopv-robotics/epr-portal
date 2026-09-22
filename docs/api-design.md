# REST API 设计

基础路径：`/api`。除目录与登录外，使用 `Authorization: Bearer <JWT>`。

## Phase 1

| 方法 | 路径 | 用途 | 鉴权 |
|---|---|---|---|
| POST | `/auth/login` | 手机/邮箱/用户名与密码登录 | 否 |
| GET | `/auth/me` | 当前用户 | 是 |
| GET | `/catalog/countries` | 国家及可选服务目录 | 否 |
| GET | `/applications?page=1&page_size=10` | 当前用户递单 | 是 |
| POST | `/applications` | 创建单国家、单服务草稿 | 是 |
| GET | `/applications/{id}` | 当前用户递单详情 | 是 |

### 创建递单

请求：

```json
{ "country": "Germany", "service_type": "WEEE" }
```

响应 `201`：

```json
{
  "id": 1,
  "application_no": "EPR2026000001",
  "company_name": null,
  "country": "Germany",
  "service_type": "WEEE",
  "status": "DRAFT",
  "created_time": "2026-09-20T09:00:00Z",
  "submitted_time": null
}
```

## Phase 2

- `GET /catalog/templates/{country}/{service}`：获取当前有效动态模板。
- `GET /company/history`：当前用户可复用企业资料。
- `GET /applications/{id}/form`：聚合读取模板与已填资料。
- `PUT /applications/{id}/company`：保存或复用公司资料。
- `PUT /applications/{id}/legal-person`：保存法人资料。
- `PUT /applications/{id}/store`：保存店铺资料。
- `PUT /applications/{id}/products`：整体保存动态产品列表。
- `POST /files/upload`：公司、法人、店铺通用文件上传。
- `POST /material/upload`：上传文件并返回存储对象信息。

文件上传接受 `multipart/form-data`，仅允许 PDF/JPG/JPEG/PNG，默认最大 20MB。`material/upload` 额外要求 `application_id` 和 `requirement_id`，并校验材料要求属于递单锁定的模板。

## Phase 3

| 方法 | 路径 | 用途 | 角色 |
|---|---|---|---|
| POST | `/applications/{id}/submit` | 提交或补件重提 | 客户本人 |
| GET | `/applications/{id}/status-history` | 查看状态轨迹 | 客户本人 |
| GET | `/admin/applications` | 审核列表，支持状态/关键词/分页 | ADMIN |
| GET | `/admin/applications/{id}` | 查看完整申请资料 | ADMIN |
| PATCH | `/admin/applications/{id}/status` | 接单、要求补件、审核完成 | ADMIN |
| GET | `/admin/applications/{id}/status-history` | 后台查看状态轨迹 | ADMIN |

提交校验失败返回 `422`，`detail.missing_fields` 包含全部缺失项。非法状态转换返回 `409`，越权返回 `403`。

## 错误规范

沿用 FastAPI `detail` 字段；401 表示凭证无效，403 表示无权限，404 表示资源不存在，422 表示请求校验失败。生产环境不向客户端返回堆栈或内部数据库错误。

# EPR Admin 管理端

独立管理端位于 `frontend/admin`，使用 React、TypeScript、Ant Design Pro，默认运行在 `http://localhost:5174`。

## Phase 1：登录、Dashboard、递单列表

- 内部员工账号登录与客户账号隔离。
- Dashboard 展示递单状态和个人任务统计。
- 递单列表支持申请编号关键词、状态、分页查询。

## Phase 2：申请详情与审核

- 查看公司、法人、店铺、产品和材料资料。
- 产品字段读取 `form_field`，材料规则读取 `material_requirement`。
- 支持文件预览、接单、补件、审核通过和状态轨迹。

## Phase 3：员工权限与任务分配

- `role` 保存权限集合，`employee` 关联登录用户与岗位角色。
- 管理员可把递单分配给员工。
- `audit_record` 记录状态变化、任务分配和模板变更。

## Phase 4：模板配置

- 按数据库中的国家/服务模板维护动态字段。
- 支持字段类型、必填、下拉选项和排序配置。
- 支持材料名称、必填、格式、说明和排序配置。
- 业务页面不按国家硬编码字段或材料。

## 启动

```text
cd frontend/admin
npm install
npm run dev
```

系统管理员：`admin@eprflow.com / Demo123!`

销售：`sales@eprflow.com / Demo123!`

财务：`finance@eprflow.com / Demo123!`

商务：`business@eprflow.com / Demo123!`

交付：`delivery@eprflow.com / Demo123!`

商务兼容账号：`staff@eprflow.com / Demo123!`

## 测试

```text
cd backend
python -m pytest

cd frontend/admin
npm run lint
npm run build
```

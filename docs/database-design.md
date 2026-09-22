# 数据库设计

## 设计原则

- PostgreSQL 为生产数据库；主键使用自增整数。
- 所有业务归属通过外键表达。
- 动态字段使用 JSONB（Phase 2）；固定、可查询的核心属性使用普通列。
- 文件列只保存存储对象键或 URL，不保存二进制内容。

## Phase 1 已实现

### user

| 字段 | 类型 | 约束 |
|---|---|---|
| id | bigint/int | PK |
| username | varchar(100) | unique, not null |
| password_hash | varchar(255) | not null |
| phone | varchar(30) | unique, nullable |
| email | varchar(255) | unique, nullable |
| role | enum | CUSTOMER / ADMIN |
| created_time | timestamptz | default now |

### company

保存可长期复用的公司信息。除名称、类型、注册号、地址外，包含 `registration_region`、`established_date`、`vat_number` 以及营业执照、信用报告、CR、BR、NNC1/NAR1、董事索引等文件字段。

### application

| 字段 | 类型 | 约束 |
|---|---|---|
| id | bigint/int | PK |
| application_no | varchar(30) | unique, not null |
| user_id | FK user | not null, indexed |
| company_id | FK company | nullable, indexed |
| template_id | FK service_template | nullable, indexed；锁定模板版本 |
| country | varchar(100) | not null |
| service_type | varchar(100) | not null |
| status | enum | default DRAFT |
| created_time | timestamptz | default now |
| submitted_time | timestamptz | nullable |
| reviewed_time | timestamptz | nullable |
| review_note | text | nullable |

编号规则：`EPR` + UTC 年份 + 六位数据库 ID，例如 `EPR2026000001`。编号只作为展示标识，不承载权限或关联语义。

### service_template

Phase 1 已建立国家服务目录表，包含国家及展示名、服务及展示名、描述、版本和状态，并对 `(country, service_type, version)` 建立唯一约束。创建递单只接受已启用的国家服务组合；Phase 2 在此基础上关联动态字段和材料要求。

## Phase 2 已实现表

- `legal_person`：`company_id` 唯一外键；中英文/拼音姓名、证件类型、性别、联系人邮箱电话、证件文件与签名。
- `store`：`application_id` 外键；平台、链接、英文公司名、英文注册城市、邮编、英文地址、后台截图。
- `product`：`application_id` 外键；`product_data JSONB`。
- `form_field`：模板外键、字段名、标签、类型、必填、选项 JSONB、排序。
- `material_requirement`：模板外键、材料名称、必填、文件类型、说明。
- `material_file`：申请与要求双外键、文件 URL、原始名称、大小、上传时间；一份递单的同一材料要求只保留当前文件。
- `application_status_history`：申请外键、原状态、目标状态、审核意见、操作人和操作时间，作为状态审计轨迹。

## 关系

`user 1—N application`；`company 1—N application`；`company 1—1/N legal_person`；`application 1—N store/product/material_file`；`service_template 1—N form_field/material_requirement`。

模板不能因新版本覆盖历史递单。Phase 2 应在递单中固化选定模板版本或模板 ID。

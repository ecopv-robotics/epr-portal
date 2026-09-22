# 业务流程与状态流转

## 客户流程

1. 用户通过手机、邮箱或用户名登录。
2. “我的递单”仅展示当前用户数据。
3. 新建递单时先选择国家，再从该国家服务目录中选择一项服务。
4. 系统立即创建 `DRAFT` 草稿与唯一申请编号。
5. Phase 2 按选定国家与服务读取模板，依次填写公司、法人、店铺、产品、材料。
6. 用户在确认页核对数据；Phase 3 校验通过后提交。

## 资料复用

选择历史公司后，可复制/关联公司信息和法人信息。不得带入店铺、产品或国家服务材料。复用行为必须清晰展示来源，并允许用户在当前申请中确认或调整。

## 状态机

```text
DRAFT -> SUBMITTED -> REVIEWING -> COMPLETED
                       |     ^
                       v     |
                    NEED_FIX
```

- 客户提交：`DRAFT → SUBMITTED`，提交前执行完整性校验并锁定资料。
- 后台接单：`SUBMITTED → REVIEWING`。
- 要求补件：`REVIEWING → NEED_FIX`。
- 客户补件后：`NEED_FIX → REVIEWING`。
- 审核完成：`REVIEWING → COMPLETED`。

不允许跳过提交直接完成；`COMPLETED` 为终态。Phase 3 已在服务层集中校验状态转换，并将每次转换写入 `application_status_history`。

## 模板加载

以 `(country, service_type)` 查询当前启用模板，按 `sort` 输出字段和材料清单。应用需固定所用模板版本，避免配置更新改变历史申请的展示与校验结果。代码中禁止以国家名称编写业务条件分支。

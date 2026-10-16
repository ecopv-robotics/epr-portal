# EPR Portal

企业级 EPR 客户递单门户。Phase 1–3 已完成：JWT 登录、递单管理、50 个欧洲国家与四项服务、动态模板、六步资料填写、资料复用、本地文件上传、正式提交、状态流转和后台审核 API。

## 快速启动

1. 复制 `.env.example` 为 `.env`。
2. 启动 PostgreSQL：`docker compose up -d db`。
3. 后端：
   - `cd backend`
   - `python -m venv .venv`
   - Windows: `.venv\Scripts\activate`
   - `pip install -r requirements.txt`
   - `uvicorn app.main:app --reload --port 8000`
4. 前端：
   - `cd frontend`
   - `npm install`
   - `npm run dev`
5. 管理端：
   - `cd frontend/admin`
   - `npm install`
   - `npm run dev`
6. 客户门户打开 `http://localhost:5173`，使用 `demo@eprflow.com / Demo123!`。
7. 员工工作台打开 `http://localhost:5174`：
   - 系统管理员：`admin@eprflow.com / Admin123!`
   - 销售：`sales@eprflow.com / Sales123!`
   - 财务：`finance@eprflow.com / Finance123!`
   - 商务：`business@eprflow.com / Business123!`
   - 交付：`delivery@eprflow.com / Delivery123!`
   - 商务兼容账号：`staff@eprflow.com / Staff123!`

后台审核 API 演示账号：`admin@eprflow.com / Admin123!`（通过 `/docs` 调试）。

### 分角色测试数据

执行以下命令可幂等生成角色场景数据（重复执行不会累加）：

```powershell
cd backend
python -m scripts.seed_showcase
```

- 销售：标准价待付款、合同已上传和待跟进订单。
- 系统管理员：同一客户多笔待付款订单、待设置打包优惠及已分摊优惠订单。
- 财务：客户已上传付款凭证待确认，以及付款信息不符已驳回订单。
- 商务：待接单、审核中和已退回补件的服务实例。
- 交付：注册办理中和已下证完成的服务实例。
- 客户：可使用 `showcase.direct.star@eprflow.com / Demo123!` 查看对应订单与服务进度。

API 文档：`http://localhost:8000/docs`。

## 测试

- 后端：`cd backend && pytest`
- 客户前端：`cd frontend && npm run lint && npm run build`
- 管理端：`cd frontend/admin && npm run lint && npm run build`

业务约束、数据结构和后续阶段见 [docs/PRD.md](docs/PRD.md)。

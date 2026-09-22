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
   - 管理员：`admin@eprflow.com / Admin123!`
   - 审核员工：`staff@eprflow.com / Staff123!`

后台审核 API 演示账号：`admin@eprflow.com / Admin123!`（通过 `/docs` 调试）。

API 文档：`http://localhost:8000/docs`。

## 测试

- 后端：`cd backend && pytest`
- 客户前端：`cd frontend && npm run lint && npm run build`
- 管理端：`cd frontend/admin && npm run lint && npm run build`

业务约束、数据结构和后续阶段见 [docs/PRD.md](docs/PRD.md)。

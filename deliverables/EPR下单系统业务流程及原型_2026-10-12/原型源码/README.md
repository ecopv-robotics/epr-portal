# EPR FLOW 原型源码

本目录包含当前可运行原型的前端、管理端和后端核心源码副本，节点依赖和本地数据库未打包。

## 本地运行

1. 根据项目根目录 `.env.example` 配置环境变量。
2. 后端进入 `backend` 安装 `requirements.txt` 并启动 `uvicorn app.main:app --reload --port 8000`。
3. 客户前端进入 `frontend` 执行 `npm install` 和 `npm run dev`。
4. 管理端进入 `frontend/admin` 执行 `npm install` 和 `npm run dev`。
5. 执行 `python -m scripts.seed_showcase` 可恢复分角色测试数据。

## 测试账号

- 客户 `demo@eprflow.com / Demo123!`
- 销售 `sales@eprflow.com / Sales123!`
- 财务 `finance@eprflow.com / Finance123!`
- 商务 `business@eprflow.com / Business123!`
- 交付 `delivery@eprflow.com / Delivery123!`
- 系统管理员 `admin@eprflow.com / Admin123!`


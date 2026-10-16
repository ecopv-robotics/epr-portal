# EPR Portal

企业级 EPR 客户递单门户。Phase 1–3 已完成：JWT 登录、递单管理、50 个欧洲国家与四项服务、动态模板、六步资料填写、资料复用、本地文件上传、营业执照/身份证/护照 OCR 回填、正式提交、状态流转和后台审核 API。

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
   - 系统管理员：`admin@eprflow.com / Demo123!`
   - 销售：`sales@eprflow.com / Demo123!`
   - 财务：`finance@eprflow.com / Demo123!`
   - 商务：`business@eprflow.com / Demo123!`
   - 交付：`delivery@eprflow.com / Demo123!`
   - 商务兼容账号：`staff@eprflow.com / Demo123!`

后台审核 API 演示账号：`admin@eprflow.com / Demo123!`（通过 `/docs` 调试）。

智能证照识别默认使用本地 RapidOCR（`OCR_PROVIDER=local`），支持大陆营业执照、身份证人像面及单页 PDF，不需要 API Key 或 GPU。安装后端依赖后，首次识别会下载模型，之后使用本地模型推理；可用 `python -c "from rapidocr import RapidOCR; from PIL import Image; RapidOCR()(Image.new('RGB', (100, 100), 'white'))"` 预热检测模型，完整预热请使用一张证件示例图片。模型文件需随离线部署环境预先准备。识别结果先展示给客户确认，无法提取的字段仍需手动填写，护照暂需手填。不会自动转发到云端。

如显式选择 `OCR_PROVIDER=openai`，需配置 `OPENAI_API_KEY`，可通过 `OPENAI_OCR_MODEL` 指定模型。营业执照英文翻译仍是独立的云端功能，与本地 OCR 无关。

本地识别使用 PP-OCRv6 medium 检测与识别模型（检测边长 1280，图片最长边 3200）。字段缺失或文字置信度不足时，使用对比度/锐化增强与 small 模型补充一次；冲突结果降低置信度并提示核对。模型均需在离线部署前缓存。文字置信度不等同于字段正确率；更高精度配置会增加 CPU 推理时间。

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

# 人员信息后台管理程序

> 基于 **FastAPI + Dash + Redmine** 的人员信息管理系统，提供后端 REST API、前端 Web 界面、Redmine 数据对接、JWT 认证、人员增删改查与批量导入等功能。

---

## 目录

- [一、项目简介](#一项目简介)
- [二、技术栈](#二技术栈)
- [三、项目目录结构](#三项目目录结构)
- [四、环境要求](#四环境要求)
- [五、部署前准备](#五部署前准备)
- [六、启动步骤](#六启动步骤)
- [七、测试说明](#七测试说明)
- [八、功能说明](#八功能说明)
- [九、常见问题](#九常见问题)
- [十、注意事项](#十注意事项)

---

## 一、项目简介

本项目是一个人员信息管理系统，采用前后端分离架构：

- **后端**：基于 FastAPI 构建 RESTful API，负责业务逻辑、JWT 认证、限流、Redis 黑名单管理。
- **前端**：基于 Dash + Dash Bootstrap Components 构建单页 Web 应用，提供登录、Dashboard、人员列表、高级搜索、数据导入等功能页面。
- **数据存储**：人员数据以 Redmine Issue（自定义字段）形式存储，不依赖独立数据库；Redis 用于 Token 黑名单和登录限流（可选，降级运行）。
- **认证**：用户凭证通过 Redmine Basic Auth 验证，验证通过后由后端签发 JWT Token；登出时将 Token 的 jti 写入 Redis 黑名单实现即时失效。
- **导入**：支持 CSV / Excel 文件批量导入，提供 `skip` / `overwrite` / `terminate` 三种重复处理策略，并可导出错误行 CSV。

---

## 二、技术栈

| 类别 | 组件 | 版本 | 用途 |
|------|------|------|------|
| 后端框架 | FastAPI | 0.115.0 | REST API 框架 |
| ASGI 服务器 | uvicorn[standard] | 0.49.0 | 后端运行容器 |
| 数据校验 | pydantic / pydantic-settings | 2.13.4 / 2.5.2 | 模型校验与配置管理 |
| HTTP 客户端 | httpx | 0.28.1 | 异步调用 Redmine API |
| 认证 | python-jose[cryptography] | 3.3.0 | JWT 签发与解析 |
| 密码哈希 | passlib[bcrypt] | 1.7.4 | 本地管理员备用密码方案 |
| 缓存 | redis | 5.0.7 | Token 黑名单、登录限流 |
| 表单解析 | python-multipart | 0.0.32 | 文件上传支持 |
| 前端框架 | dash | 4.3.0 | Python Web UI 框架 |
| UI 组件 | dash-bootstrap-components | 2.0.4 | Bootstrap 风格组件 |
| 图表 | plotly | 6.3.0 | Dashboard 图表 |
| 数据处理 | pandas | 2.2.3 | CSV/Excel 解析、导入 |
| HTTP 请求（前端） | requests | 2.32.3 | 前端调用后端 API |
| 测试框架 | pytest | 7.4.3 | 单元/接口/集成测试 |
| 测试覆盖率 | pytest-cov | 4.1.0 | 覆盖率统计 |
| 异步测试 | pytest-asyncio | 0.21.1 | 异步用例支持 |
| UI 测试 | Playwright | （需单独安装） | 端到端 UI 自动化测试 |

> 说明：Playwright 不在 `requirements.txt` 中，运行 UI 测试前需单独安装：`pip install pytest-playwright` 并执行 `playwright install`。

---

## 三、项目目录结构

```
Personnel-Information-Management-System/
├── backend/                      # 后端代码
│   ├── main.py                   # FastAPI 应用入口（含 uvicorn 启动逻辑）
│   ├── __init__.py
│   └── app/
│       ├── api/v1/               # API 路由层
│       │   ├── auth.py            # 认证路由：/login /verify /logout
│       │   ├── personnel.py       # 人员管理路由：CRUD、搜索、批量删除
│       │   └── import_api.py     # 数据导入路由：上传导入、导出错误行
│       ├── core/                  # 核心组件
│       │   ├── config.py          # 全局配置（读取 .env）
│       │   ├── dependencies.py    # FastAPI 依赖注入（RedmineClient、当前用户）
│       │   ├── security.py        # JWT 签发/解析、密码哈希、黑名单
│       │   ├── redis_client.py    # Redis 连接池与基础操作（降级安全）
│       │   ├── redmine_client.py  # Redmine API 客户端（Issue/User CRUD）
│       │   └── rate_limiter.py    # 登录限流（Redis INCR 滑动窗口）
│       ├── models/                # 领域模型
│       │   ├── personnel.py       # Personnel 模型 + Redmine Issue 映射
│       │   ├── custom_field.py    # 自定义字段 ID 映射表
│       │   └── user.py            # 用户模型
│       ├── schemas/               # Pydantic Schema
│       │   ├── auth.py            # 登录请求/响应
│       │   ├── personnel.py       # 人员 CRUD 请求/响应
│       │   ├── import_schemas.py  # 导入结果/错误详情
│       │   └── common.py          # 统一响应 ApiResponse、PaginationData
│       ├── services/              # 业务服务层
│       │   ├── auth_service.py    # 登录认证逻辑
│       │   ├── personnel_service.py # 人员 CRUD 业务
│       │   └── import_service.py # 文件导入业务
│       └── utils/
│           ├── logger.py          # 日志管理（RotatingFileHandler）
│           └── exceptions.py      # 自定义业务异常
├── frontend/                     # 前端代码
│   ├── app.py                    # Dash 应用入口（路由、认证守卫、登出）
│   ├── ui/                       # 页面
│   │   ├── login.py              # 登录页
│   │   ├── dashboard.py          # 仪表盘/首页
│   │   ├── personnel_list.py     # 人员列表页
│   │   ├── personnel_form.py      # 新增/编辑人员表单
│   │   ├── search.py             # 高级搜索页
│   │   └── import_page.py        # 数据导入页
│   ├── components/               # 通用组件
│   │   ├── navbar.py
│   │   ├── sidebar.py
│   │   └── modals.py
│   ├── utils/
│   │   ├── api_client.py         # 后端 HTTP 调用封装（get/post/put/delete/upload）
│   │   └── auth.py               # 前端 Token 缓存管理
│   └── assets/custom.css         # 自定义样式
├── tests/                        # 测试代码
│   ├── conftest.py               # 根级 fixture（Redmine Mock、TestClient）
│   ├── unit/                     # 单元测试（模型、服务、工具）
│   ├── api/                      # 接口测试（FastAPI TestClient）
│   ├── integration/              # 集成测试（完整业务链路）
│   └── ui/                       # UI 测试（Playwright）
│       ├── pages/                # Page Object 模式
│       └── test_*.py             # UI 测试用例
├── logs/                         # 运行日志目录
│   └── app.log                   # 主日志文件
├── htmlcov/                      # 测试覆盖率 HTML 报告（自动生成）
├── .env                          # 环境变量（敏感，已 gitignore）
├── .env_dev                      # 开发环境变量模板（可参考）
├── requirements.txt              # Python 依赖清单
├── pytest.ini                    # pytest 配置
├── .gitignore
└── README.md
```

---

## 四、环境要求

### 4.1 操作系统

- Windows / Linux / macOS 均可（当前已在 Windows 25H2 验证）。

### 4.2 Python 版本

- **建议 Python 3.11 及以上**（项目使用了 `datetime.UTC`、现代类型注解等 3.11+ 特性）。
- 最低不低于 Python 3.10。

### 4.3 外部服务

| 服务 | 是否必需 | 说明 |
|------|----------|------|
| **Redmine** | ✅ 必需 | 人员数据存储与用户认证均依赖 Redmine；需可访问的 Redmine 实例 + Admin API Key |
| **Redis** | ⚠️ 可选（推荐） | 用于 Token 黑名单与登录限流；未启用或连接失败时应用降级运行（黑名单失效、限流放行） |

### 4.4 凭证要求

- **Redmine Admin API Key**：必须，用于读取用户完整信息（含 custom_fields）和操作 Issue。Key 对应账户需具备目标项目的 Issue 读写权限。
- **JWT SECRET_KEY**：必须，JWT 签名密钥；生产环境务必替换为强随机值。
- **登录账号**：使用 Redmine 中实际存在的用户账号（用户名 + Redmine 密码）。

---

## 五、部署前准备

### 5.1 克隆项目

```bash
git clone <仓库地址>
cd Personnel-Information-Management-System
```

### 5.2 创建并激活虚拟环境

**Windows PowerShell：**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS：**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 5.3 安装依赖

```bash
pip install -r requirements.txt
```

> 如需运行 UI 测试，额外安装：
> ```bash
> pip install pytest-playwright
> playwright install
> ```

### 5.4 配置环境变量

在项目根目录创建 `.env` 文件（参考 `.env` 已有结构或 `.env_dev`），关键配置项如下：

```ini
# ─── 安全配置 ───────────────────────────────────────────────
# JWT 签名密钥（生产环境必填，务必替换为随机值）
# Windows PowerShell 生成方式:
#   [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
# Linux/Mac 生成方式:
#   openssl rand -base64 32
SECRET_KEY=<请替换为你的随机密钥>

# ─── 后端服务端口 ───────────────────────────────────────────
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8002

# ─── 前端服务端口（Dash）────────────────────────────────────
DASH_HOST=0.0.0.0
DASH_PORT=8070

# ─── 后端 API 基址（前端调用用）────────────────────────────
API_BASE=http://localhost:8002

# ─── 跨域配置 ───────────────────────────────────────────────
# 允许的前端地址（逗号分隔），默认仅允许本地 8070
CORS_ALLOWED_ORIGINS=http://127.0.0.1:8070

# ─── Redmine 配置 ───────────────────────────────────────────
REDMINE_URL=http://127.0.0.1:3001/
REDMINE_API_KEY=<你的 Redmine Admin API Key>
REDMINE_PROJECT_ID=1

# ─── Redis 配置 ─────────────────────────────────────────────
REDIS_ENABLE=True
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
# REDIS_PASSWORD=  # 如有密码请填写

# ─── 日志配置（可选，已有默认值）────────────────────────────
# LOG_LEVEL=INFO          # DEBUG / INFO / WARNING / ERROR
# LOG_DIR=logs            # 日志目录
# LOG_MAX_BYTES=10485760  # 单文件 10MB
# LOG_BACKUP_COUNT=5      # 保留 5 份历史日志

# ─── JWT 配置（可选，已有默认值）────────────────────────────
# JWT_ALGORITHM=HS256
# JWT_EXPIRE_HOURS=24
```

> **说明**：`backend/app/core/config.py` 通过 `pydantic-settings` 自动读取 `.env`；`SECRET_KEY`、`REDMINE_URL`、`REDMINE_API_KEY` 为必填项，缺失会启动失败。

---

## 六、启动步骤

### 6.1 启动后端服务

在项目根目录（虚拟环境已激活）执行：

```bash
# 方式一：直接运行入口脚本
python backend/main.py

# 方式二：使用 uvicorn 模块方式（支持热重载）
python -m backend.main

# 方式三：使用 uvicorn 命令直接启动
uvicorn backend.main:app --host 0.0.0.0 --port 8002 --reload
```

- 默认监听：`http://0.0.0.0:8002`
- 开发模式下（`DEBUG=True`）启用 `--reload` 热重载。

### 6.2 启动前端服务

**新开一个终端**，激活虚拟环境后执行：

```bash
python frontend/app.py
```

- 默认访问地址：`http://127.0.0.1:8070`
- 控制台会输出：
  ```
  ============================================================
  人员信息管理系统 - 前端启动
  访问地址: http://localhost:8070
  ============================================================
  ```

### 6.3 验证服务启动

**验证后端：**
```bash
# 根路径返回项目信息
curl http://localhost:8002/
# 期望返回: {"message":"人员信息管理系统 API","Version":"1.0.0"}
```

**验证 Redis 连接（如已启用）：**
查看后端启动日志，应出现：
```
Redis 连接成功 | host=127.0.0.1 | port=6379
```

### 6.4 访问 API 文档

FastAPI 自带交互式文档，启动后端后访问：

- **Swagger UI**：`http://localhost:8002/docs`
- **ReDoc**：`http://localhost:8002/redoc`

可在 Swagger 中直接试用 `/api/v1/auth/login`、`/api/v1/personnel/` 等接口（需先登录获取 Token，点击右上角 "Authorize" 按钮填入 `Bearer <token>`）。

### 6.5 访问前端

浏览器打开 `http://127.0.0.1:8070`，会自动跳转至 `/login` 登录页，使用 Redmine 中的真实账号登录。

---

## 七、测试说明

### 7.1 测试配置

`pytest.ini` 关键配置：

```ini
[pytest]
pythonpath = backend            # 将 backend 加入 Python 路径
testpaths = tests              # 测试目录
addopts =
    --cov=backend/app          # 覆盖率统计范围
    --cov-report=html          # 生成 HTML 覆盖率报告（htmlcov/）
    --cov-report=term-missing  # 终端输出缺失行
    --cov-branch               # 分支覆盖率
    --headed                   # UI 测试以有头模式运行
asyncio_mode = auto            # 自动处理异步测试
```

### 7.2 运行全部测试

在项目根目录执行：

```bash
pytest
```

### 7.3 分层运行测试

**单元测试：**
```bash
pytest tests/unit/ -v
```

**接口测试：**
```bash
pytest tests/api/ -v
```

**集成测试：**
```bash
pytest tests/integration/ -v
```

**UI 测试（需要前后端服务均启动）：**
```bash
# 先确保后端在 8002、前端在 8070 已启动
pytest tests/ui/ -v
```

> UI 测试默认使用 `--headed` 有头浏览器模式，便于观察；可在命令行追加 `--headless` 改为无头模式（需自行配置）。

### 7.4 单独运行某个测试文件

```bash
pytest tests/unit/test_personnel_service.py -v
pytest tests/api/test_personnel.py -v
pytest tests/ui/test_login_ui.py -v
```

### 7.5 测试是否依赖真实环境

- **单元/接口/集成测试**：✅ **完全 Mock**，不依赖真实 Redmine/Redis。
  - `tests/conftest.py` 提供 `RedmineMemoryStore`（内存 Redmine）+ `httpx.MockTransport`（拦截 HTTP 层）。
  - 测试账号固定为 `admin / admin123`（见 `tests/conftest.py` 中的 `login_payload` fixture）。
- **UI 测试**：⚠️ **依赖真实环境**，需要：
  1. 后端服务运行在 `http://127.0.0.1:8002`；
  2. 前端服务运行在 `http://127.0.0.1:8070`；
  3. Redmine 中存在可登录的账号（默认 `admin / admin123`，可在 `conftest.py` 的 `admin_credentials` fixture 中修改）。

### 7.6 查看覆盖率报告

测试完成后，HTML 覆盖率报告生成于 `htmlcov/index.html`，浏览器打开即可查看逐行覆盖率。

---

## 八、功能说明

### 8.1 登录认证

- **入口**：`/login` 页面（前端路由）
- **流程**：前端提交用户名 + 密码 → 后端 `/api/v1/auth/login` → 通过 Basic Auth 调 Redmine `/users/current.json` 验证 → 验证通过后用 Admin API Key 拉取用户完整信息 → 签发 JWT（含 `sub`/`username`/`role`/`jti`）→ 前端存入 `sessionStorage`。
- **限流**：同一 IP 60 秒内最多 5 次登录尝试，超出返回 HTTP 429（依赖 Redis，不可用时降级放行）。
- **登出**：前端点击导航栏退出按钮 → 调 `/api/v1/auth/logout` → 将当前 Token 的 jti 写入 Redis 黑名单（TTL 为剩余有效期）→ 前端清除本地缓存并跳转登录页。

### 8.2 人员列表

- **前端路由**：`/personnel`
- **后端接口**：`GET /api/v1/personnel/`
- 支持分页（`page`/`size`）、关键词搜索（`keyword`）、部门/职位筛选、入职日期范围筛选、排序（`sort_by`/`sort_order`）。

### 8.3 人员新增 / 编辑 / 删除 / 批量删除

| 操作 | 方法 | 接口 |
|------|------|------|
| 新增 | POST | `/api/v1/personnel/` |
| 详情 | GET | `/api/v1/personnel/{personnel_id}` |
| 修改 | PUT | `/api/v1/personnel/{personnel_id}` |
| 删除（软删除） | DELETE | `/api/v1/personnel/{personnel_id}` |
| 批量删除 | POST | `/api/v1/personnel/batch`（body: `[1,2,3]`） |

- 前端新增/编辑通过 `/add` 路由的表单页面完成。
- 删除为软删除（通过 Redmine Issue 状态变更实现）。
- 批量删除返回 `BatchDeleteResponse.deleted_count`，支持部分成功。

### 8.4 搜索 / 筛选

- **前端路由**：`/search`
- **后端接口**：`POST /api/v1/personnel/search`（body 为 `PersonnelSearchRequest`）
- 支持多条件组合高级搜索。
- 辅助接口：`GET /api/v1/personnel/departments`、`GET /api/v1/personnel/positions`（返回去重的部门/职位列表，用于筛选下拉框）。

### 8.5 数据导入

- **前端路由**：`/import`
- **后端接口**：
  - `POST /api/v1/import/`：上传 CSV / Excel 文件，参数 `strategy` 可选 `skip`（跳过重复）/ `overwrite`（覆盖重复）/ `terminate`（遇重复即终止）。
  - `POST /api/v1/import/export-errors`：导出错误行 CSV（带 UTF-8 BOM，Excel 可正确显示中文）。
- **文件列名**：支持中文列名（人员编号、姓名、性别、年龄、手机号、邮箱、部门、职位、入职日期）和英文列名（employee_id、name 等）。
- **处理流程**：pandas 解析 → 列名映射 → 逐行 Pydantic 校验 → 查询已有编号 → 按策略写入 Redmine → 返回 `ImportResultData`（含成功/失败/重复/跳过/覆盖统计 + 错误详情列表）。

### 8.6 Dashboard 仪表盘

- **前端路由**：`/dashboard`（登录后默认页）
- 展示三大功能卡片入口：人员管理、高级搜索、数据导入。
- 配合 `navbar`（顶栏含退出按钮）和 `sidebar`（侧边栏导航）组成主框架。

---

## 九、常见问题

### 9.1 Redmine 连接失败

**现象**：登录返回"用户名或密码错误"或 500 错误；后端日志出现 `httpx.ConnectError`。

**排查**：
1. 确认 `.env` 中 `REDMINE_URL` 正确且可访问：`curl <REDMINE_URL>/users/current.json`。
2. 确认 `REDMINE_API_KEY` 有效且对应账户为管理员（需读取其他用户信息）。
3. 确认 Redmine 服务已启动、防火墙放行端口。
4. 确认 `REDMINE_PROJECT_ID` 在 Redmine 中存在且 API Key 对应账户有该项目权限。

### 9.2 Redis 连接失败

**现象**：后端启动日志出现 `Redis 连接失败，应用将降级运行`。

**影响**：Token 黑名单失效（登出后 Token 在剩余有效期内仍可用）、登录限流放行（不再限制 5 次/分钟）。

**排查**：
1. 确认 Redis 服务已启动：`redis-cli ping` 应返回 `PONG`。
2. 确认 `.env` 中 `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` 正确。
3. 如暂无 Redis，可将 `REDIS_ENABLE=False`，应用会跳过连接并降级运行。

### 9.3 环境变量缺失

**现象**：后端启动报错 `ValidationError`（pydantic-settings），提示 `SECRET_KEY` / `REDMINE_URL` / `REDMINE_API_KEY` 字段缺失。

**解决**：检查项目根目录是否存在 `.env` 文件，并确认上述三个必填项已填写。

### 9.4 前端无法访问后端

**现象**：前端页面操作时报错 "连接后端失败" 或 CORS 错误。

**排查**：
1. 确认后端已启动：`curl http://localhost:8002/`。
2. 确认 `frontend/utils/api_client.py` 中的 `API_BASE`（默认 `http://localhost:8002`）与实际后端地址一致；若部署在不同主机，需修改该常量或通过 `set_api_base` 设置。
3. 确认 `.env` 的 `CORS_ALLOWED_ORIGINS` 包含前端访问地址（默认 `http://127.0.0.1:8070`）。
4. 跨域配置修改后需重启后端。

### 9.5 Token 认证失败

**现象**：接口返回 401，提示"Token 无效或已过期"或"Token 已注销"。

**排查**：
1. Token 已过期（默认 24 小时）→ 重新登录。
2. Token 已被登出加入黑名单 → 重新登录。
3. `SECRET_KEY` 被修改过，旧 Token 无法解析 → 重新登录。
4. 请求头未带 `Authorization: Bearer <token>`。

### 9.6 导入失败或字段校验失败

**现象**：导入返回错误详情列表，或 HTTP 400。

**排查**：
1. **文件格式**：仅支持 `.csv` / `.xlsx` / `.xls`，其他格式会返回"不支持的文件格式"。
2. **列名**：必须包含全部必填列（人员编号、姓名、性别、年龄、手机号、邮箱、部门、职位、入职日期），缺失列会被当作空值并校验失败。
3. **字段格式**：
   - 手机号需为 11 位数字；
   - 邮箱需符合标准格式；
   - 年龄需为合理数值；
   - 入职日期不晚于今天。
4. **CSV 编码**：建议使用 UTF-8（带 BOM），Excel 导出的 CSV 通常已带 BOM，后端用 `utf-8-sig` 解析。
5. **重复策略**：`terminate` 策略遇到第一条重复即停止；`skip` 跳过重复行；`overwrite` 覆盖更新已有记录。
6. **错误行导出**：导入完成后可点"导出错误数据"下载仅含错误行的 CSV，修正后重新导入。

---

## 十、注意事项

### 10.1 安全

- 🔴 **切勿将 `.env` 提交到 Git**（项目 `.gitignore` 已忽略 `.env`）。文件中含 `SECRET_KEY`、`REDMINE_API_KEY` 等敏感信息。
- 🔴 **生产环境务必修改 `SECRET_KEY`** 为强随机值，不要使用开发环境默认值。
- 🔴 **Redmine API Key 权限要求**：Key 对应账户需为 Redmine 管理员，否则无法通过 `get_user_with_api_key` 读取用户完整信息（含 custom_fields），登录流程会失败。
- 🔴 不要在日志、文档、聊天中泄露 Token、API Key、密码等凭证。

### 10.2 日志

- 日志目录：`logs/`（相对项目根目录，可通过 `.env` 的 `LOG_DIR` 修改）。
- 主日志文件：`logs/app.log`。
- 单文件最大 10MB，最多保留 5 份历史日志（可配置 `LOG_MAX_BYTES` / `LOG_BACKUP_COUNT`）。
- 日志级别默认 `INFO`，开发调试时可设为 `DEBUG`。

### 10.3 部署

- 生产环境建议将 `DEBUG=False`，关闭热重载。
- 生产环境建议使用 `gunicorn -k uvicorn.workers.UvicornWorker` 多进程部署后端。
- 前端 Dash 生产环境建议关闭 `debug`，并通过 `gunicorn` 或反向代理（nginx）部署。
- 确保后端 `FASTAPI_PORT`（8002）与前端 `DASH_PORT`（8070）端口未被占用。

### 10.4 数据

- 人员数据存储于 Redmine Issue 的自定义字段中，字段 ID 映射定义见 `backend/app/models/custom_field.py`。
- 删除为软删除（通过 Issue 状态变更），不会真正从 Redmine 删除记录。
- 导入前建议备份 Redmine 数据，避免 `overwrite` 策略误覆盖。

### 10.5 测试

- `tests/conftest.py` 中的 Mock Redmine 账号为 `admin / admin123`，与真实环境无关。
- UI 测试会真实操作浏览器并访问前后端服务，请确保服务已启动且 Redmine 中存在对应账号。
- 覆盖率 HTML 报告生成于 `htmlcov/`，已 gitignore，勿提交。

---

## License

本项目包含 `LICENSE` 文件，详情请参阅该文件。

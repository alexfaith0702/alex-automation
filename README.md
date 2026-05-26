# API 自动化测试框架

基于 **Python + Pytest + Allure** 的接口自动化测试框架，适用于 [app.py](app.py) 的 Flask Web 服务。

## 项目结构

```
alex-automation/
├── web_service/
│   ├── app.py                  # Flask 被测服务
│   └── static/
│       ├── login.py
│       └── query.py
│
├── run_tests.py                # 一键运行：测试 + 报告生成
├── requirements.txt            # Python 依赖
├── pytest.ini                  # Pytest 配置（标记、路径、Allure 目录）
│
├── common/                     # 封装层
│   ├── http_client.py          # requests 封装（自动日志 / Allure 步 / 脱敏）
│   ├── logger.py               # 日志封装（控制台 + 文件 + Allure 缓冲）
│   └── allure_report.py        # Java-free HTML 报告生成器
│
├── conftest.py                 # 根级 fixtures（服务启动、HttpClient、数据加载器）
│
├── test_data/                  # 数据驱动用例
│   ├── login_cases.json        # 登录用例（6 组正/反向数据）
│   └── query_cases.json        # 查询用例（8 组筛选组合）
│
├── test_api/                   # 测试用例
│   ├── conftest.py             # API 层 fixtures + 失败自动附加日志的 hook
│   ├── test_login.py           # POST /api/login（8 个用例）
│   └── test_query.py           # GET /api/query + /api/health（13 个用例）
│
└── reports/                    # 输出目录（gitignore）
    ├── allure-results/         # Allure 原始数据
    ├── allure-report/          # HTML 报告（index.html）
    └── logs/                   # 测试日志
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 一键运行（测试 → Allure 结果 → HTML 报告）
python run_tests.py

# 3. 浏览器打开报告
start reports/allure-report/index.html
```

## 常用命令

```bash
# 运行全部测试
pytest test_api/ -v

# 按标记筛选
pytest test_api/ -v -m smoke        # 冒烟测试
pytest test_api/ -v -m negative     # 反向用例

# 按名称筛选
pytest test_api/ -v -k "login"      # 只跑登录相关

# 生成 Allure 原始数据
pytest test_api/ --alluredir=reports/allure-results

# 从已有数据生成 HTML 报告（无需重新跑测试）
python common/allure_report.py
```

## 核心能力

### 1. HttpClient — requests 封装

[common/http_client.py](common/http_client.py)

```python
from common import HttpClient

client = HttpClient(base_url="http://127.0.0.1:5000", logger=log)
client.token = "your-bearer-token"

resp = client.get("/api/query", params={"keyword": "Apple"})
resp = client.post("/api/login", json={"username": "admin", "password": "pass"})
```

每个 HTTP 调用自动完成：
- 生成一个 Allure 步骤（`GET /api/query`）
- 请求/响应详情作为 JSON 附件（headers、body、status、耗时）
- Authorization 头自动脱敏
- 控制台 + 文件双通道日志

### 2. LogManager — 日志封装

[common/logger.py](common/logger.py)

三通道输出：
| 通道 | 说明 |
|------|------|
| 控制台 | 带颜色区分级别（DEBUG=青、INFO=绿、WARN=黄、ERROR=红） |
| 文件 | `reports/logs/test_run.log`，10MB 自动轮转，保留 5 个备份 |
| Allure 缓冲 | 内存保留最近 500 条，测试失败时自动附加到报告 |

```python
from common.logger import get_logger
log = get_logger()
log.info("用户登录成功")
```

### 3. HTML 报告 — 零依赖

[common/allure_report.py](common/allure_report.py)

- 读取 Allure JSON 结果，生成单个自包含 HTML 文件
- **无需 Java 环境**
- 按 Feature → Story → Test 层级展示
- 失败用例默认展开，包含：
  - 请求/响应完整内容
  - 执行日志（从 WARNING 到 DEBUG 全级别）
  - 断言错误信息 + 完整堆栈
- 点击用例名称切换展开/折叠，点击附件按钮查看详情

### 4. 失败日志自动捕获

[test_api/conftest.py](test_api/conftest.py) 中的 `pytest_runtest_makereport` hook：

测试失败时自动在报告中附加：
- **Execution Log** — 本用例的完整执行日志
- **Last Request / Response** — 最后一次 HTTP 调用的请求和响应体
- **Test Description** — 用例的 docstring 说明

### 5. 数据驱动

测试数据与代码分离，用例从 JSON 文件加载：

```json
// test_data/login_cases.json
[
  { "name": "valid_admin", "username": "admin", "password": "password123", "expect_success": true },
  { "name": "wrong_password", "username": "admin", "password": "wrongpass", "expect_success": false }
]
```

```python
# 测试方法中遍历
def test_login_data_driven(self, http_client, login_test_cases):
    for case in login_test_cases:
        with allure.step(f"Case: {case['name']}"):
            resp = http_client.post("/api/login", json={...})
            if case["expect_success"]:
                assert resp.status_code == 200
            else:
                assert resp.status_code == 401
```

## 标记说明

| 标记 | 说明 |
|------|------|
| `@pytest.mark.smoke` | 冒烟测试（关键路径） |
| `@pytest.mark.regression` | 回归测试 |
| `@pytest.mark.negative` | 反向用例 |

在 `pytest.ini` 中注册，使用 `pytest -m <marker>` 筛选。

## 被测接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/login` | 用户登录，返回 token | 无 |
| GET | `/api/query` | 按 keyword/category 筛选商品 | Bearer token |
| GET | `/api/health` | 健康检查 | 无 |

## 依赖

```
flask>=2.0.0
pytest>=7.0.0
allure-pytest>=2.13.0
requests>=2.28.0
```

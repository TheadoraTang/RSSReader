# Week16 GentleCold - Summary Agent 后端系统

## 本周负责范围

- Summary Agent 核心开发。
- LLM Provider 抽象层。
- OpenAI-Compatible API 接入。
- vLLM / Ollama 本地模型接入配置。
- Summary LLM 用量统计。

## 主要实现

### 1. Summary Agent

新增 `backend/app/services/summary_agent.py`：

- 从文章标题、`cleaned_markdown`、`cleaned_html`、`raw_html`、RSS `summary` 中构造摘要输入。
- 优先使用清洗后的 Markdown，避免把 HTML 标签直接喂给模型。
- 对超长正文做 12000 字符截断，避免一次请求过大。
- 统一输出中文结构化摘要：一句话概览、关键要点、关键词。
- 调用失败时将连接失败、鉴权失败、模型不存在等错误转成可读提示。

### 2. Provider 抽象与配置

新增 `llm_providers` 表，支持以下 provider 类型：

- `openai_compatible`
- `vllm`
- `ollama`
- `custom`

后端新增接口：

- `GET /api/ai/providers`
- `POST /api/ai/providers`
- `PUT /api/ai/providers/{provider_id}`
- `DELETE /api/ai/providers/{provider_id}`
- `POST /api/ai/summary/{article_id}`

Provider 记录字段包括：

- `name`
- `provider_type`
- `base_url`
- `api_key`
- `model`
- `enabled`
- `is_default`

摘要调用统一走 OpenAI-compatible Chat Completions 协议，因此 vLLM 与 Ollama 只要暴露 `/v1/chat/completions` 即可复用同一套 agent。

### 3. vLLM / Qwen3-8B 本地模型

前端 AI 设置页提供 `vLLM Qwen3-8B` 快速模板：

- Provider: `Local vLLM Qwen3-8B`
- 类型: `vllm`
- Base URL: `http://127.0.0.1:8001/v1`
- Model: `Qwen/Qwen3-8B`

Web/Electron 开发时 FastAPI 常用 `8000` 端口，因此模板默认使用 `8001`，避免和后端冲突。如果单独运行 vLLM 且没有端口冲突，也可以使用 vLLM 常见默认端口 `8000`。

ModelScope 下载与 vLLM 启动示例：

```bash
pip install modelscope vllm
modelscope download --model Qwen/Qwen3-8B --local_dir ./models/Qwen3-8B
vllm serve ./models/Qwen3-8B \
  --served-model-name Qwen/Qwen3-8B \
  --host 127.0.0.1 \
  --port 8001
```

然后在 RSSReader 的 AI 设置中选择 `vLLM Qwen3-8B` 模板，确认 Base URL 为：

```text
http://127.0.0.1:8001/v1
```

### 4. Ollama / Qwen3-8B 本地模型

前端 AI 设置页提供 `Ollama` 快速模板：

- Provider: `Local Ollama`
- 类型: `ollama`
- Base URL: `http://127.0.0.1:11434/v1`
- API Key: `ollama`
- Model: `qwen3:8b`

启动示例：

```bash
ollama pull qwen3:8b
ollama serve
```

Ollama 的 OpenAI-compatible endpoint 通常是：

```text
http://127.0.0.1:11434/v1
```

### 5. 前端接入

更新 `frontend/src/views/AISettingsView.vue`：

- 将原“Provider 配置界面预留”改为真实 CRUD。
- 支持 vLLM、Ollama、OpenAI-compatible 三类快速模板。
- 支持设置默认 provider。
- Provider 表格展示名称、类型、模型、Base URL、启用/默认状态。

更新 `frontend/src/views/ReaderView.vue`：

- 摘要按钮改为 provider 下拉菜单。
- 可选择默认 provider 或指定 provider 生成摘要。
- 摘要结果展示在文章正文下方。
- 展示本次调用的输入 / 输出 token。

更新 `frontend/src/views/StatsView.vue`：

- 统计页继续展示总调用数、输入 token、输出 token。
- 新增按功能统计。
- 新增按 provider + model 统计。

### 6. 用量统计

`ai_results` 表现在记录：

- `provider`
- `model`
- `input_tokens`
- `output_tokens`

`GET /api/stats/llm` 返回：

- `total_articles`
- `total_calls`
- `input_tokens`
- `output_tokens`
- `by_feature`
- `by_provider`

如果 OpenAI-compatible provider 返回 `usage.prompt_tokens` 和 `usage.completion_tokens`，系统直接使用真实用量；如果 provider 没返回 usage，Summary Agent 会做保守 token 估算，保证统计页不为空。

## 实际测试记录

### 单元测试

命令：

```bash
PYTHONPATH=backend /Users/a1234/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest discover -s backend/tests
```

结果：

```text
Ran 22 tests in 0.036s
OK
```

新增测试：

- `backend/tests/test_summary_agent.py`
  - 验证 Summary Agent 优先使用清洗后的 Markdown。
  - 验证 OpenAI-compatible 调用、模型名传递和 usage 读取。
- `backend/tests/test_llm_provider_repository.py`
  - 验证 provider CRUD。
  - 验证默认 provider。
  - 验证摘要结果的 token 用量聚合。

### 前端类型检查

命令：

```bash
cd frontend
./node_modules/.bin/vue-tsc --noEmit --pretty false
```

结果：通过，无类型错误。

说明：`npm run build` 在当前 Node/Vite 环境中曾出现 Vite build 进程长时间不输出的问题；单独 `vue-tsc` 已验证类型层面，Vite dev server 可以正常启动并被 Electron 加载。

### API 端到端测试

使用本地 OpenAI-compatible 测试服务模拟 vLLM/Qwen3-8B：

- Base URL: `http://127.0.0.1:18000/v1`
- Model: `Qwen/Qwen3-8B`

验证内容：

- 创建 `vllm` provider。
- 创建 `ollama` provider。
- 对文章调用 `POST /api/ai/summary/{article_id}`。
- 检查 `GET /api/stats/llm`。

结果：

- vLLM 类型 provider 调用成功，返回摘要并记录 `123` input tokens / `45` output tokens。
- Ollama 类型 provider 调用成功，返回摘要并记录 `123` input tokens / `45` output tokens。
- 统计接口能按 `summary`、provider、model 聚合。

### Electron 实际软件测试

已打开实际 Electron 应用验证：

1. 使用 `npx electron .` 启动桌面端。
2. Electron 主进程自动启动 FastAPI 后端，实际后端地址为 `http://127.0.0.1:51474`。
3. 确认 preload 注入的 `apiBaseUrl` 生效，前端请求进入 Electron 后端。
4. 在 Electron 应用 AI 设置页中保存 `Local vLLM Qwen3-8B` provider。
5. 通过 Electron 后端实际订阅 RSS：

```text
https://hnrss.org/frontpage
```

结果：

- RSS 源添加成功：`Feed added and synced successfully.`
- 当前 Electron 数据库中有 `21` 篇真实订阅文章。
- 对真实订阅文章调用 Summary Agent 成功。
- 摘要结果成功保存，统计接口返回：

```json
{
  "total_articles": 21,
  "total_calls": 1,
  "input_tokens": 222,
  "output_tokens": 66,
  "by_feature": [
    { "name": "summary", "calls": 1, "tokens": 288 }
  ],
  "by_provider": [
    {
      "provider": "Local vLLM Qwen3-8B",
      "model": "Qwen/Qwen3-8B",
      "calls": 1,
      "input_tokens": 222,
      "output_tokens": 66
    }
  ]
}
```

## 遇到的问题与解决

### 1. 上游仓库地址修正

最初 `GentleCold/RSSReader` 仓库只有文档分支，没有 `develop` 和完整应用代码。后来确认真正上游为：

```text
https://github.com/TheadoraTang/RSSReader
```

解决方式：

- 添加 `upstream` 指向 TheadoraTang/RSSReader。
- 从 `upstream/develop` 切出 `week16-summary-agent` 分支继续开发。

### 2. Python 3.14 本机环境不可用

本机 Homebrew Python 3.14 的 `pyexpat` 动态库报错，导致 `venv` / `pip` 无法正常使用。

解决方式：

- 使用 Codex bundled Python：

```text
/Users/a1234/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
```

### 3. Electron 依赖安装超时

首次 `npm install` 下载 Electron 二进制时出现 `read ETIMEDOUT`。

解决方式：

```bash
ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/ npm install
```

重试后安装成功。

### 4. Electron 数据库路径大小写差异

手工准备测试数据时最初写入：

```text
~/Library/Application Support/RSSReader/app.db
```

但 Electron 实际使用：

```text
~/Library/Application Support/rssreader/app.db
```

解决方式：

- 通过 `GET /api/health` 确认真正数据库路径。
- 后续测试全部使用 Electron 后端 API 或正确数据库路径。

### 5. vLLM 默认端口与 FastAPI 开发端口冲突

FastAPI Web 开发常用 `8000`，vLLM 示例也常用 `8000`。

解决方式：

- 前端 vLLM 模板默认改为 `http://127.0.0.1:8001/v1`。
- 文档说明如无端口冲突也可手动改为 `8000/v1`。

## 当前限制

- 本次没有在本机真实加载 Qwen3-8B 权重进行推理，因为下载与运行 8B 模型依赖本机显存/内存和时间成本；已提供 ModelScope 下载与 vLLM 启动命令。
- 软件链路已用本地 OpenAI-compatible 服务实际验证，能够证明 RSSReader 对 vLLM/Ollama/OpenAI-compatible provider 的调用、摘要保存和用量统计逻辑可用。
- RAG 问答配置仍沿用原有模块，本次只完成 Summary Agent 相关 provider 和统计。

## 后续建议

- 在具备 GPU 或足够内存的机器上运行真实 `Qwen/Qwen3-8B` vLLM 服务，执行同样的 Electron 摘要测试。
- 后续 Translation Agent 可以复用本次 `llm_providers` 表和 provider 调用逻辑。
- 可增加 provider “测试连接”按钮，保存前检查 `/v1/models` 或执行一次轻量 chat completion。

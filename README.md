# QQ Mail Agent

<p align="center">
  <a href="#中文"><strong>中文</strong></a>
  &nbsp;|&nbsp;
  <a href="#english"><strong>English</strong></a>
</p>

---

## 中文

基于 LangGraph + LangChain 的 QQ 邮箱智能处理 Agent。它通过 IMAP 读取 QQ 邮箱邮件，将邮件解析为结构化输入，提交给 LangGraph 工作流进行分类和处理；需要回复时生成草稿，并在人工确认后通过 SMTP 发出邮件。

### 功能

- QQ 邮箱 IMAP 收信
- QQ 邮箱 SMTP 发信
- 邮件分类：`ignore`、`notify`、`respond`
- LangGraph thread/run 工作流处理
- Tool calling 邮箱工具调用
- Human-in-the-loop 人工确认
- LangGraph memory 用户偏好记忆
- LangSmith tracing 调试与追踪

### 安装

```shell
git clone https://github.com/haciniemiku/qqmailagent.git
cd qqmailagent
uv sync --extra dev
source .venv/bin/activate
cp .env.example .env
```

如果不使用 `uv`：

```shell
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -e .
```

### 配置

编辑 `.env`：

```shell
OPENAI_API_KEY="<OpenAI-API-Key>"

LANGSMITH_TRACING=true
LANGSMITH_API_KEY="<LangSmith-API-Key>"
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_PROJECT="ambient-agent-101"

QQ_EMAIL="your-email@qq.com"
QQ_EMAIL_AUTH_CODE="your-qq-mail-authorization-code"
QQ_IMAP_HOST="imap.qq.com"
QQ_IMAP_PORT="993"
QQ_SMTP_HOST="smtp.qq.com"
QQ_SMTP_PORT="465"
QQ_MAILBOX="INBOX"
```

请使用 QQ 邮箱授权码，不要使用 QQ 密码。

### 启动

启动本地 LangGraph 服务：

```shell
langgraph dev
```

另开一个终端，拉取最近邮件：

```shell
source .venv/bin/activate
python src/email_assistant/tools/qqmail/run_ingest.py --email your-email@qq.com --minutes-since 1440 --include-read
```

QQ 邮箱图名称：

```text
email_assistant_hitl_memory_qqmail
```

### 常用命令

只处理最近 2 小时未读邮件：

```shell
python src/email_assistant/tools/qqmail/run_ingest.py --email your-email@qq.com --minutes-since 120
```

处理最近 24 小时已读和未读邮件：

```shell
python src/email_assistant/tools/qqmail/run_ingest.py --email your-email@qq.com --minutes-since 1440 --include-read
```

只处理一封邮件，用于测试：

```shell
python src/email_assistant/tools/qqmail/run_ingest.py --email your-email@qq.com --minutes-since 1440 --include-read --early
```

跳过发送者和线程过滤：

```shell
python src/email_assistant/tools/qqmail/run_ingest.py --email your-email@qq.com --minutes-since 1440 --include-read --skip-filters
```

### 查看结果

LangGraph Studio:

```text
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

Agent Inbox:

```text
https://dev.agentinbox.ai/
```

连接信息：

```text
Deployment URL: http://127.0.0.1:2024
Assistant / Graph ID: email_assistant_hitl_memory_qqmail
```

### 数据流

```text
QQ Mail
  ↓ IMAP
fetch_group_emails()
  ↓ email_data
run_ingest.py
  ↓ create/reuse LangGraph thread, create run
email_assistant_hitl_memory_qqmail
  ↓
triage_router
  ├── ignore  → END
  ├── notify  → human review
  └── respond → response_agent → human approval → SMTP send
```

### 安全提示

`.env` 已被 Git 忽略，不要提交 API key、LangSmith key 或 QQ 邮箱授权码。

[Back to top](#qq-mail-agent)

---

## English

A LangGraph + LangChain email agent for QQ Mail. It reads emails through IMAP, converts them into structured inputs, sends them into a LangGraph workflow for triage and processing, drafts replies when needed, and sends emails through SMTP only after human approval.

### Features

- Read QQ Mail through IMAP
- Send replies through QQ Mail SMTP
- Triage emails into `ignore`, `notify`, and `respond`
- Process emails with LangGraph thread/run workflow
- Use tool calling for mailbox operations
- Require human approval before sending emails
- Store user preferences with LangGraph memory
- Trace and debug runs with LangSmith

### Installation

```shell
git clone https://github.com/haciniemiku/qqmailagent.git
cd qqmailagent
uv sync --extra dev
source .venv/bin/activate
cp .env.example .env
```

If you do not use `uv`:

```shell
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -e .
```

### Configuration

Edit `.env`:

```shell
OPENAI_API_KEY="<OpenAI-API-Key>"

LANGSMITH_TRACING=true
LANGSMITH_API_KEY="<LangSmith-API-Key>"
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_PROJECT="ambient-agent-101"

QQ_EMAIL="your-email@qq.com"
QQ_EMAIL_AUTH_CODE="your-qq-mail-authorization-code"
QQ_IMAP_HOST="imap.qq.com"
QQ_IMAP_PORT="993"
QQ_SMTP_HOST="smtp.qq.com"
QQ_SMTP_PORT="465"
QQ_MAILBOX="INBOX"
```

Use a QQ Mail authorization code, not your QQ password.

### Run

Start the local LangGraph server:

```shell
langgraph dev
```

In another terminal, ingest recent QQ Mail messages:

```shell
source .venv/bin/activate
python src/email_assistant/tools/qqmail/run_ingest.py --email your-email@qq.com --minutes-since 1440 --include-read
```

The QQ Mail graph name is:

```text
email_assistant_hitl_memory_qqmail
```

### Common Commands

Only process unread emails from the last 2 hours:

```shell
python src/email_assistant/tools/qqmail/run_ingest.py --email your-email@qq.com --minutes-since 120
```

Include read emails from the last 24 hours:

```shell
python src/email_assistant/tools/qqmail/run_ingest.py --email your-email@qq.com --minutes-since 1440 --include-read
```

Process only one email for testing:

```shell
python src/email_assistant/tools/qqmail/run_ingest.py --email your-email@qq.com --minutes-since 1440 --include-read --early
```

Skip sender and thread filters:

```shell
python src/email_assistant/tools/qqmail/run_ingest.py --email your-email@qq.com --minutes-since 1440 --include-read --skip-filters
```

### Inspect Results

LangGraph Studio:

```text
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

Agent Inbox:

```text
https://dev.agentinbox.ai/
```

Use:

```text
Deployment URL: http://127.0.0.1:2024
Assistant / Graph ID: email_assistant_hitl_memory_qqmail
```

### Data Flow

```text
QQ Mail
  ↓ IMAP
fetch_group_emails()
  ↓ email_data
run_ingest.py
  ↓ create/reuse LangGraph thread, create run
email_assistant_hitl_memory_qqmail
  ↓
triage_router
  ├── ignore  → END
  ├── notify  → human review
  └── respond → response_agent → human approval → SMTP send
```

### Security

`.env` is ignored by Git and should never be committed. Do not commit API keys, LangSmith keys, or QQ Mail authorization codes.

[Back to top](#qq-mail-agent)

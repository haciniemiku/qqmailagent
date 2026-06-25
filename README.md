# QQ Mail Agent / QQ 邮箱智能处理 Agent

基于 LangGraph + LangChain 的 QQ 邮箱智能处理 Agent。它通过 IMAP 读取 QQ 邮箱邮件，将邮件解析为结构化输入，提交给 LangGraph 工作流进行分类和处理；需要回复时生成草稿，并在人工确认后通过 SMTP 发出邮件。

A LangGraph + LangChain email agent for QQ Mail. It reads emails through IMAP, converts them into structured inputs, sends them into a LangGraph workflow for triage and processing, drafts replies when needed, and sends emails through SMTP only after human approval.

## 功能 / Features

- QQ 邮箱 IMAP 收信 / Read QQ Mail through IMAP
- QQ 邮箱 SMTP 发信 / Send replies through SMTP
- 邮件分类：`ignore`、`notify`、`respond` / Email triage into `ignore`, `notify`, and `respond`
- LangGraph thread/run 工作流处理 / LangGraph thread/run based workflow
- Tool calling 邮箱工具调用 / Tool calling for mailbox operations
- Human-in-the-loop 人工确认 / Human approval before sending
- LangGraph memory 用户偏好记忆 / User preference memory
- LangSmith tracing 调试与追踪 / LangSmith tracing for debugging

## 安装 / Installation

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

## 配置 / Configuration

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

请使用 QQ 邮箱授权码，不要使用 QQ 密码。

## 启动 / Run

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

## 常用命令 / Common Commands

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

Skip sender/thread filters:

```shell
python src/email_assistant/tools/qqmail/run_ingest.py --email your-email@qq.com --minutes-since 1440 --include-read --skip-filters
```

## 查看结果 / Inspect Results

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

## 数据流 / Data Flow

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

## 安全提示 / Security

`.env` is ignored by Git and should never be committed.

`.env` 已被 Git 忽略，不要提交 API key、LangSmith key 或 QQ 邮箱授权码。

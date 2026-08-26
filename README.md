# XPUOJ 自动化评测与提交工具

针对 XPUOJ（面向 GPU/XPU 算子评测平台）的自动化代码提交与测评结果查询工具。

## 功能特性

- **Token 自动缓存与刷新**：支持账号密码登录与本地 JWT 令牌缓存，Token 失效自动重登。
- **题目查询**：查看比赛列表与指定比赛的题目详情。
- **代码提交与即时测评**：支持指定语言（如 `cuda-h800`、`triton-h800` 等）提交，并可自动轮询评测进度与得分详情（包括各测试点耗时、`score_ratio` 等指标）。
- **批量/周期性提交**：支持多题目批量轮询提交测试。

## 快速上手

### 1. 环境准备

推荐使用 [uv](https://github.com/astral-sh/uv) 管理 Python 依赖：

```bash
# 同步依赖环境
uv sync
```

### 2. 配置账号

复制配置模板并填入您的账号与密码：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`：

```yaml
email: "your_email@example.com"
password: "your_password"
contest_id: 4
problem_order: 1
```

> **提示**：`config.yaml` 和缓存的 `token.json` 已在 `.gitignore` 中被忽略，不会被提交至代码仓库。

## 使用方法

### 单次提交代码

```bash
# 提交代码到比赛 4 题目 1（默认 triton-h800），并轮询等待评测结果
uv run client.py submit solution.py --wait

# 指定比赛 ID、题目序号与语言
uv run client.py submit kernel.cu --contest 4 --problem 1 --language cuda-h800 --wait
```

### 查询比赛题目

```bash
# 列出比赛中的题目
uv run client.py list 4
```

### 查询提交详情

```bash
# 查看指定提交记录的状态与评测数据
uv run client.py status <SUBMISSION_ID>
```

### 批量/定时轮询提交

编辑 `auto_submit.py` 中的 `SUBMISSIONS` 列表及提交间隔，执行：

```bash
uv run auto_submit.py
```

## 相关文档

- [analyze.md](analyze.md)：XPUOJ 后端 API 逆向分析及数据结构说明。

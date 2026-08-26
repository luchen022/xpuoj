"""
XPUOJ 自动化脚本 - 第三阶段
基于逆向分析构建的完整自动化流程：登录 → 提交代码 → 查看测评结果

使用方法:
    uv run monitor.py                    # 交互式登录
    uv run monitor.py --auto             # 使用 config.yaml 自动登录
    uv run monitor.py submit <file>      # 直接提交代码文件到比赛4题目1
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
#     "pyyaml",
# ]
# ///

import json
import sys
import time
import argparse
import requests


API_BASE = "https://sd629vuj4f7uh2cscrbe0.apigateway-cn-beijing.volceapi.com"
TOKEN_FILE = "token.json"


class XPUOJClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self.token = None
        self._email = None
        self._password = None

    def save_token(self):
        """持久化 token"""
        with open(TOKEN_FILE, "w") as f:
            json.dump({"token": self.token, "email": self._email}, f)

    def load_token(self) -> bool:
        """加载已保存的 token"""
        try:
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
            self.token = data.get("token")
            self._email = data.get("email")
            if self.token:
                self.session.headers["Authorization"] = f"Bearer {self.token}"
                return True
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return False

    def check_token(self) -> bool:
        """验证 token 是否有效"""
        if not self.token:
            return False
        try:
            resp = self.session.get(f"{API_BASE}/api/auth/getSessionInfo", params={
                "token": self.token,
            })
            data = resp.json()
            # 有效 token 会返回用户信息，无效的会返回 error
            if "error" in data or data.get("error"):
                return False
            # 检查是否有 username（说明是已登录用户）
            user = data.get("user", {})
            if user and user.get("username"):
                print(f"[✓] Token 有效，用户: {user['username']}")
                return True
            # 可能返回的是默认配置，没有 user 字段也算有效（token 只是过期）
            return True
        except Exception:
            return False

    def login(self, email: str, password: str) -> bool:
        """登录并获取 token"""
        self._email = email
        self._password = password
        resp = self.session.post(f"{API_BASE}/api/auth/login", json={
            "email": email,
            "password": password,
        })
        data = resp.json()
        if "error" in data:
            print(f"[✗] 登录失败: {data['error']}")
            return False

        self.token = data.get("token")
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            self.save_token()
            print(f"[✓] 登录成功，token: {self.token[:30]}...")
            return True
        else:
            print(f"[✗] 登录响应中未找到 token: {data}")
            return False

    def ensure_login(self, email: str = None, password: str = None) -> bool:
        """确保已登录：优先用缓存 token，过期则重新登录"""
        # 1. 尝试加载缓存 token
        if self.load_token():
            print(f"[i] 发现缓存 token，验证中...")
            if self.check_token():
                return True
            print("[!] Token 已过期，重新登录...")

        # 2. 需要登录
        if email and password:
            return self.login(email, password)
        elif self._email and self._password:
            return self.login(self._email, self._password)
        else:
            return False

    def get_contest_problems(self, contest_id: int) -> list:
        """获取比赛题目列表"""
        resp = self.session.post(f"{API_BASE}/api/contest/getContestProblems", json={
            "contestId": contest_id,
            "locale": "zh_CN",
        })
        data = resp.json()
        if "error" in data:
            print(f"[✗] 获取题目列表失败: {data['error']}")
            return []
        return data.get("data", data) if isinstance(data, dict) else data

    def get_problem(self, contest_id: int, problem_order: int) -> dict:
        """获取题目详情"""
        resp = self.session.post(f"{API_BASE}/api/contest/play/getProblem", json={
            "contestId": contest_id,
            "problemOrder": problem_order,
            "localizedContentsOfLocale": "zh_CN",
            "samples": True,
            "judgeInfo": True,
            "judgeInfoToBePreprocessed": True,
            "lastSubmissionAndLastAcceptedSubmission": True,
        })
        return resp.json()

    def submit_code(self, contest_id: int, problem_order: int, code: str, language: str = "triton-h800") -> dict:
        """提交代码"""
        resp = self.session.post(f"{API_BASE}/api/contest/play/submit", json={
            "contestId": contest_id,
            "problemOrder": problem_order,
            "content": {
                "code": code,
                "language": language,
                "compileAndRunOptions": {},
            },
            "uploadInfo": None,
        })
        return resp.json()

    def get_submission_detail(self, submission_id: str) -> dict:
        """查询提交结果"""
        resp = self.session.post(f"{API_BASE}/api/submission/getSubmissionDetail", json={
            "submissionId": submission_id,
            "locale": "zh_CN",
        })
        return resp.json()

    def get_submission_detail_raw(self, submission_id: str) -> str:
        """查询提交结果原始响应"""
        resp = self.session.post(f"{API_BASE}/api/submission/getSubmissionDetail", json={
            "submissionId": submission_id,
            "locale": "zh_CN",
        })
        return resp.text

    def query_submissions(self, contest_id: int, max_id: int = None, take_count: int = 10) -> dict:
        """查询提交列表"""
        body = {
            "locale": "zh_CN",
            "contestId": contest_id,
            "takeCount": take_count,
        }
        if max_id:
            body["maxId"] = max_id
        resp = self.session.post(f"{API_BASE}/api/contest/play/querySubmissions", json=body)
        return resp.json()

    def wait_for_result(self, submission_id: str, timeout: int = 180, poll_interval: float = 50.0) -> dict:
        """轮询等待测评结果"""
        print(f"[⏳] 等待测评结果 (submission: {submission_id})...")
        start = time.time()
        while time.time() - start < timeout:
            result = self.get_submission_detail(submission_id)

            # 状态在 progress 字段中
            progress = result.get("progress") or {}
            meta = result.get("meta") or {}
            progress_type = progress.get("progressType", "")
            status = progress.get("status", "") or meta.get("status", "")

            if progress_type == "Finished" or status not in ["", "Waiting", "Pending", "Compiling", "Judging", "Running"]:
                print_result(result)
                return result

            time.sleep(poll_interval)

        print(f"[⚠] 超时 ({timeout}s)，请手动查看结果")
        return {}


def print_result(result: dict):
    """格式化输出测评结果"""
    import re
    meta = result.get("meta", {})
    progress = result.get("progress", {})

    status = progress.get("status", "") or meta.get("status", "?")
    score = progress.get("score", meta.get("score", "?"))
    display_score = progress.get("displayScore", meta.get("displayScore", "?"))
    problem = meta.get("problemTitle", "?")
    time_used = meta.get("timeUsed", 0)

    print(f"\n{'='*60}")
    print(f"  题目: {problem}")
    print(f"  状态: {status}")
    print(f"  分数: {score} (显示分: {display_score})")
    print(f"  耗时: {time_used}ms  内存: {meta.get('memoryUsed', 0)//1024}MB")
    print(f"{'='*60}")

    # 各测试点
    testcases = progress.get("testcaseResult", {})
    if testcases:
        print(f"\n  测试点结果 ({len(testcases)} 个):")
        print(f"  {'文件':<10} {'状态':<12} {'耗时':>8} {'显示分':>6} {'score_ratio':>12}")
        print(f"  {'-'*50}")
        for tc_hash, tc in sorted(testcases.items(), key=lambda x: x[1].get("testcaseInfo", {}).get("inputFile", "") or ""):
            tc_status = tc.get("status", "?")
            tc_time = tc.get("time", 0)
            tc_score = tc.get("displayScore", tc.get("score", "?"))
            tc_input = tc.get("testcaseInfo", {}).get("inputFile", tc_hash[:8]) or "sample"
            # 解析 score_ratio
            user_err = tc.get("userError", "")
            ratio = ""
            if "score_ratio" in user_err:
                m = re.search(r'"score_ratio":([0-9.]+)', user_err)
                if m:
                    ratio = f"{float(m.group(1)):.4f}"
            print(f"  {tc_input:<10} {tc_status:<12} {tc_time:>6}ms {tc_score:>6} {ratio:>12}")
    print()


def load_config() -> dict:
    """从 config.yaml 加载配置"""
    try:
        import yaml
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}


def interactive_login(client: XPUOJClient) -> bool:
    """交互式登录"""
    email = input("邮箱: ").strip()
    password = input("密码: ").strip()
    return client.login(email, password)


def main():
    parser = argparse.ArgumentParser(description="XPUOJ 自动化工具")
    parser.add_argument("--auto", action="store_true", help="使用 config.yaml 自动登录")
    parser.add_argument("--contest", type=int, default=4, help="比赛 ID (默认 4)")
    parser.add_argument("--problem", type=int, default=1, help="题目序号 (默认 1)")
    subparsers = parser.add_subparsers(dest="command")

    # submit 子命令
    submit_parser = subparsers.add_parser("submit", help="提交代码文件")
    submit_parser.add_argument("file", help="代码文件路径")
    submit_parser.add_argument("--contest", type=int, default=4, help="比赛 ID")
    submit_parser.add_argument("--problem", type=int, default=1, help="题目序号")
    submit_parser.add_argument("--language", default="triton-h800", help="语言 (默认 triton-h800)")
    submit_parser.add_argument("--wait", action="store_true", help="等待测评结果")

    # list 子命令
    list_parser = subparsers.add_parser("list", help="列出比赛题目")
    list_parser.add_argument("contest_id", type=int, nargs="?", default=None, help="比赛 ID (默认用 config.yaml 中的值)")

    # status 子命令
    status_parser = subparsers.add_parser("status", help="查看提交状态")
    status_parser.add_argument("submission_id", help="提交 ID")

    args = parser.parse_args()

    client = XPUOJClient()
    config = load_config()

    # 登录：优先用缓存 token，过期则自动重新登录
    if args.auto:
        if not config.get("email") or not config.get("password"):
            print("[✗] config.yaml 中缺少 email 或 password")
            sys.exit(1)
        if not client.ensure_login(config["email"], config["password"]):
            sys.exit(1)
    else:
        # 交互模式也先尝试缓存
        if client.load_token() and client.check_token():
            pass  # token 有效，跳过登录
        else:
            if not interactive_login(client):
                sys.exit(1)

    # 执行命令
    if args.command == "submit":
        with open(args.file, "r") as f:
            code = f.read()
        print(f"[→] 提交代码到 比赛{args.contest} 题目{args.problem} ({len(code)} 字符, 语言: {args.language})")
        result = client.submit_code(args.contest, args.problem, code, args.language)
        print(f"[←] 响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

        # 提取 submissionId
        data = result.get("data", result)
        submission_id = None
        if isinstance(data, dict):
            submission_id = data.get("submissionId") or data.get("id")
        elif isinstance(data, str):
            submission_id = data

        if submission_id and args.wait:
            client.wait_for_result(str(submission_id))

    elif args.command == "list":
        contest_id = args.contest_id or config.get("contest_id", 4)
        problems = client.get_contest_problems(contest_id)
        print(json.dumps(problems, ensure_ascii=False, indent=2))

    elif args.command == "status":
        print(client.get_submission_detail_raw(args.submission_id))

    else:
        # 默认：交互模式
        print("[i] 已登录，可用命令:")
        print("  uv run monitor.py list 4              # 列出比赛4的题目")
        print("  uv run monitor.py submit code.py       # 提交代码")
        print("  uv run monitor.py submit code.py --wait # 提交并等待结果")
        print("  uv run monitor.py status 5369           # 查看提交状态")


if __name__ == "__main__":
    main()

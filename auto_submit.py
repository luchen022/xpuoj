# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
#     "pyyaml",
# ]
# ///

"""
XPUOJ 自动重复提交脚本 (每 2 分钟提交 题目1, 2, 3)

使用方法:
    cd /mnt/d/Projects/xpuoj && uv run auto_submit.py
"""

import os
import sys
import time
from datetime import datetime
from monitor import XPUOJClient, load_config

SUBMISSIONS = [
    {
        "file": "/mnt/d/Projects/timuyi/privet/p1.cu",
        "problem": 1,
        "language": "cuda-h800",
    },
    {
        "file": "/mnt/d/Projects/timuyi/privet/p2.py",
        "problem": 2,
        "language": "triton-h800",
    },
    {
        "file": "/mnt/d/Projects/timuyi/privet/p3.py",
        "problem": 3,
        "language": "triton-h800",
    },
]

INTERVAL_SECONDS = 30  # 2 分钟休眠间隔


def auto_submit():
    client = XPUOJClient()
    config = load_config()

    email = config.get("email")
    password = config.get("password")
    contest_id = config.get("contest_id", 4)

    print("==================================================")
    print("   XPUOJ 自动批量提交脚本 (每 2 分钟循环提交)")
    print("==================================================")
    for sub in SUBMISSIONS:
        print(f"  - 题目 {sub['problem']}: {sub['file']} ({sub['language']})")
    print("==================================================\n")

    round_count = 1

    while True:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now_str}] 🚀 开始第 {round_count} 轮提交...")

        # 自动利用 token.json 验证；若失效则利用 config.yaml 重新登录
        if not client.ensure_login(email, password):
            print("[✗] 登录失败（请检查 token.json 或 config.yaml），10 秒后重试...")
            time.sleep(10)
            continue

        for item in SUBMISSIONS:
            filepath = item["file"]
            prob_id = item["problem"]
            lang = item["language"]

            if not os.path.exists(filepath):
                print(f"  [!] 文件不存在: {filepath}，跳过")
                continue

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    code = f.read()

                print(f"  [→] 提交 题目{prob_id} | 语言: {lang} | 代码长度: {len(code)} 字节")
                result = client.submit_code(
                    contest_id=contest_id,
                    problem_order=prob_id,
                    code=code,
                    language=lang
                )

                sub_id = None
                data = result.get("data", result)
                if isinstance(data, dict):
                    sub_id = data.get("submissionId") or data.get("id")
                elif isinstance(data, str):
                    sub_id = data

                if sub_id:
                    print(f"      [✓] 提交成功! Submission ID: {sub_id}")
                else:
                    print(f"      [!] 响应: {result}")

            except Exception as e:
                print(f"      [✗] 提交题目 {prob_id} 出错: {e}")

        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ 提交完成，休眠 {INTERVAL_SECONDS} 秒（2 分钟）后进行下一轮提交...\n")
        time.sleep(INTERVAL_SECONDS)
        round_count += 1


if __name__ == "__main__":
    auto_submit()

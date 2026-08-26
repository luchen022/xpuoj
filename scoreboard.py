#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
#     "pyyaml",
# ]
# ///

"""
XPUOJ 排行榜查询脚本
获取指定比赛的排行榜，并在终端格式化输出对齐表格，支持导出 JSON/CSV。

使用方法:
    uv run scoreboard.py                 # 查询默认比赛排行榜
    uv run scoreboard.py -c 13           # 查询指定比赛 (如 13) 的排行榜
    uv run scoreboard.py -n 10           # 只看前 10 名
    uv run scoreboard.py --json          # 打印 JSON 原始数据
    uv run scoreboard.py --csv rank.csv  # 导出到 CSV 文件
"""

import sys
import json
import csv
import argparse
import unicodedata
from datetime import datetime
from client import XPUOJClient, load_config


def get_display_width(text: str) -> int:
    """计算字符串在终端的实际显示宽度（支持中文字符双宽计算）"""
    return sum(2 if unicodedata.east_asian_width(c) in ("F", "W") else 1 for c in str(text))


def pad_str(text: str, target_width: int, align: str = "left") -> str:
    """根据终端显示宽度进行对齐填充"""
    text_str = str(text) if text is not None else ""
    w = get_display_width(text_str)
    pad = max(0, target_width - w)
    if align == "right":
        return " " * pad + text_str
    elif align == "center":
        left = pad // 2
        return " " * left + text_str + " " * (pad - left)
    return text_str + " " * pad


def fetch_all_scoreboard(client: XPUOJClient, contest_id: int, page_size: int = 50) -> dict:
    """分页获取比赛全部排行榜数据"""
    skip = 0
    all_records = []
    total = 0

    while True:
        data = client.get_scoreboard(contest_id, skip_count=skip, take_count=page_size)
        if "error" in data:
            print(f"[✗] 获取排行榜失败: {data['error']}", file=sys.stderr)
            return {"scoreboard": [], "total": 0}

        records = data.get("scoreboard", [])
        total = data.get("total", len(records))
        all_records.extend(records)

        skip += len(records)
        if skip >= total or not records:
            break

    return {"scoreboard": all_records, "total": total}


def format_time(iso_str: str) -> str:
    """将 ISO 时间格式转换为简短的 MM-DD HH:MM"""
    if not iso_str:
        return "-"
    try:
        # 处理类似 2026-08-23T18:44:20.000Z
        iso_clean = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_clean)
        # 转为本地时间（如需要显示简化版）
        return dt.strftime("%m-%d %H:%M")
    except Exception:
        return iso_str[:16].replace("T", " ")


def print_scoreboard_table(scoreboard_data: dict, contest_id: int, top: int = None, current_user: str = None):
    """格式化打印终端对齐表格"""
    records = scoreboard_data.get("scoreboard", [])
    total = scoreboard_data.get("total", len(records))

    if top and top > 0:
        records = records[:top]

    if not records:
        print(f"[i] 比赛 {contest_id} 暂无榜单数据。")
        return

    # 扫描所有题目编号（P1, P2, ...）
    problem_orders = set()
    for item in records:
        for p in item.get("problemScores", []):
            if "order" in p:
                problem_orders.add(p["order"])
    sorted_problems = sorted(problem_orders) if problem_orders else [1]

    # 列宽定义
    rank_w = 6
    user_w = 16
    nick_w = 14
    total_w = 10
    prob_w = 9
    sub_w = 8
    pen_w = 8
    time_w = 13

    # 构建表头
    headers = [
        pad_str("排名", rank_w, "right"),
        pad_str("用户名", user_w),
        pad_str("昵称", nick_w),
        pad_str("总分", total_w, "right"),
    ]
    for p_order in sorted_problems:
        headers.append(pad_str(f"P{p_order}", prob_w, "right"))
    headers.extend([
        pad_str("提交数", sub_w, "right"),
        pad_str("罚时(m)", pen_w, "right"),
        pad_str("最后提交", time_w, "center"),
    ])

    header_line = " ".join(headers)
    line_sep = "-" * len(header_line)

    title = f" 比赛 {contest_id} 排行榜 (共 {total} 人" + (f"，显示前 {len(records)} 名" if top else "") + ") "
    border_len = max(len(header_line), 60)
    title_bar = f"{'=' * ((border_len - get_display_width(title)) // 2)}{title}"
    title_bar += "=" * (border_len - get_display_width(title_bar))

    print(f"\n{title_bar}")
    print(header_line)
    print(line_sep)

    for item in records:
        rank = item.get("rank", "-")
        user_meta = item.get("userMeta") or {}
        username = user_meta.get("username", "") or f"User_{item.get('userId')}"
        nickname = user_meta.get("nickname", "") or ""
        total_score = item.get("totalScore", 0.0)
        penalty = item.get("penalty", 0) // 60  # 秒转分钟
        last_time = format_time(item.get("lastSubmitTime"))

        # 每题分数与提交统计
        prob_scores = {p.get("order"): p for p in item.get("problemScores", [])}
        total_subs = sum(p.get("submissionCount", 0) for p in item.get("problemScores", []))

        cols = [
            pad_str(str(rank), rank_w, "right"),
            pad_str(username[:14], user_w),
            pad_str(nickname[:12], nick_w),
            pad_str(f"{total_score:.2f}", total_w, "right"),
        ]

        for p_order in sorted_problems:
            p_info = prob_scores.get(p_order)
            if p_info is not None:
                score_str = f"{p_info.get('score', 0):.2f}"
            else:
                score_str = "-"
            cols.append(pad_str(score_str, prob_w, "right"))

        cols.extend([
            pad_str(str(total_subs), sub_w, "right"),
            pad_str(str(penalty), pen_w, "right"),
            pad_str(last_time, time_w, "center"),
        ])

        row_str = " ".join(cols)
        # 高亮当前用户
        if current_user and (current_user.lower() in username.lower() or current_user.lower() in nickname.lower()):
            print(f"\033[1;32m{row_str}  <-- YOU\033[0m")
        else:
            print(row_str)

    print(f"{'=' * border_len}\n")


def export_csv(scoreboard_data: dict, filepath: str):
    """导出排行榜到 CSV 文件"""
    records = scoreboard_data.get("scoreboard", [])
    if not records:
        print("[!] 无数据可导出", file=sys.stderr)
        return

    problem_orders = set()
    for item in records:
        for p in item.get("problemScores", []):
            if "order" in p:
                problem_orders.add(p["order"])
    sorted_problems = sorted(problem_orders) if problem_orders else [1]

    fieldnames = ["rank", "userId", "username", "nickname", "email", "totalScore"]
    for p in sorted_problems:
        fieldnames.append(f"P{p}_score")
        fieldnames.append(f"P{p}_subs")
    fieldnames.extend(["totalSubmissions", "penaltyMinutes", "lastSubmitTime"])

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in records:
            meta = item.get("userMeta") or {}
            prob_map = {p.get("order"): p for p in item.get("problemScores", [])}
            row = {
                "rank": item.get("rank"),
                "userId": item.get("userId"),
                "username": meta.get("username"),
                "nickname": meta.get("nickname"),
                "email": meta.get("email"),
                "totalScore": item.get("totalScore"),
                "totalSubmissions": sum(p.get("submissionCount", 0) for p in item.get("problemScores", [])),
                "penaltyMinutes": item.get("penalty", 0) // 60,
                "lastSubmitTime": item.get("lastSubmitTime"),
            }
            for p in sorted_problems:
                p_info = prob_map.get(p, {})
                row[f"P{p}_score"] = p_info.get("score")
                row[f"P{p}_subs"] = p_info.get("submissionCount")
            writer.writerow(row)

    print(f"[✓] 已成功将排行榜导出到: {filepath}")


def main():
    config = load_config()
    default_contest = config.get("contest_id", 13)

    parser = argparse.ArgumentParser(description="XPUOJ 排行榜查询工具")
    parser.add_argument("-c", "--contest", type=int, default=default_contest, help=f"比赛 ID (默认: {default_contest})")
    parser.add_argument("-n", "--top", type=int, default=None, help="只显示排名前 N 位")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出原始数据")
    parser.add_argument("--csv", type=str, default=None, help="导出为 CSV 文件 (指定文件路径)")
    args = parser.parse_args()

    client = XPUOJClient()
    email = config.get("email")
    password = config.get("password")

    # 尝试登录/读取缓存 token
    if not client.ensure_login(email, password):
        print("[!] 提示: 未提供有效登录凭据，尝试匿名请求...", file=sys.stderr)

    # 获取榜单数据
    data = fetch_all_scoreboard(client, args.contest)

    if args.json:
        if args.top and args.top > 0:
            data["scoreboard"] = data.get("scoreboard", [])[:args.top]
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    if args.csv:
        export_csv(data, args.csv)
        return

    # 获取当前用户名用于高亮
    current_username = client._email.split("@")[0] if client._email else None
    print_scoreboard_table(data, contest_id=args.contest, top=args.top, current_user=current_username)


if __name__ == "__main__":
    main()

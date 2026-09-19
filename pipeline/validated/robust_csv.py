#!/usr/bin/env python3
# =============================================================================
# 稳健读取 /mnt/f 上的 MOOSE 输出 CSV —— 因为 9p 会**静默返回过期数据**
# =============================================================================
#
# 【2026-09-19 实测的坑】
#   对**同一个正在被追加**的 CSV 连续读三次，得到三个不同的结果：
#       第 1 次: 1757 行, 末 t=0.0351
#       第 2 次: 2680 行, 末 t=0.0535
#       第 3 次: 6185 行, 末 t=0.1236   ← 与 shell 的 tail/wc 一致
#   原因是 `/mnt/f` 是 Windows 盘经 **9p 协议**挂载的，读会命中过期的缓存页。
#   **不会报错**，只是悄悄给你一个旧版本。
#
#   本项目此前**三次**出现"时间倒退"的怪象，全部是读 `/mnt/f` 造成的；
#   我一度据此误判过"结果发散了""平衡依赖于 M"。
#
# 【稳健读法】
#   1. 先 `wc -l` 拿 shell 认可的字节/行数（shell 走的是另一条路径，实测一致）
#   2. 反复读，直到 Python 读到的行数与之一致（或达到重试上限）
#   3. 返回**行数最多**的那一次（追加型文件里，最新的就是行数最多的）
#
# 用法：
#   from robust_csv import read_rows
#   rows = read_rows("/mnt/f/.../out.csv")
# =============================================================================

import csv
import subprocess
import time


def _shell_lines(path):
    try:
        out = subprocess.run(["wc", "-l", path], capture_output=True,
                             text=True, timeout=10).stdout
        return int(out.split()[0])
    except Exception:
        return None


def read_rows(path, retries=12, delay=0.3):
    """
    返回 list[dict]。**连续两次读到一样的行数才停**，返回行数最多的那一次。

    ⚠ 不要用 `list(csv.DictReader(open(path)))` —— 它可能给你一个旧快照。

    ⚠⚠ 也**不要**靠 `wc -l` 判断何时停。第一版就是那么写的，结果：
        `wc -l` **本身也会过期**（9p 缓存），于是循环提前退出、
        返回一个旧快照 —— 实测在 T14 上就把 t=0.0185 读成了 t=0.0053。
        改成"连续两次一致"才可靠。
    """
    best = []
    prev_len = -1
    same = 0
    for _ in range(retries):
        try:
            rows = list(csv.DictReader(open(path, encoding="utf-8",
                                             errors="replace")))
        except Exception:
            rows = []
        if len(rows) > len(best):
            best = rows
        # 连续两次读到同样的行数 => 稳定
        if len(rows) == prev_len and len(rows) > 0:
            same += 1
            if same >= 2:
                break
        else:
            same = 0
        prev_len = len(rows)
        time.sleep(delay)
    return best


def read_rows_strict(path):
    """
    给**已经跑完、不会再变**的文件用：读两次，两次一致才返回。
    不一致就说明有缓存问题，抛错而不是悄悄给出可能过期的数据。
    """
    a = read_rows(path)
    b = read_rows(path)
    if len(a) != len(b) or (a and b and a[-1] != b[-1]):
        raise RuntimeError(
            f"{path}: 两次读取不一致（{len(a)} vs {len(b)} 行）—— "
            f"9p 缓存问题，数据可能过期。请稍后重试或先 cp 到 WSL 本地盘。")
    return a


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        r = read_rows(p)
        want = _shell_lines(p)
        ok = "OK " if (want is None or len(r) >= want - 1) else "不一致!"
        print("%-6s %-6d 行 (shell %s)  末行: %s"
              % (ok, len(r), want, dict(r[-1]) if r else "-"))

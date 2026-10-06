#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_sentinel.py <tag> <step> —— 哨兵：等某臂出现 `snap_<step>.npz` 就**自动跑判定器**。

## 为什么用哨兵而不是反复轮询
用户 2026-10-07 要求「每个实验 4 核、留核给论文写作」
⇒ 我的轮询本身不该抢资源；哨兵**每 2 分钟才醒一次**，并且**不做重活**。

## 判活纪律（`R625 §13.3`）
哨兵只负责"**文件出现**"这一个客观事件；它**不判断**算例是否卡死
（那要看 CPU 增量，由 `_t11_cpu_audit.py` 负责）。
"""
import os
import subprocess
import sys
import time

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework"
PY = "/root/miniconda3/envs/ml/bin/python"
LOG = "/mnt/f/speed_up/_w2_sentinel.log"
tag = sys.argv[1] if len(sys.argv) > 1 else "c2B647"
target = sys.argv[2] if len(sys.argv) > 2 else "100"

snap = os.path.join(ROOT, "_exp/_bk_t5/dry_%s/snap_%05d.npz" % (tag, int(target)))


def log(m):
    with open(LOG, "a") as fh:
        fh.write("[%s] %s\n" % (time.strftime('%H:%M:%S'), m))


log("哨兵启动：等 %s（每 120 s 查一次）" % snap)
for i in range(90):                       # 最多等 3 小时
    if os.path.exists(snap):
        log("✅ 出现 %s（%.1f MB）⇒ 跑判定器"
            % (os.path.basename(snap), os.path.getsize(snap) / 1e6))
        time.sleep(30)                    # 等文件写完
        with open("/mnt/f/speed_up/_w2_verdict.txt", "w") as fh:
            subprocess.call([PY, "_t11_cube_verdict.py"], cwd=ROOT,
                            stdout=fh, stderr=subprocess.STDOUT)
        with open("/mnt/f/speed_up/_w2_shape.txt", "w") as fh:
            subprocess.call([PY, "_t11_shape2.py", tag], cwd=ROOT,
                            stdout=fh, stderr=subprocess.STDOUT)
        log("✅ 判定器已出结果（_w2_verdict.txt / _w2_shape.txt）")
        break
    if i % 5 == 0:
        log("等 %s 中…（第 %d 次）" % (os.path.basename(snap), i + 1))
    time.sleep(120)
else:
    log("⚠ 超时（3 小时）仍未出现 %s" % snap)

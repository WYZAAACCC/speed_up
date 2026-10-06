#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_quarantine_stale.py —— 把**跨运行的残留快照**移出活动目录（**改名保留，绝不删除**）。

判据（与 `_t11_artifact_audit.py` 同）：快照 mtime **早于** 同目录 `meta.json` 的 mtime
⇒ 它不可能属于本次运行 ⇒ 是上一次运行留下的残留。

动作：移到 `<dir>/_stale_from_earlier_run/`（**同盘同目录改名，不删**），
      并写出 `QUARANTINE_README.txt` 说明原因与来源。
"""
import glob
import json
import os
import shutil
import time

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
OUT = "/mnt/f/speed_up/_w2_quarantine.txt"
L = ["#### %s" % time.strftime('%F %T'), ""]
for t in ("c2Eq0", "c2B647", "c2PosA", "c2B15", "c2Arch3"):
    d = os.path.join(ROOT, "dry_%s" % t)
    mj = os.path.join(d, "meta.json")
    if not os.path.exists(mj):
        continue
    mt_meta = os.path.getmtime(mj)
    a = json.load(open(mj, encoding="utf-8")).get("exp_args", {})
    stale = [f for f in sorted(glob.glob(os.path.join(d, "snap_*.npz")))
             if os.path.getmtime(f) < mt_meta - 1.0]
    L.append("【%s】meta: steps=%s snap_every=%s（mtime=%s）"
             % (t, a.get('steps'), a.get('snap_every'),
                time.strftime('%H:%M:%S', time.localtime(mt_meta))))
    if not stale:
        L.append("   ✅ 无残留")
        continue
    qdir = os.path.join(d, "_stale_from_earlier_run")
    os.makedirs(qdir, exist_ok=True)
    for f in stale:
        dst = os.path.join(qdir, os.path.basename(f))
        shutil.move(f, dst)
        L.append("   → 移出 %s（mtime=%s）⇒ %s"
                 % (os.path.basename(f),
                    time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(dst))),
                    os.path.relpath(qdir, d)))
    with open(os.path.join(qdir, "QUARANTINE_README.txt"), "w") as fh:
        fh.write(
            "本目录里的文件**不属于**当前这次运行，是**更早一次运行**留下的残留。\n\n"
            "判据：文件 mtime **早于** 同级 `meta.json` 的 mtime。\n"
            "来源：本次实验先后启动过 v2.1（snap_every=40）与 v2.2（snap_every=100）\n"
            "      两次运行共用同一个 `--out` 目录，而 v2.1 被中途杀掉 ⇒ 残留。\n"
            "危害：若量具按文件名顺序读，会把**两次运行**的快照混成一个序列\n"
            "      ⇒ 判定被污染（实测：`c2Eq0` 的判定曾用到这里的 `snap_00040`）。\n"
            "处理：**改名保留，未删除**；需要时可搬回。\n"
            "时间：%s\n" % time.strftime('%F %T'))
open(OUT, 'w').write("\n".join(L) + "\n")
print("\n".join(L))

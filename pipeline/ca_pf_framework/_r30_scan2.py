#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30：扫全仓 (a) 有没有跑过 `--arm auto`；(b) series.csv 里 psi_mean 有没有非 nan。"""
import os
import csv
import glob
import json

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

print('--- 目录名带 auto / wet 的算例 ---')
hits = [d for d in glob.glob('_exp/*') if os.path.isdir(d)
        and ('auto' in os.path.basename(d) or 'wet' in os.path.basename(d))]
print(hits or '（无）')

print('--- 所有 meta.json 的 arm 取值统计 ---')
cnt = {}
for p in glob.glob('_exp/*/meta.json') + glob.glob('_exp/*/*/meta.json'):
    try:
        m = json.load(open(p))
    except Exception:
        continue
    a = m.get('arm', '?')
    cnt[a] = cnt.get(a, 0) + 1
print(cnt)

print('--- 所有 launch_*.json 里出现过的 --arm 值 ---')
arms = {}
for p in glob.glob('_exp/*/launch_*.json'):
    try:
        j = json.load(open(p))
    except Exception:
        continue
    cmd = j.get('cmd', [])
    if '--arm' in cmd:
        a = cmd[cmd.index('--arm') + 1]
        arms[a] = arms.get(a, 0) + 1
print(arms)

print('--- series.csv 里 psi_mean 非空的算例 ---')
bad = []
for p in glob.glob('_exp/*/series.csv') + glob.glob('_exp/*/*/series.csv'):
    try:
        rs = list(csv.DictReader(open(p)))
    except Exception:
        continue
    v = [r['psi_mean'] for r in rs if r.get('psi_mean') not in ('', 'nan', None)]
    if v:
        bad.append((p, len(v), v[:3]))
print(bad or '（NONE：所有 series.csv 的 psi_mean 都是 nan）')

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_closedcheck.py —— 核验：`_bk_exp.py --closed` 与 `_bk_closed.py` 生成的长命令行
**推出的是同一套参数**（R29 的"一条命令"承诺必须可核）。

做法：两边都只做**推导**（`--dry-run` 或纯打印），把结果里的关键参数比对。
不跑仿真 ⇒ 几秒钟。

用法：python3 _bk_closedcheck.py [--alpha-km A] [--gamma G] [--tag T]
"""
import argparse
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
PY = sys.executable
import windowB_closure as CL                                    # noqa: E402

KEYS = ('--N', '--dx-nm', '--steps', '--plate-L', '--plate-W', '--plate-T',
        '--plate-t-physical', '--eng-r-nm', '--eng-t-nm', '--eng-elong',
        '--nuc-overlap-nm', '--eng-t-last-reduce-nm', '--beta-h', '--laths',
        '--nuc-law', '--alpha-km', '--cool-ratio', '--T-end',
        '--grow-stack', '--nuc-every')


def parse_cmd(text):
    """从 `_bk_closed.py` 打印的**命令行**里抽出 `--key value` 对。"""
    out = {}
    toks = text.split()
    for i, t in enumerate(toks):
        if t in KEYS and i + 1 < len(toks):
            out[t] = toks[i + 1]
    # 标志型（无值）
    for t in ('--grow-stack',):
        if t in toks:
            out[t] = 'True'
    if '--nuc-every' in toks:
        i = toks.index('--nuc-every')
        if i + 1 < len(toks):
            out['--nuc-every'] = toks[i + 1]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--alpha-km', type=float, default=CL.ALPHA_KM_REF)
    ap.add_argument('--gamma', type=float, default=CL.GAMMA_F1_MAIN)
    a = ap.parse_args()

    # ① `_bk_closed.py` 打印出来的命令行
    r1 = subprocess.run([PY, '-u', '_bk_closed.py', '--alpha-km', str(a.alpha_km),
                         '--gamma', str(a.gamma), '--tag', 'CHK'],
                        cwd=_HERE, capture_output=True, text=True)
    c1 = parse_cmd(r1.stdout)

    # ② `_bk_exp.py --closed` 自己的推导：读它打印的**机器可读**那一行
    #    `CLOSED_ARGS {json}`（不去正则抠人读的表 —— 那个格式会变）。
    r2 = subprocess.run([PY, '-u', '_bk_exp.py', '--closed', '--dry-run',
                         '--alpha-km', str(a.alpha_km),
                         '--gamma0', str(a.gamma), '--tag', 'CHK2',
                         '--out', '_exp/_bk_closed'],
                        cwd=_HERE, capture_output=True, text=True)
    c2 = {}
    for line in r2.stdout.splitlines():
        if line.startswith('CLOSED_ARGS '):
            d = json.loads(line[len('CLOSED_ARGS '):])
            c2 = {'--' + k.replace('_', '-'): str(v) for k, v in d.items()}
            break
    if not c2:
        print('✗ `--closed` 没有打印 CLOSED_ARGS（退出码 %d）' % r2.returncode)
        print(r2.stdout[-2000:])
        return 1

    print('=' * 96)
    print('`--closed`（一条命令） vs `_bk_closed.py`（长命令行）')
    print('=' * 96)
    bad = 0
    for k in KEYS:
        v1, v2 = c1.get(k), c2.get(k)
        if v1 is None and v2 is None:
            continue
        if k == '--gamma0':
            # `--closed` **不自动改** gamma0（它是文献选择）⇒ 两边都应等于用户传的值
            pass
        same = (v1 == v2)
        if not same:
            # 允许数值等价（4590 vs 4590.00）
            try:
                same = abs(float(v1) - float(v2)) < 1e-6
            except (TypeError, ValueError):
                same = False
        if not same:
            bad += 1
        print('  %-24s closed.py=%-14s --closed=%-14s %s'
              % (k, v1, v2, 'OK' if same else '**不一致**'))
    print('-' * 96)
    print('  不一致项 = %d' % bad)

    # ---- ②b 参数一致之外，还要核**这套参数本身合法** ---------------------
    #   两处"一致"可能是"一致地都错" ⇒ 必须独立核闭式的判据。
    rec = CL.recommend(alpha_KM=a.alpha_km)
    ok_o, ratio_o, qm = CL.ordered_ok(rec['q'], 1e-9, a.alpha_km, rec['L_lath'],
                                      dG_worst=rec['dG_at_start'])
    checks = [
        ('C-3 有序性 Δt_grow/Δt_nuc ≤ 1', ok_o, '%.3f（q_cap=%.3e）' % (ratio_o, qm)),
        ('C-4 t/Δx ≥ 4（本仓库分辨率目标）', rec['t_over_dx'] >= 4.0,
         '%.2f' % rec['t_over_dx']),
        ('C-4 几何装得下 n 根', rec['n_geo_cap'] >= rec['n_lath'],
         'n_cap=%d ≥ n=%d' % (rec['n_geo_cap'], rec['n_lath'])),
        ('C-2 n == floor(α(M_s−T_end))', rec['n_lath'] ==
         CL.n_lath_int(298.0, a.alpha_km), 'n=%d' % rec['n_lath']),
        ('C-8 供给限速（不是几何限速）',
         CL.who_limits(rec['n_geo_cap'], a.alpha_km)['binding'] == 'kinetics',
         str(CL.who_limits(rec['n_geo_cap'], a.alpha_km))),
        ('C-3 步数 ≥ 下界 / 安全系数', rec['steps'] >= rec['steps_min'] / 0.8,
         '%d ≥ %.0f' % (rec['steps'], rec['steps_min'] / 0.8)),
    ]
    bad2 = 0
    for nm, ok_, det in checks:
        if not ok_:
            bad2 += 1
        print('  %-34s %s  %s' % (nm, 'OK' if ok_ else '**不合法**', det))
    print('  参数合法性：不合法项 = %d' % bad2)
    if r2.returncode != 0:
        print('  ⚠ `--closed --dry-run` 退出码 = %d（尾部输出：%s）'
              % (r2.returncode, r2.stderr.strip().splitlines()[-1:] or ''))
    return 1 if (bad or bad2) else 0


if __name__ == '__main__':
    raise SystemExit(main())

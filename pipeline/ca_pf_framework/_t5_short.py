#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_short.py --- ★★★★★ 实验(5)重启的**短跑定参数**（用户要求："先短跑定参数，再长跑"）

## 这一跑要回答的四件事（**全部是当前的外推项，必须实测**）
| # | 问题 | 之前的状态 |
|---|---|---|
| 1 | **N=160 的真实峰值内存** `VmHWM` | 只有"N=160 归档臂 3–4 GB"的转述 ⇒ **未实测** |
| 2 | **N=160 的真实单步耗时** | 由 abA 的 4.68 s/步(N=112) 按 N³ 外推 ⇒ **13.6 s/步【推理】** |
| 3 | **N=160 的真实检查点体积** | 由 N=64 的 20.93 MB 按 N³ 外推 ⇒ **~300–380 MB/帧【推理】** |
| 4 | **24 次形核够不够在 10 µm 盒里长出多块** | **完全未知** ← 判据③④⑤ 的前提 |

## 配置的取舍（**显式记账**）
* **物理基线 = abA**（用户逐字要求"参照 abA"）：
  `--alpha-km 0.041739`、`--T-end 298.0`、`--cool-rate 2.3524e6`、`--nuc-law athermal`
  ⇒ **形核数 `n = floor(0.041739 × (873.0 − 298.0)) = 24`**
* **⚠ 我**没有**动 `α_KM`** —— 它在日志里标着 `(user)`，是**用户给的物理输入**；
  为"提高形核数"而调它必须用户确认。**⇒ 本跑用原值，先把"够不够"量出来。**
* **`nv = 48`**（`--m 4`，12 变体 × 4）⇒ 24 个形核用掉一半场位，留有余量
* **算子**：直接复用 `_r581_p2.py` 的 `SWITCHES`（13 项逐位优化算子，**不重抄、避免漂移**）
* **断点续跑**：`--ckpt-every 20 --ckpt-keep 2`（用户要求"已能断点续跑"的代码上跑）
* **盒**：`N=160`、`dx=62.5 nm` ⇒ **10.00 µm**（用户要求 ≥10 µm）
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PY = '/root/miniconda3/envs/ml/bin/python'


def laths(m, nvar=12):
    return ','.join(str(v) for v in range(1, nvar + 1) for _ in range(m))


def build(a, switches):
    return ([PY, '-u', os.path.join(HERE, '_bk_exp.py'),
             '--N', str(a.N), '--dx-nm', '62.5',
             '--steps', str(a.steps), '--every', str(a.every),
             '--snap-every', str(a.snap_every), '--pair-every', str(a.pair_every),
             '--norm-smooth', '0', '--phi-band-every', '200',
             '--eng-cadence', '30', '--nthreads', str(a.nthreads),
             '--plate-L', '1000', '--plate-W', '500', '--plate-T', '510',
             '--gamma0', '0.25', '--beta-h', '6.477', '--grow-stack',
             '--nuc-law', 'athermal', '--nuc-init', '6',
             '--nuc-block-target', str(a.B), '--nuc-shape', 'ellipsoid',
             '--nuc-supercrit', '1', '--nuc-sites-refill', '1',
             '--qs-clock', '1', '--qs-max-relax', '100',
             # ★★★★★ 物理基线 = abA（用户逐字要求"参照 abA"）
             '--alpha-km', repr(float(a.alpha_km)), '--T-end', repr(float(a.T_end)),
             '--cool-rate', '2.3524e6',
             '--facet-proj', '0', '--facet-excl', '0',
             '--reinit-dt', '1e-4', '--reinit-band', '6.0',
             '--nuc-overlap-nm', repr(float(a.overlap_nm))] +
            (['--nuc-periodic-seed', '1'] if int(a.periodic_seed) == 1 else []) +
            ['--laths', laths(a.m, a.nvar),
             '--ckpt-every', str(a.ckpt_every), '--ckpt-keep', str(a.ckpt_keep)]
            + (['--resume', a.resume] if a.resume else [])
            + ['--out', a.out, '--tag', a.tag]
            + switches)


def watch(pid, box, stop, limit_kb):
    while not stop.is_set():
        try:
            with open('/proc/%d/status' % pid) as fh:
                for ln in fh:
                    if ln.startswith('VmHWM:'):
                        kb = int(ln.split()[1])
                        box['kb'] = max(box.get('kb', 0), kb)
                        if kb > limit_kb and not box.get('killed'):
                            box['killed'] = True
                            print('  ⚠⚠⚠ 内存看门狗触发：VmHWM=%.2f GB > %.2f GB ⇒ 杀'
                                  % (kb / 1048576.0, limit_kb / 1048576.0), flush=True)
                            try:
                                os.kill(pid, 9)
                            except OSError:
                                pass
                        break
        except OSError:
            pass
        stop.wait(0.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='t5s1')
    ap.add_argument('--N', type=int, default=160)
    ap.add_argument('--m', type=int, default=4)
    # ★★★★★ R581-T5R-s18（**形核停滞的修复**）：`--nvar` —— **活跃变体数**。
    #   ## 病灶（第 17 轮诊断跑实测，`nuc_dbg.json`）
    #     `nfsv_nofield = 6`、`n_target_final = 10`、`ok = 3`
    #     ⇒ **6 个形核事件因"同变体组里没有空闲场"被拒**。
    #   ## 机制（`windowB_surface.py:2324-2345` + 代码自己的结论 `:2385-2394`）
    #     `nfsv` 在**同一变体组**里找未被占用的场；找不到就拒绝。
    #     代码逐字：「**「空场用完」= 模型能表示的板条数到顶**
    #     （**`nv` 是个表示上限，不是物理上限**）…… 必须**拒绝 + 计数**」。
    #   ## 为什么 `--nvar` 是正确旋钮
    #     `laths(m, nvar)` = `nvar` 个变体 × 每个 `m` 个场 ⇒ **`nv = nvar·m`**。
    #     我的跑**塌缩到单变体**（`f_var = 1/0/0/…`）⇒ 该变体只有 `m` 个场
    #     ⇒ **用完即封顶**。把 `nvar` 调小、`m` 调大，**乘积（= nv = 内存）不变**，
    #     而**单变体可容纳的板条数 = m** 变大。
    #   ⚠ **取舍记账**：变体数变少**会削弱判据⑥（涌现自协调需要多变体）**
    #     ⇒ 这是显式的取舍；当前必须先解除形核封顶（否则判据③④⑤ 完全拿不到）。
    #   ⚠ **不采用** `nfsv_strict=False`（回退到已有场）—— 代码明确警告它
    #     「会把"表示不了"伪装成"又长了一片"」。
    ap.add_argument('--nvar', type=int, default=12,
                    help='活跃变体数（nv = nvar × m）。默认 12 与归档一致。')
    ap.add_argument('--B', type=int, default=5)
    ap.add_argument('--steps', type=int, default=40)
    ap.add_argument('--every', type=int, default=5)
    ap.add_argument('--snap-every', type=int, default=200)
    ap.add_argument('--pair-every', type=int, default=20)
    ap.add_argument('--nthreads', type=int, default=4)
    ap.add_argument('--alpha-km', type=float, default=0.041739)   # ★ abA 的原值
    ap.add_argument('--T-end', type=float, default=298.0)         # ★ abA 的原值
    ap.add_argument('--ckpt-every', type=int, default=20)
    ap.add_argument('--ckpt-keep', type=int, default=2)
    # ★★★★★ S4（`--nuc-overlap-nm`）单变量 A/B 用：
    #   审计 §2 已证明它**直接**接在引擎的 `attach_overlap` 上，
    #   而本长跑走的正是 **attach 通道** ⇒ **默认 0 会破坏块内界面完整性**。
    #   `62.5` = 1Δx = 代码自带剂量–响应实测的最优；`0` = 旧默认（= 被审计的简化）。
    ap.add_argument('--overlap-nm', type=float, default=62.5)
    ap.add_argument('--periodic-seed', type=int, default=1, choices=(0, 1))
    ap.add_argument('--resume', default='')
    ap.add_argument('--out', default='_exp/_bk_t5')
    ap.add_argument('--mem-limit-gb', type=float, default=14.0)
    ap.add_argument('--cores', default='0-7')
    ap.add_argument('--archive-old', action='store_true')
    a = ap.parse_args()

    import importlib.util
    spec = importlib.util.spec_from_file_location('p2', os.path.join(HERE, '_r581_p2.py'))
    p2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(p2)
    switches = list(p2.SWITCHES)          # ★ 13 项逐位优化算子，单一真源

    if a.archive_old:
        d = os.path.join(a.out, 'dry_' + a.tag)
        if os.path.isdir(d):
            n = '%s_superseded_%d' % (d, int(time.time()))
            shutil.move(d, n)
            print('  已归档改名：%s → %s' % (d, os.path.basename(n)))

    c = build(a, switches)
    lg = '_w2_t5_short_%s.log' % a.tag
    nv = int(a.nvar) * a.m
    Ms = 873.0
    n_nuc = int((float(a.alpha_km) * (Ms - float(a.T_end))) // 1)
    print('=' * 100)
    print('T5 短跑  tag=%s  N=%d ⇒ 盒 %.2f µm' % (a.tag, a.N, a.N * 62.5 / 1000))
    print('  nv=%d  B=%d  steps=%d  threads=%d  内存上限 %.1f GB  绑核 %s'
          % (nv, a.B, a.steps, a.nthreads, a.mem_limit_gb, a.cores))
    print('  ★ 物理基线 = abA：α_KM=%.6f  T_end=%.1f  ⇒ **导出形核数 n = %d**'
          % (a.alpha_km, a.T_end, n_nuc))
    print('  ★ 优化算子 = %d 项（复用 `_r581_p2.SWITCHES`）：%s'
          % (len(switches) // 2, ' '.join(switches[:8]) + ' …'))
    print('  ★ 断点续跑：--ckpt-every %d --ckpt-keep %d%s'
          % (a.ckpt_every, a.ckpt_keep,
             '  **续跑自 %s**' % a.resume if a.resume else ''))
    print('  ★ S4：--nuc-overlap-nm = **%s**（62.5 = 1Δx 修复值；0 = 旧默认）'
          % a.overlap_nm)
    print('  ★ N13：--nuc-periodic-seed = %d' % int(a.periodic_seed))
    print('=' * 100)
    sys.stdout.flush()

    env = dict(os.environ)
    for k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        env.pop(k, None)
    env.pop('MALLOC_MMAP_THRESHOLD_', None)
    env.pop('MALLOC_TRIM_THRESHOLD_', None)
    t0 = time.time()
    with open(lg, 'wb') as fh:
        pr = subprocess.Popen(['taskset', '-c', a.cores] + c, stdout=fh,
                              stderr=subprocess.STDOUT, env=env)
        box, stop = {}, threading.Event()
        th = threading.Thread(target=watch, args=(pr.pid, box, stop,
                                                  a.mem_limit_gb * 1048576.0))
        th.daemon = True
        th.start()
        pr.wait()
        stop.set()
        th.join(timeout=2)
    el = time.time() - t0
    txt = open(lg, encoding='utf-8', errors='replace').read()
    steps = [int(m.group(1)) for m in re.finditer(r'\[\s*(\d+)\]\s+Vt=', txt)]
    sps = [float(m.group(1)) for m in re.finditer(r'\|\s*([\d.]+)s/步', txt)]
    print()
    print('  exit=%d  墙钟 %.1f s' % (pr.returncode, el))
    print('  峰值 RSS（VmHWM，看门狗实测）= **%.2f GB**%s'
          % (box.get('kb', 0) / 1048576.0, '  ⚠ 被看门狗杀' if box.get('killed') else ''))
    print('  走到 step %s（共 %d 步）' % (steps[-1] if steps else '?', a.steps))
    if sps:
        print('  单步耗时：中位 **%.2f s/步**  最小 %.2f  最大 %.2f（%d 个采样）'
              % (sorted(sps)[len(sps) // 2], min(sps), max(sps), len(sps)))
    ck = os.path.join(a.out, 'dry_' + a.tag, 'ckpt')
    if os.path.isdir(ck):
        fs = sorted(os.listdir(ck))
        print('  ★ 检查点：%d 个文件 —— %s' % (len(fs), ', '.join(fs[:6])))
        for f in fs:
            print('      %-24s %8.1f MB' % (f, os.path.getsize(os.path.join(ck, f)) / 1048576.0))
    print('  日志 %s' % lg)
    print('=' * 100)


if __name__ == '__main__':
    main()

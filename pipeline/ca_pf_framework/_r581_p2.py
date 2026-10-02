#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_p2.py --- Part 2（任务(5) 重启）的**统一运行器**：带内存看门狗 + 结构化读数。

## 为什么需要它
1. `R581` 实测：N=160 的**峰值 RSS 远高于** `R550/R580` 的内存定律（差 2.6–4 倍）。
   而 AGENTS §3.12 记着：WSL 只有 24 GB，**占满会整机卡死**（不是"慢"，是"卡死"）。
   ⇒ 必须有一个**独立看门狗**在 RSS 超阈值时**先杀进程**，绝不能让它把 WSL 拖死。
2. 真实路径的步进读数要从 stdout 里抓（`[step] Vt=... | X s/步`）。
3. 需要把 N8 横幅、df(T) 轨迹、以及末态判据行**落到一处**，便于机器判读。

用法:
  python3 _r581_p2.py --run --tag p2_b5 --N 160 --m 4 --steps 4000 \
                      --nuc-block-target 5
  python3 _r581_p2.py --read <tag>          # 只读已有结果
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
PY = '/root/miniconda3/envs/ml/bin/python'
RE_STEP = re.compile(r'\[\s*(\d+)\]\s+Vt=([\d.eE+\-]+).*?\|\s*([\d.]+)s/步')
RE_DF = re.compile(r'df\s*=\s*([\d.eE+\-]+)')

# ★ 全**逐位相同**的开关（每一档都有独立判据，见 `R580_VERIFY.md` / `_r581_L1prof.sh`）。
#   ⚠ **不用** `--phi-prec f32`（近似，非逐位）；**不用** `--fft-mode rfft`（非逐位）。
SWITCHES = ['--eps0-mode', 'einsum', '--ed-pair', 'gather',
            '--k-loop', 'act', '--act-mode', 'bincount',
            '--argmin2-mode', 'copyto', '--grad-mode', 'sliced',
            '--pf-phi', 'onfly', '--h-chunk', '4',
            '--extend-mode', 'near',
            # ★ R581-L2：ε⁰ 流式装配的首轴分块（生产口径实测整步 1.178×，逐位）。
            '--eps0-tile', '4',
            # ★ R581-L5：复用 region() 的 winner（省一次 argmin/步；逐位，整步 1.058×）。
            '--argmin2-reuse', '1',
            # ★ R581-L6：upwind_flux_vec 的整轴融合 C 核（逐位；整步 1.190×）。
            #   ⚠ 需要 `_r581_ufv.so`：先 `bash _r581_buildc.sh`。
            '--ufv-c', '1',
            # ★ R581-L4：`_bbox_pad` 逐轴 any 版（逐位；`_bbox_pad` 本身 15.362×，
            #   折算约 0.4% 单步 —— 天花板低，如实登记）。
            '--bbox-mode', 'axis']


def laths(m, nvar=12):
    return ','.join(str(v) for v in range(1, nvar + 1) for _ in range(m))


def cmd_of(a):
    return ([PY, '-u', os.path.join(HERE, '_bk_exp.py'),
             '--N', str(a.N), '--dx-nm', '62.5',
             '--steps', str(a.steps), '--every', '5',
             # ⚠ R525 §9.3：**不能**传 `--pair-every 0` —— 那会让 `blk_nprof`/`nblk_sig`
             #   变成空列，C3/C4 就**无从判起**（P4/P6 曾因此假 FAIL）。
             '--snap-every', '200', '--pair-every', '50', '--norm-smooth', '0',
             '--phi-band-every', '200', '--eng-cadence', '30',
             '--nthreads', str(a.nthreads),
             '--plate-L', '1000', '--plate-W', '500', '--plate-T', '510',
             '--gamma0', '0.25', '--beta-h', '6.477', '--grow-stack',
             '--nuc-law', 'athermal', '--nuc-init', '6',
             '--nuc-block-target', str(a.B), '--nuc-shape', 'ellipsoid',
             '--nuc-supercrit', '1', '--nuc-sites-refill', '1',
             # ⚠ **不传** `--nuc-fresh-every`：N8 已修（`_bk_exp.py:686`）⇒ 自动取 K=n(T_end) 并硬校验
             '--qs-clock', '1', '--qs-max-relax', '100',
             '--alpha-km', '0.011', '--T-end', '350.0', '--cool-rate', '2.3524e6',
             '--facet-proj', '0', '--facet-excl', '0',
             '--reinit-dt', '1e-4', '--reinit-band', '6.0',
             '--laths', laths(a.m),
             '--out', a.out, '--tag', a.tag]
            + (['--nuc-overlap-nm', repr(float(a.overlap_nm))]
               if a.overlap_nm is not None else [])
            + (['--nuc-periodic-seed', '1'] if int(a.periodic_seed) == 1 else [])
            + SWITCHES)


def watch(pid, box, stop, limit_kb):
    """独立看门狗：读 /proc/<pid>/status 的 VmHWM；超阈值 ⇒ **立刻杀**。"""
    while not stop.is_set():
        try:
            with open('/proc/%d/status' % pid) as fh:
                for ln in fh:
                    if ln.startswith('VmHWM:'):
                        kb = int(ln.split()[1])
                        box['kb'] = max(box.get('kb', 0), kb)
                        if kb > limit_kb and not box.get('killed'):
                            box['killed'] = True
                            print('  ⚠⚠⚠ **内存看门狗触发**：VmHWM=%.2f GB > 上限 %.2f GB '
                                  '⇒ 杀进程（防 WSL 整机卡死，AGENTS §3.12）'
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
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--read', default='')
    ap.add_argument('--tag', default='p2')
    ap.add_argument('--N', type=int, default=160)
    ap.add_argument('--m', type=int, default=4, help='每个变体给几个场 ⇒ nv = 12*m')
    ap.add_argument('--B', type=int, default=5, help='--nuc-block-target')
    ap.add_argument('--steps', type=int, default=4000)
    ap.add_argument('--nthreads', type=int, default=4)
    ap.add_argument('--out', default='_exp/_bk_p2')
    ap.add_argument('--mem-limit-gb', type=float, default=18.0)
    ap.add_argument('--cores', default='0-7')
    # ★★★★★ R581-R3（goal §(16)② S4）：`--nuc-overlap-nm`。
    #   ## 为什么必须暴露出来（本轮实测的发现）
    #   `_bk_exp.py:1403` 把它**直接**接到引擎的 `attach_overlap`：
    #       attach_overlap=a.nuc_overlap_nm * 1e-9
    #   而本长跑走的正是引擎的 **`attach` 通道**（日志里 `模式 **attach**`）
    #   ⇒ **默认 0 会直接影响块内界面的完整性**。
    #   代码自带的**剂量–响应实测**（`windowB_surface.py:1658-1662`，同 Δx=62.5 nm、
    #   同 n*、N=96、200 步）：
    #       `o = 1Δx = 62.5 nm` ⇒ 界面完整（β 夹层占比 0.13–0.15 = 预摆对照底噪）
    #       `o = 0`             ⇒ 只剩 **0.29–0.62**（阶梯错位伪影）
    #       `o = 1.5Δx`         ⇒ **过大**，会把先形成的板条撕碎
    #   ⚠ 记账：CLI 帮助（`_bk_exp.py:3068`）却写「建议值 ≥ 1.5Δx（⇒ 94 nm）」——
    #     **与上面这条实测自相矛盾**（那条是给**驱动层** `_seed_next` 路的）。
    #     ⇒ 本脚本取**引擎路实测的最优** `1Δx = 62.5 nm`，并把矛盾登记进报告。
    ap.add_argument('--overlap-nm', type=float, default=None,
                    help='若给定，则传 `--nuc-overlap-nm <v>`（S4 的修复值建议 62.5）')
    # ★★★★★ R581-R3（goal §(16)⑥ / N13）：`--nuc-periodic-seed`。
    #   N13 的判定：**播种是"有界盒"的，而动力学是"周期"的** ⇒ 靠近盒面的随机位点
    #   被整片丢掉（实测 `oob = 122` vs `ok = 13`）。修法 = 打开这个开关。
    #   A/B 实测（`R2 §6 N13`）：`oob` **122 → 0**、`nfsv_nofield` 3→0、
    #   `fresh_blocked` 5→0、**`Vt` +57%**、逐块分布 `10/1/1` → `5/3/2/2/1/1/1`
    #   （**多块 × 每块多根第一次真正出现**）。
    #   ⚠ 它是**缺陷修复**，不是逐位开关 ⇒ 必须与别的改动分开记账。
    ap.add_argument('--periodic-seed', type=int, default=0, choices=(0, 1),
                    help='1 = 传 `--nuc-periodic-seed 1`（N13 的修复）')
    ap.add_argument('--archive-old', action='store_true',
                    help='跑前把同名目录 mv 归档改名（**绝不删除**）')
    a = ap.parse_args()

    nv = 12 * a.m
    if a.archive_old:
        d = os.path.join(a.out, 'dry_' + a.tag)
        if os.path.isdir(d):
            n = '%s_superseded_%d' % (d, int(time.time()))
            shutil.move(d, n)
            print('  已归档改名：%s → %s' % (d, os.path.basename(n)))

    c = cmd_of(a)
    lg = '_w2_r581_p2_%s.log' % a.tag
    print('=' * 100)
    print('R581-P2  tag=%s  N=%d  m=%d ⇒ nv=%d  B=%d  steps=%d  threads=%d'
          % (a.tag, a.N, a.m, nv, a.B, a.steps, a.nthreads))
    print('  内存上限（看门狗）= %.1f GB；绑核 %s' % (a.mem_limit_gb, a.cores))
    print('  S4 修复：--nuc-overlap-nm = %s' % (a.overlap_nm if a.overlap_nm is not None
                                               else '（未传 ⇒ 默认 0.0）'))
    print('  N13 修复：--nuc-periodic-seed = %d' % int(a.periodic_seed))
    print('  ★ 开关档：**全部逐位相同**（无 f32、无 rfft）')
    print('=' * 100)
    sys.stdout.flush()

    env = dict(os.environ)
    for k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        env[k] = '1'
    box, stop = {}, threading.Event()
    t0 = time.time()
    with open(lg, 'w') as fh:
        p = subprocess.Popen(['taskset', '-c', a.cores] + c, cwd=HERE,
                             stdout=fh, stderr=subprocess.STDOUT, env=env)
        th = threading.Thread(target=watch, args=(p.pid, box, stop,
                                                  a.mem_limit_gb * 1048576),
                              daemon=True)
        th.start()
        rc = p.wait()
        stop.set(); th.join(timeout=3)
    wall = time.time() - t0

    txt = open(lg, errors='replace').read()
    sp = [(int(m.group(1)), float(m.group(2)), float(m.group(3)))
          for m in RE_STEP.finditer(txt)]
    dfs = [float(x) for x in RE_DF.findall(txt)]
    print('  墙钟 %.1f s = %.2f h    exit=%d    峰值 RSS = %.2f GB%s'
          % (wall, wall / 3600.0, rc, box.get('kb', 0) / 1048576.0,
             '   ★ 被看门狗杀' if box.get('killed') else ''))
    print('  Traceback 行数 = %d' % len(re.findall(r'^Traceback', txt, re.M)))
    print('  步进读数 = %d 个' % len(sp))
    if sp:
        steady = sorted(x[2] for x in sp[-6:])
        print('  末 6 个 s/步 = %s ⇒ 中位 %.3f'
              % (' '.join('%.3f' % x[2] for x in sp[-6:]), steady[len(steady) // 2]))
        print('  末态 step=%d  Vt=%.6g' % (sp[-1][0], sp[-1][1]))
        print('  ⇒ 外推 600 步 ≈ %.2f h（按末 6 个中位）'
              % (600 * steady[len(steady) // 2] / 3600.0))
    print('  N8 横幅：%s' % ('（未出现）' if 'N8' not in txt else
                             [l.strip() for l in txt.splitlines() if 'N8' in l][0][:110]))
    print('  块数口径：%s' % ([l.strip() for l in txt.splitlines()
                              if '块数口径' in l][:1] or ['（未出现）']))
    print('  df 读数个数 = %d  首/末 = %s / %s'
          % (len(dfs), dfs[0] if dfs else '—', dfs[-1] if dfs else '—'))
    # ★ 记账：df 必须**随 T 变**（goal §(16)⑥ 的硬要求）
    if len(dfs) >= 2:
        print('  ⇒ df 变化范围 [%.6g, %.6g]  相对变化 %.3e ⇒ %s'
              % (min(dfs), max(dfs), (max(dfs) - min(dfs)) / max(abs(min(dfs)), 1e-300),
                 '✅ 随 T 变' if max(dfs) != min(dfs) else '❌ **df 恒定**'))
    print('  日志：%s' % lg)
    return 0


if __name__ == '__main__':
    sys.exit(main())

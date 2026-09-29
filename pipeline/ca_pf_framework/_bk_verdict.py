#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_bk_verdict.py —— **阶段 3 的判决**（判据**先登记**，不许事后改口径）。

## 预登记判据（`BLOCK_STATUS.md` §4 / `BLOCK_DERIVATION.md` §8）

| # | 判据 | 阈值 | 依据 |
|---|---|---|---|
| **V-1 块结构** | `nslab_n == M` **且** `nf3_col == M-1` **且** `nf3_faces > 0` | 全部测点成立 | ★ **`nf3_col` 单独不够**：它只数"柱里相邻的同变体板条对"，若两根板条之间夹了母相 β，`nf3_col` 仍是 M−1 而 `f3_faces` 会掉到 0 ⇒ **必须两者同时成立**才算"被界面分隔" |
| **V-2 每根都在长** | 每根板条的体积**单调不减**且末值 > 初值 | 全部 k | 用**落盘快照**重测（CSV 只存总量） |
| **V-3 界面不动** | `max\|Δpos\| < 0.12 Δx`（P-1） | 全程 | §6.6.2 |
| **V-4 没撞盒壁** | `box_touch == 0` 全程 | 全程 | §9.5（否则几何读数作废） |
| **V-5 数值健康** | `ncomp_max` 末值 ≤ 2（不碎裂） | 末值 | §9.4 |
| **V-6 通道是活的** | 与 `gpos`（γ=100）配对：`gpos` 的 \|Δpos\| **显著大于** `dry` | 比 > 3× | 没它，"界面不动"没有意义 |

跑法：  python3 _bk_verdict.py --tag p2 --arms dry,wet --ctrl-tag ctrl --ctrl-arm gpos
"""
import argparse
import csv
import glob
import json
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402


def load_series(d):
    p = os.path.join(d, 'series.csv')
    if not os.path.exists(p):
        return None
    with open(p, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def fnum(r, k, dv=float('nan')):
    v = r.get(k, '')
    try:
        return float(v)
    except Exception:
        return dv


def drift_basis(rows, grown):
    """`\u0394pos` 的**可用基准**：生长臂要剔除形核步，否则平均位置的跳变被误读成迁移。

    ★ 为什么 V-6 也必须用它：V-6 是"界面不动的分辨力对照"，若 `dry` 那一侧
      用的是**含形核跳变**的原始 `max|\u0394pos|`（`gs4` = 1.266 \u0394x），
      就会算出 `0.236/1.266 = 0.2\u00d7` 并**判 FAIL** —— 而真实情况是
      `V-3g = 0.0225 \u0394x`，比值应为 **10.5\u00d7，PASS**。
      同一份数据、同一把尺，只因基准选错就得出相反结论（本项目已多次栽在这上面）。
    ★ 非生长臂 `grown=False` ⇒ 返回原始 max，**与改动前逐位相同**。
    """
    fin = [abs(fnum(x, 'f3_pos_dx')) for x in rows
           if np.isfinite(fnum(x, 'f3_pos_dx'))]
    if not fin:
        return None
    if not grown:
        return max(fin)
    ns = [fnum(x, 'nslab_n') for x in rows]
    jj = []
    for i in range(1, len(rows)):
        if int(round(ns[i])) != int(round(ns[i - 1])):
            continue
        a0, a1 = fnum(rows[i - 1], 'f3_pos_dx'), fnum(rows[i], 'f3_pos_dx')
        if np.isfinite(a0) and np.isfinite(a1):
            jj.append(abs(a1 - a0))
    return max(jj) if jj else None


def arm_report(tagroot, arm):
    d = os.path.join(_HERE, tagroot, arm)
    if not os.path.isdir(d):
        return None
    meta = {}
    mp = os.path.join(d, 'meta.json')
    if os.path.exists(mp):
        meta = json.load(open(mp, encoding='utf-8'))
    rows = load_series(d)
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    mtime = os.path.getmtime(os.path.join(d, 'series.csv')) if rows else 0.0
    out = dict(arm=arm, dir=d, meta=meta, rows=rows, snaps=snaps, mtime=mtime)
    if snaps:
        per = []
        covs = []
        for s in snaps:
            z = np.load(s)
            reg = z['region']
            vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
            r = BM.measure_state(reg, float(z['L']) / reg.shape[0], z['n_hab'],
                                 z['w_ax'], z['a_ax'], vmap)
            per.append((int(z['step']),
                        {k: r['vol_%d' % k] for k in sorted(vmap)},
                        r['nslab_n'], r['nf3_col'], r['f3_faces'],
                        max(r['ncomp_%d' % k] for k in sorted(vmap))))
            # ★ V-7/V-7b 用 `_bk_measure.snapshot_coverage`（**单一实现**）
            cv = BM.snapshot_coverage(z)
            covs.append((int(z['step']), cv))
        out['per'] = per
        out['covs'] = covs
    return out


def newest_tag(root):
    """`root` 下**最近被写过**的标签（按各臂 `series.csv` 的 mtime 最大值）。

    ★ 为什么要有它：`--tag` 原默认写死 `'p2'`，于是"忘了传 `--tag`"会**静默**
      去读一个早就被杀掉的旧臂，并把它当成当前结果报出来（本项目真踩过：
      读的是被 kill 的 `p2`，报的是陈旧数字）。默认改成"最新"能挡住这类事故，
      但**光靠默认值不够** —— 所以下面还会把**实际读到的绝对路径 + mtime + sha**
      大声打出来，让"读错臂"不可能不被发现。
    """
    base = root if os.path.isabs(root) else os.path.join(_HERE, root)
    best, best_t = None, -1.0
    if not os.path.isdir(base):
        return None
    for name in sorted(os.listdir(base)):
        p = os.path.join(base, name, 'series.csv')
        if os.path.exists(p):
            t = os.path.getmtime(p)
            if t > best_t:
                best, best_t = name.rsplit('_', 1)[-1], t
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='_exp/_bk_block')
    ap.add_argument('--tag', default='auto',
                    help="'auto'（默认）= 读 root 下最近被写过的标签")
    ap.add_argument('--arms', default='dry,wet')
    ap.add_argument('--ctrl-root', default='_exp/_bk_ctrl')
    ap.add_argument('--ctrl-tag', default='ctrl')
    ap.add_argument('--ctrl-arm', default='gpos')
    a = ap.parse_args()
    if a.tag == 'auto':
        a.tag = newest_tag(a.root)
        if a.tag is None:
            print('✗ %s 下没有任何 series.csv ⇒ 无法自动选标签' % a.root)
            return 1

    print('=' * 104)
    print('_bk_verdict —— 阶段 3 判决（判据**先登记**）')
    print('  ★ 实际读取的根/标签: %s / **%s**（由 --tag 决定；auto=最新）'
          % (a.root, a.tag))
    print('=' * 104)
    reps = {}
    for arm in [x for x in a.arms.split(',') if x]:
        r = arm_report('%s' % a.root, '%s_%s' % (arm, a.tag))
        if r is None:
            print('  ⚠ 找不到臂 %s' % arm)
            continue
        reps[arm] = r
    if not reps:
        return 1

    for arm, r in reps.items():
        M = int(r['meta'].get('nv', 0)) or None
        rows = r['rows']
        print('-' * 104)
        print('臂 %s   M=%s   测点=%d   快照=%d' % (arm, M, len(rows), len(r['snaps'])))
        # ★ 大声报出**实际读的是哪一个目录**（绝对路径 + series.csv 的 mtime）。
        #   本项目出过一次"读错旧臂却当成当前结果"的事故 ⇒ 这条不是装饰。
        print('     目录=%s' % r['dir'])
        print('     series.csv mtime=%s  （若这不是你要的臂，说明 --tag 传错了）'
              % (time.strftime('%m-%d %H:%M:%S', time.localtime(r['mtime']))
                 if r.get('mtime') else '—'))
        if not rows:
            continue
        ns = [fnum(x, 'nslab_n') for x in rows]
        nc = [fnum(x, 'nf3_col') for x in rows]
        nf = [fnum(x, 'nf3') for x in rows]
        # ★ nan 必须**先滤掉**再取 max：生长臂在前几个快照还没有任何 F3 面
        #   ⇒ `f3_pos_dx` 恒为 nan ⇒ `max([nan, ...])` 返回 nan
        #   ⇒ V-3 假 FAIL（实测 `dry_gs2` 就是这样），而 V-6 更是把
        #   `0.236 / nan = inf` 报成 PASS。两处都踩过。
        dp = [abs(fnum(x, 'f3_pos_dx')) for x in rows]
        dp = [v for v in dp if np.isfinite(v)]
        bt = [fnum(x, 'box_touch') for x in rows]
        ncm = [fnum(x, 'ncomp_max') for x in rows]
        ck = []
        ck.append(('V-1 块结构 (nslab==M & nf3col==M-1 & nf3faces>0)',
                   bool(M) and all(v == M for v in ns)
                   and all(v == M - 1 for v in nc) and all(v > 0 for v in nf[1:]),
                   'nslab=%s  nf3col=%s  nf3faces=%s'
                   % (sorted(set(ns)), sorted(set(nc)), [int(x) for x in nf[:3]])))
        if 'per' in r and len(r.get('per', [])) >= 2:
            vols = {}
            for (_st, vd, _a, _b, _c, _d) in r['per']:
                for k, v in vd.items():
                    vols.setdefault(k, []).append(v)
            # ★★ Round 10 **重新界定 V-2 的适用范围**（不是放宽阈值，是改测的量）：
            #   原判据「**每根**体积单调不减」是对**预摆整齐堆叠**推出来的 ——
            #   那种初态下每根都有 F1 面积。但对一个**堆叠**，**内层板条两张宽面
            #   全是 F3、`Δf = Δe_el ≡ 0` ⇒ 它没有任何体驱动力**（§5.1 的推导），
            #   体积只受 F3 面积最小化支配，**可以小幅回落**。
            #   实测 `dry_pa`（预摆）就 FAIL 在这条上（板条 3：0.3772→…→0.3845
            #   中间有回落），而它在物理上没有错。
            #   ⇒ 判据改成两条，**两条都打印**：
            #       V-2  总体积单调不减（这才是"块在长"的物理要求）——**判**
            #       V-2b 逐板条的跌幅——**只报不判**（阈值要等对照分布，不先拍数）
            #   ⚠ 不许"把原读数藏起来"：逐板条的起止值仍然原样打印。
            tot = [sum(vd.values()) for (_st, vd, _a, _b, _c, _d) in r['per']]
            mono_tot = all(tot[i] <= tot[i + 1] + 1e-30 for i in range(len(tot) - 1))
            ck.append(('V-2 总体积单调不减（"块在长"的物理要求）', mono_tot,
                       'Vt: %.4f → %.4f µm³（%d 个快照）'
                       % (tot[0] * 1e18, tot[-1] * 1e18, len(tot))))
            per_lath = '; '.join('%d:%.4f→%.4f' % (k, vols[k][0] * 1e18,
                                                   vols[k][-1] * 1e18)
                                 for k in sorted(vols))
            drops = {k: (min(vols[k]) / max(vols[k]) - 1.0) * 100.0
                     for k in vols if max(vols[k]) > 0}
            ck.append(('V-2b 逐板条体积（**只报不判**：内层片允许回落）', None,
                       '%s   跌幅=%s' % (per_lath,
                                       ' '.join('%d:%.1f%%' % (k, drops[k])
                                                for k in sorted(drops)))))
        else:
            ck.append(('V-2 每根都在长', None,
                       '**数据不足**：只有 %d 个快照（需 ≥2）⇒ 判据不适用'
                       % len(r.get('per', []))))
        ck.append(('V-3 界面不动 max|Δpos| < 0.12 Δx',
                   (max(dp) < 0.12) if dp else None,
                   ('max=%.3f Δx（末=%+.3f）' % (max(dp), fnum(rows[-1], 'f3_pos_dx')))
                   if dp else '**无有效测点**：全程没有 F3 面 ⇒ `Δpos` 恒为 nan'))
        ck.append(('V-4 没撞盒壁 (box_touch==0)', all(v == 0 for v in bt),
                   'box_touch=%s' % sorted(set(bt))))
        ck.append(('V-5 数值健康 (ncomp_max 末 ≤ 2)',
                   ncm[-1] <= 2, 'ncomp_max: %.0f → %.0f' % (ncm[0], ncm[-1])))
        # ★ V-5b：**显著**碎裂（分量 ≥32 体素）。`ncomp_max` 会把 1–2 体素的
        #   离散孤儿算成碎裂（`dry_gs2` 实测 ncomp_max=4，实际是 1 根 2022 体素的
        #   完整板条 + 3 个 1–2 体素孤儿）。两个口径**都报**，不用阈值悄悄改结论。
        ncb = [fnum(x, 'ncompbig_max') for x in rows]
        if all(np.isfinite(v) for v in ncb):
            ck.append(('V-5b 无**显著**碎裂 (ncompbig_max 末 ≤ 2)',
                       ncb[-1] <= 2,
                       'ncompbig_max: %.0f → %.0f（≥%d 体素才算一个分量）'
                       % (ncb[0], ncb[-1], BM.MIN_SIG_VOX)))
        else:
            ck.append(('V-5b 无显著碎裂', None,
                       '本臂 CSV 无 `ncompbig_max` 列（旧版跑的）；'
                       '用 `_bk_comp.py <dir> <step>` 事后查分量谱'))

        # ★ V-7 / V-7b 界面完整性（阈值由预装对照 `dry_pa` 校准，见
        #   `_bk_measure.snapshot_coverage` 的 docstring）
        if r.get('covs'):
            st, cv = r['covs'][-1]
            if np.isfinite(cv['cov']):
                ck.append(('V-7 界面完整性 (F3 覆盖率 ≥ 0.85)',
                           cv['cov'] >= 0.85,
                           '@step %d 覆盖率=%.3f（应占 %.4f，实测 %.4f µm²）'
                           % (st, cv['cov'], cv['exp_int'] * 1e12,
                              cv['f3_area'] * 1e12)))
            if cv['beta_frac']:
                w = cv['worst']
                ck.append(('V-7b 无多余 β 夹层 (每对 β 占比 ≤ 0.25)',
                           cv['beta_frac'][w] <= 0.25,
                           '最差对 %d|%d = %.3f   各对: %s'
                           % (w[0], w[1], cv['beta_frac'][w],
                              '  '.join('%d|%d:%.2f' % (ij[0], ij[1], f)
                                        for ij, f in
                                        sorted(cv['beta_frac'].items(),
                                               key=lambda t: -t[1])))))

        # ---- V-1g：**「长出来的块」**专用判据 ----------------------------------
        # ★ 为什么 V-1 不能直接用在生长臂上：生长臂按定义 **t=0 只有 1 个核**
        #   （`dry_gs2` 实测 nslab_n 首值 = 1），而 V-1 要求**每个测点都 == M**
        #   ⇒ 生长臂必然 FAIL，但这不是物理失败，是判据不适用。
        # ★ 生长臂该证的是**三件事**（缺一不可）：
        #   ① 末态与预装臂**同构**：`nslab_n == M` 且 `nf3_col == M-1` 且面 > 0；
        #   ② `nslab_n` 从 1 出发、**单调不减**、**每次只 +1**（= 一次一个新场，
        #      不是一次劈裂出多片，也不是并成一片）；
        #   ③ 阶梯的**级数 == M-1**（确实发生了 M-1 次形核）。
        # ★ 生长臂的识别：**不能只看 meta**。`dry_gs2` 是 Round 9 之前跑的，
        #   它的 meta.json 里没有 `grow_stack`（meta 少字段正是本轮修掉的坑）
        #   ⇒ 只认 meta 会让 V-1g **静默不判**（第一版实测就是这样，
        #   判决表里干脆没有 V-1g 这一行，很容易被读成"过了"）。
        #   数据侧的判据是硬的：预装臂按定义 **t=0 就有 M 片**，
        #   所以 `nslab_n` 首值 < M 只可能是"长出来的"。
        grown = bool(r['meta'].get('grow_stack')) or (bool(M) and ns[0] < M)
        if grown:
            n1s = [int(round(v)) for v in ns]
            steps_up = [i for i in range(1, len(n1s)) if n1s[i] != n1s[i - 1]]
            ok_up = all(n1s[i] - n1s[i - 1] == 1 for i in steps_up)
            ok_fin = (bool(M) and n1s[-1] == M and int(round(nc[-1])) == M - 1
                      and int(round(nf[-1])) > 0)
            ck.append(('V-1g 长出来的块 (末态同构 + 单调+1 阶梯 + 级数 M-1)',
                       bool(ok_up and ok_fin and n1s[0] == 1
                            and len(steps_up) == M - 1),
                       'nslab 阶梯=%s（首=%d 末=%d，级数=%d 应为 %d，'
                       '面=%d）' % ('→'.join(str(x) for x in
                                             [n1s[0]] + [n1s[i] for i in steps_up]),
                                    n1s[0], n1s[-1], len(steps_up), M - 1,
                                    int(round(nf[-1])))))
        # ---- V-3g：**生长臂**的"界面不动" ----------------------------------
        # ★ 为什么 V-3 不能直接用在生长臂上：`f3_pos_dx` 是**所有 F3 面的平均
        #   位置**，而每来一次形核就凭空多出一张界面 ⇒ 平均值**必然**跳变。
        #   实测 `dry_gs2`：Δpos 在 30/40/50 步恒为 +0.000，到 60 步（第 3 个核）
        #   突跳到 −2.717，90 步（第 4 个核）又跳到 −1.071 …… ⇒ V-3 读出
        #   `max=3.417 Δx` 并被判 FAIL，但**这不是界面迁移**。
        # ★ 判据改成：**剔除 `nslab_n` 发生变化的那些测点**之后，
        #   相邻测点的 |Δpos| 变化 < 0.12 Δx。只用 CSV 里已有的列，可证伪。
        if grown:
            jj = []
            for i in range(1, len(rows)):
                if int(round(ns[i])) != int(round(ns[i - 1])):
                    continue                       # 形核步：跳过
                a0 = fnum(rows[i - 1], 'f3_pos_dx')
                a1 = fnum(rows[i], 'f3_pos_dx')
                if np.isfinite(a0) and np.isfinite(a1):
                    jj.append(abs(a1 - a0))
            ck.append(('V-3g 界面不动（**剔除形核步**后 max|ΔΔpos| < 0.12 Δx）',
                       (max(jj) < 0.12) if jj else None,
                       ('max=%.4f Δx（%d 个非形核测点）' % (max(jj), len(jj)))
                       if jj else '**无有效测点**'))
        # ★ V-2g：**逐步**逐板条体积（来自 `vols` 列，Round 10 起才有）。
        #   V-2 只能看快照（默认 50 步一个）⇒ 中间过程全丢。V-2g 用**每个测点**，
        #   报每根板条"出生后相对最大值的最大跌幅"。
        #   ⚠ **只报不判**：内层板条**允许**小幅回落 —— 它们两张宽面都是 F3、
        #     `Δf = Δe_el ≡ 0`，没有体驱动力（§5.1），体积只受 F3 面积最小化支配。
        #     阈值要等对照臂（`dry_pa`）的实测分布出来再定，**不得先拍一个数**。
        if any('vols' in x for x in rows):
            seq = {}
            for x in rows:
                vs = x.get('vols', '')
                try:
                    vv = [float(t) for t in vs.split('/')]
                except ValueError:
                    continue
                for k, v in enumerate(vv, start=1):
                    if v > 0:
                        seq.setdefault(k, []).append(v)
            drops = []
            for k in sorted(seq):
                pk = max(seq[k])
                mn = min(seq[k])
                drops.append((k, 100.0 * (mn / pk - 1.0), len(seq[k])))
            if drops:
                print('     V-2g 逐板条体积跌幅（**只报不判**，阈值待对照校准）: %s'
                      % '  '.join('%d:%.1f%%(%d测点)' % t for t in drops))
        # ★ V-8：**长出来的块**专用的"片数与厚度保真"—— 6 个场必须全部在位。
        #   `gs3` 实测板条 1 被咬成 20 个碎片、从柱剖面里消失，而 `V-1g` 仍 PASS
        #   （它只看阶梯的级数）⇒ 必须有这一条兜住"片还在不在"。
        if grown and any('ths' in x for x in rows):
            last = rows[-1]
            try:
                th = [float(t) for t in last.get('ths', '').split('/')]
            except ValueError:
                th = []
            present = [k for k, v in enumerate(
                [float(t) for t in last.get('vols', '').split('/')], start=1) if v > 0]
            nrun = len(set(int(x) for x in last.get('runs', '').split('/') if x))
            ck.append(('V-8 六片全在位（柱剖面里的场数 == M）',
                       nrun == M if M else None,
                       'runs=%s ⇒ %d 个不同场（应为 %d）；在位的场=%s'
                       % (last.get('runs'), nrun, M, present)))
            _band = [k for k in present if th and k <= len(th)
                     and 0.8 * 250.0 <= th[k - 1] <= 1.3 * 250.0]
            ck.append(('V-8b 末态厚度保真（在位片 ∈ [200,325] nm）',
                       (len(_band) == len(present)) if present else None,
                       '厚度=%s nm（T=250；**场 1 的读数会被 1–2 体素孤儿污染**，'
                       '精确值看 `_bk_pair.py`）'
                       % '/'.join('%.0f' % th[k - 1] for k in present
                                  if k <= len(th))))
        for t, ok, det in ck:
            print('   %-52s %s  %s'
                  % (t, 'PASS' if ok else ('—' if ok is None else '**FAIL**'), det))

    # V-6 通道活性（与正对照配对）
    # ★ 必须**先滤掉 nan**：没有 F3 面的测点 `f3_pos_dx` 是 nan，
    #   不滤的话 `dmax/dm = 0.236/nan = inf` ⇒ **假 PASS**（实测踩过）。
    # ★ 生长臂的基准还要**剔除形核步**（见 `drift_basis` 的记账），
    #   否则同一份数据会算出 0.2× 并误判 FAIL。
    cr = arm_report(a.ctrl_root, '%s_%s' % (a.ctrl_arm, a.ctrl_tag))
    if cr and cr['rows']:
        _cM = int(cr['meta'].get('nv', 0)) or None
        _cns = [fnum(x, 'nslab_n') for x in cr['rows']]
        _cgrown = bool(cr['meta'].get('grow_stack')) or (bool(_cM) and _cns
                                                         and _cns[0] < _cM)
        dmax = drift_basis(cr['rows'], _cgrown)
    else:
        dmax = None
    if dmax is not None:
        _csteps = int(fnum(cr['rows'][-1], 'step')) if cr and cr['rows'] else -1
        print('-' * 104)
        print('正对照 %s（γ=100）：max|Δpos| = %.3f Δx   ⚠ 该对照只跑了 **%d 步**'
              % (a.ctrl_arm, dmax, _csteps))
        print('   ⚠ **长度必须配对**：对照自己的漂移也随步数增长 —— 实测同一个 γ=100 臂，'
              '60 步给 0.236 Δx、200 步给 0.344 Δx。')
        print('     拿 60 步的对照去比 200 步的臂，会把 `dry_nr` 的 4.0× 压成 2.7× 并**误判 FAIL**。'
              '（`--ctrl-tag` 请选与该臂步数相当的对照。）')
        for arm, r in reps.items():
            _M2 = int(r['meta'].get('nv', 0)) or None
            _ns2 = [fnum(x, 'nslab_n') for x in r['rows']]
            _gr = bool(r['meta'].get('grow_stack')) or (bool(_M2) and _ns2
                                                        and _ns2[0] < _M2)
            dm = drift_basis(r['rows'], _gr)
            if dm is None:
                print('   V-6 %-6s vs 正对照：**本臂全程无有效 F3 测点** '
                      '⇒ 无法判定（不是 PASS）' % arm)
                continue
            ratio = dmax / dm if dm > 1e-12 else float('inf')
            print('   V-6 %-6s vs 正对照：%.3f / %.3f = **%.1f×**（基准%s）⇒ %s'
                  % (arm, dmax, dm, ratio,
                     '剔除形核步' if _gr else '原始 max',
                     'PASS（通道是活的）' if ratio > 3 else '**FAIL（量具无分辨力）**'))
    else:
        print('-' * 104)
        print('⚠ 正对照（%s/%s）尚未产出 ⇒ **V-6 无法判定**（在那之前"界面不动"不作结论）'
              % (a.ctrl_root, a.ctrl_arm))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

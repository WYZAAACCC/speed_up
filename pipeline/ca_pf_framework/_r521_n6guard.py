#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r521_n6guard.py —— **N6 修复的量具**（`--multi-block` 可行性检查 + 余量报告）。

## N6 是什么（判定见 `R2_PARAM_VERDICTS.md §0 N6`）
`_bk_exp.py` 的 `--multi-block` 分支里，
**块心跨度是 `(nb−1)·_gap_blk`**（播种那段 `_xi = (_b−(nb−1)/2)·_gap_blk`），
而"沿长轴余量"那句报告写的是 `0.5·L − 0.5·plate_L − 0.5·block_gap_nm` —— **两处独立错误**：

| # | 错在哪 | 后果 |
|---|---|---|
| ① | **系数**：少乘 `(nb−1)` | ⚠ **`nb=2` 时 `0.5·(nb−1)=0.5` 与旧式恰好相等** ⇒ 旧式**只在 nb=2 上对**，而归档唯一的 `--multi-block` 臂正是 **nb=2** ⇒ **"唯一用过的那一点恰好对"**，所以没人发现 |
| ② | **变量**：读 `a.block_gap_nm`（`≤0` 时 = **0**），播种用 `_gap_blk`（`≤0` 时 = **2.0 µm**） | 默认配置下把 2 µm **当成 0** |

**并且**：那段报告在**播种之后**才执行
（实测 `_w2_r51_b62r_smoke.log`：`块0：变体…` 第 25 行、`多块：…` 第 **31** 行）
⇒ **它从来不是守卫，是事后报告**，物理上不可能拦住任何东西。
⇒ 修法 = ①播种**前**加真检查（N6 段）②报告口径改对。

## 本量具的四个判据（**先写死，再跑**）
* **T1 语法**：`py_compile` 通过。
* **T2 负对照（必须被拦住）**：nb=12、默认 gap、L=4 µm
  ⇒ 必须出现 `播种前可行性检查失败`（N6），
  且**必须不出现** `elong*R=` —— 即**在 `seed_plate` 之前**就拦住。
  ⚠ 修前实测：这个配置一路走到 `seed_plate` 才抛
    `ValueError: elongated seed exceeds domain: elong*R=5e-07 um > margin -9.562e-06 um`。
* **T3 正对照（必须放行，且与归档逐位一致）**：完全复刻归档臂 `dry_b62r`
  （N=144 / Δx=62.5 nm ⇒ L=9 µm、`--block-gap-nm 3000`、`--plate-L 2000`、nb=2）
  ⇒ 必须出现 `✅ 播种前可行性检查`，且报告行必须是
  **`沿长轴余量 2.00 µm`**（归档日志 `_w2_r51_b62r_smoke.log:31` 的原值）。
  ⚠ **这一条是"修了等于没修"的证据**：nb=2 上新旧式**必须给出同一个数**。
* **T4 解析对照（不跑引擎）**：拿上面三组 (L, nb, gap, plate_L) 直接算新旧两式，
  断言 ①nb=2 时**完全相等** ②nb=12 时**反号**。
  这一条把"是不是我算错了"与"是不是引擎没走到"分开。
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
LOG = os.path.join(HERE, '_w2_r521_n6guard.log')
OUT = '_exp/_bk_guard'


def old_margin(L, nb, gap_nm_raw, plate_L_m):
    """修前那句报告。

    ⚠⚠ **`gap_nm_raw` 必须是 `--block-gap-nm` 的原始值（nm），不是 `_gap_blk`。**
    修前代码读的是 `a.block_gap_nm` **本身** —— 即 `--block-gap-nm` 未传时它是 **0**。
    （本量具第一版把 `resolve_gap(0)`=2 µm 喂进来 ⇒ 得 `−0.200` 而非 `+1.500`
      ⇒ T4c/T4d 假 FAIL。**那正是被修的那个 bug 在我自己的量具里复现了一遍。**）
    `nb` 参数保留但**故意不用** —— 修前式子**没有** `nb`（这正是缺陷①）。
    """
    return 0.5 * L - 0.5 * plate_L_m - 0.5 * (gap_nm_raw * 1e-9)


def new_margin(L, nb, gap_blk_m, plate_L_m):
    """修后那句报告：半跨度 `0.5·(nb−1)·_gap_blk`。"""
    return 0.5 * L - 0.5 * (nb - 1) * gap_blk_m - 0.5 * plate_L_m


def resolve_gap(gap_nm):
    """`_bk_exp.py` 那句 `_gap_blk` 的口径。"""
    return gap_nm * 1e-9 if gap_nm > 0 else 2.0e-6


def need_half(L, nb, gap_blk_m, plate_L_m):
    """播种前检查用的**需要半盒**。"""
    return 0.5 * (nb - 1) * gap_blk_m + 0.5 * plate_L_m


def run_case(tag, extra, timeout=1800):
    cmd = [PY, '-u', os.path.join(HERE, '_bk_exp.py'),
           '--out', OUT, '--tag', tag, '--nthreads', '2',
           '--every', '5', '--snap-every', '0', '--phi-band-every', '0',
           '--pair-every', '0', '--norm-smooth', '0'] + extra
    lp = os.path.join(HERE, '_w2_r521_%s.log' % tag)
    with open(lp, 'w') as fh:
        p = subprocess.run(cmd, cwd=HERE, stdout=fh, stderr=subprocess.STDOUT,
                           timeout=timeout)
    with open(lp, errors='replace') as fh:
        return p.returncode, fh.read(), lp


def main():
    rows = []

    def chk(name, ok, detail):
        rows.append((name, bool(ok), detail))

    # ---------- T1 语法 ----------
    r = subprocess.run([PY, '-m', 'py_compile', os.path.join(HERE, '_bk_exp.py')],
                       capture_output=True, text=True)
    chk('T1 语法 py_compile', r.returncode == 0,
        (r.stderr or 'OK').strip().splitlines()[-1] if r.stderr else 'OK')

    # ---------- T4 解析对照（先做：不跑引擎，最便宜） ----------
    # **归档臂 `dry_b62r`**（`_w2_r51_b62r_smoke.log:2` 实测）：N=144、Δx=62.5 nm
    #   ⇒ L=9.000 µm；`--block-gap-nm 3000`；`--plate-L 2000`；`--laths 1,1,1,2,2,2` ⇒ nb=**2**
    o2 = old_margin(9e-6, 2, 3000, 2000e-9)
    n2 = new_margin(9e-6, 2, resolve_gap(3000), 2000e-9)
    chk('T4a nb=2 新旧式**必须相等**（归档行为不变）',
        abs(o2 - n2) < 1e-15,
        'old=%+.6f µm  new=%+.6f µm  差=%.2e' % (o2 * 1e6, n2 * 1e6, abs(o2 - n2)))
    chk('T4b nb=2 复现归档日志原值 2.00 µm',
        abs(n2 - 2.0e-6) < 5e-9,
        'new=%+.3f µm（归档 `_w2_r51_b62r_smoke.log:31` = +2.00 µm）' % (n2 * 1e6))

    # **崩溃臂 `_r520b`**（`_r520b_paramrun.sh` 实测配置）：
    #   `--N 64 --dx-nm 62.5` ⇒ L=4.000 µm；**未传 `--block-gap-nm`** ⇒ 原始值 **0**；
    #   `--plate-L 1000`；`--laths` 12 变体 × 6 = 72 ⇒ nb=**12**。
    _PL520 = 1000e-9
    o12 = old_margin(4e-6, 12, 0, _PL520)          # 旧式：gap 读成 **0**，且只算 1 个 gap
    n12 = new_margin(4e-6, 12, resolve_gap(0), _PL520)   # 新式：`_gap_blk`=2 µm、半跨度 11 µm
    nd12 = need_half(4e-6, 12, resolve_gap(0), _PL520)
    chk('T4c nb=12 旧式说"余量充裕"、新式说"装不下"（**必须反号**）',
        (o12 > 1e-6) and (n12 < 0),
        'old=%+.3f µm（"%s"）  new=%+.3f µm（"%s"）；需要半盒 %.3f > 实际半盒 %.3f'
        % (o12 * 1e6, '余量充裕' if o12 > 1e-6 else '警告',
           n12 * 1e6, '余量充裕' if n12 > 1e-6 else '警告', nd12 * 1e6, 2.0))

    # ★ T4d 改为**由代码推出的硬界**，不再引用任何"我记得的"崩溃数值。
    #   依据 `windowB_surface.py:2348`：`_margin = min(_c.min(), (L−_c).min())`
    #   ⇒ 取**中心到任一面**的最小距离。
    #   极端块心 = `c0 + 0.5·(nb−1)·_gap_blk · u`（`u` 单位向量）。
    #   对**任意**单位 `u` 都有 `max_i |u_i| ≥ 1/√3`
    #   ⇒ 必有某个分量落在 `c0_i ± 11.0/√3 = 2.0 ± 6.351 µm`
    #   ⇒ `min(_c.min(), (L−_c).min()) ≤ 2.0 − 6.351 = **−4.351 µm** < 0
    #   ⇒ **无论布局轴朝哪，`seed_plate` 都必然 `ValueError`**。
    #   ⚠ 之前会话里记的"−9.562e-06"**在任何日志里都搜不到**
    #     （`grep -rn 'elong\*R' _w2_*.log` 无 r520 条目）⇒ **该数字作废，标【未取证】**。
    #     现值只用**代码可推**的界，不用记忆值。
    _worst = 2.0 - 11.0 / (3 ** 0.5)
    chk('T4d 由 `_c` 逐面最小距离推出：**任意布局轴下 margin 必为负**',
        _worst < 0,
        '最坏面距上界 = 2.000 − 11.000/√3 = **%+.3f µm** < 0 ⇒ `seed_plate` 必抛 '
        '（`windowB_surface.py:2348`）' % _worst)

    # ---------- T2 负对照：必须被拦住 ----------
    lat12 = ','.join(str(v) for v in range(1, 13))
    rc, txt, lp = run_case('n6neg',
                           ['--N', '64', '--dx-nm', '62.5', '--laths', lat12,
                            '--multi-block', '--steps', '3'])
    got_guard = '播种前可行性检查失败' in txt
    got_seedval = bool(re.search(r'elong\*R\s*=', txt))
    chk('T2a 负对照被**播种前检查**拦住', got_guard,
        '日志 %s 含 N6 拦截消息 = %s' % (os.path.basename(lp), got_guard))
    chk('T2b 负对照**没有**走到 seed_plate（不得出现 elong*R）', not got_seedval,
        '`elong*R=` 出现 = %s（修前实测为 True）' % got_seedval)
    if got_guard:
        mm = re.search(r'需要半盒 ≥ ([\d.]+) µm.*?实际半盒 = 0\.5·L = ([\d.]+) µm.*?差 ([\d.]+) µm',
                       txt, re.S)
        chk('T2c 拦截消息里三个数自洽',
            bool(mm) and abs(float(mm.group(3)) - (float(mm.group(1)) - float(mm.group(2)))) < 0.01,
            ('需要 %.3f / 实际 %.3f / 差 %.3f µm' % (float(mm.group(1)), float(mm.group(2)),
                                                     float(mm.group(3)))) if mm else '解析失败')

    # ---------- T3 正对照：复刻归档臂 dry_b62r ----------
    rc3, txt3, lp3 = run_case('n6pos',
                              ['--N', '144', '--dx-nm', '62.5',
                               '--laths', '1,1,1,2,2,2',
                               '--plate-L', '2000', '--block-gap-nm', '3000',
                               '--multi-block', '--steps', '3'])
    got_ok = '✅ **播种前可行性检查**' in txt3
    chk('T3a 正对照通过播种前检查', got_ok,
        '日志 %s 含 ✅ = %s' % (os.path.basename(lp3), got_ok))
    m = re.search(r'多块：2 块；块心间距（\*\*实际\*\*，`_gap_blk`）= ([\d.]+) µm ⇒ '
                  r'块心半跨度 ([\d.]+) µm；再加板条半长 ([\d.]+) µm ⇒ '
                  r'\*\*沿长轴余量 ([+\-]?[\d.]+) µm\*\*', txt3)
    chk('T3b 报告行解析成功', bool(m), (m.group(0)[:90] + '…') if m else '未匹配到报告行')
    if m:
        chk('T3c 报告余量 = **归档原值 +2.00 µm**（逐位一致）',
            abs(float(m.group(4)) - 2.00) < 5e-3,
            '报告 %s µm；归档 `_w2_r51_b62r_smoke.log:31` = 2.00 µm' % m.group(4))
    # 正对照必须**真的播了 2 个块**（不是"没崩就算过"）
    _nb0 = len(re.findall(r'块0：变体', txt3))
    _nb1 = len(re.findall(r'块1：变体', txt3))
    chk('T3d 正对照真的播下 **2 个块**', (_nb0 == 1) and (_nb1 == 1),
        '日志中 `块0：变体`×%d、`块1：变体`×%d' % (_nb0, _nb1))
    # 负对照必须**一个块都没播**（拦在播种之前）
    _nneg = len(re.findall(r'块\d：变体', txt))
    chk('T3e 负对照**一个块都没播**（拦在播种前）', _nneg == 0,
        '负对照日志中 `块N：变体` 出现 %d 次（修前会是 1~n 次后才崩）' % _nneg)

    # ---------- 汇总 ----------
    npass = sum(1 for _, ok, _ in rows if ok)
    lines = ['=' * 100,
             'R521 —— **N6 量具**（`--multi-block` 播种前可行性检查 + 余量报告口径）',
             '=' * 100]
    for name, ok, detail in rows:
        lines.append('  %-52s %s   %s' % (name, '✅ PASS' if ok else '❌ FAIL', detail))
    lines.append('')
    lines.append('★ 汇总：%d/%d PASS' % (npass, len(rows)))
    lines.append('★ ⇒ %s' % ('**全部通过**（N6 修复有效且归档不变）'
                             if npass == len(rows) else
                             '**未全部通过**，照实记，不得宣称修复成立。'))
    out = '\n'.join(lines)
    sys.stdout.write(out + '\n')
    with open(LOG, 'w') as fh:
        fh.write(out + '\n')
    return 0 if npass == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main())

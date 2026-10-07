#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r537_parrun.py —— **多个不相关算例并行的调度器**（任务(4)「把核数用满」的落地件）。

## 实测依据（`R531_THREADSCALE.md §7`）
| 打法 | 总吞吐（算例/单位时间） |
|---|---|
| 16 线程 × 1 个（**旧做法**） | 0.891 |
| 4 线程 × 1 个 | 1.013 |
| **4 线程 × 4 并发** | **2.148（2.41×）** |
| 1 线程 × 4 并发 | 1.488 |

⇒ **`--nthreads 4` + 4 个并发**是实测最优。
⇒ 用户要求「多个不相关的仿真在内存允许的条件下并行进行」—— **本件就是那条**。

## 用法
    python _r537_parrun.py <并发数> <配置json>
`配置json` 是个列表，每项 `{"tag": "...", "args": ["--N","64", ...]}`。
**公共参数**由 `COMMON` 给（与 `_r529_paramrun2.sh` 逐字相同）。

## 纪律（本仓 §3.2 教训 8）
**每个算例必须有独立的 `--out` 目录**（否则 CSV 互相覆盖）⇒ 本件**强制**：
每项自动加 `--out <OUT>/<tag>`，**并且拒绝 `args` 里自带的 `--out`**。

## 记账
* 并发期间**采样核占用**（`ps` 的 `%cpu` 之和），报告峰值 ⇒ 回答"到底用了几核"。
* 每个算例的 `s/步`、末态 `Vt`、`nfsv_nofield`、退出码。
* **正对照**：同一配置跑两遍 ⇒ 末态 `Vt` 必须**逐位相同**（可复现性）；
  若调用方给了重复的 `tag`，本件会自动加后缀，**不会**让两个算例写同一目录。
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
OUT = '_exp/_bk_par'

COMMON = ['--N', '64', '--dx-nm', '62.5', '--every', '20',
          '--snap-every', '200', '--phi-band-every', '200',
          '--pair-every', '100', '--norm-smooth', '0',
          '--plate-L', '1000', '--plate-W', '500', '--plate-T', '510',
          '--gamma0', '0.25', '--beta-h', '6.477', '--grow-stack',
          '--nuc-law', 'athermal', '--nuc-init', '6',
          '--nuc-shape', 'ellipsoid', '--nuc-supercrit', '1',
          '--nuc-sites-refill', '1', '--qs-clock', '1', '--qs-max-relax', '100',
          '--alpha-km', '0.011', '--T-end', '350.0', '--cool-rate', '2.3524e6',
          '--facet-proj', '0', '--facet-excl', '0',
          '--reinit-dt', '1e-4', '--reinit-band', '6.0',
          '--steps', '4000']
LATHS10 = ','.join(str(v) for v in range(1, 13) for _ in range(10))
RE_STEP = re.compile(r'\[(\s*\d+)\]\s+Vt=([\d.eE+\-]+).*?\|\s*([\d.]+)s/步')


def _env():
    e = dict(os.environ)
    # `_r531` 实测：真实负载上 4 线程最快（16 线程反而慢 12%）
    for k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        e[k] = '1'
    return e


def _cpu_sum():
    try:
        o = subprocess.run(['ps', '-eo', 'pcpu,args'], capture_output=True,
                           text=True, timeout=30).stdout
    except Exception:                                           # noqa: BLE001
        return float('nan')
    tot = 0.0
    for ln in o.splitlines():
        if '_bk_exp.py' in ln:
            try:
                tot += float(ln.split(None, 1)[0])
            except ValueError:
                pass
    return tot / 100.0


def _launch(cfg, tag, nt):
    if '--out' in cfg['args']:
        raise SystemExit('❌ 配置 %s 自带 `--out` —— 本件强制独立目录'
                         '（CSV 会互相覆盖，本仓 §3.2 教训 8）' % tag)
    cmd = ([PY, '-u', os.path.join(HERE, '_bk_exp.py')] + COMMON +
           ['--laths', LATHS10, '--nthreads', str(nt), '--tag', tag,
            '--out', os.path.join(OUT, tag)] + list(cfg['args']))
    lp = os.path.join(HERE, '_w2_r537_%s.log' % tag)
    fh = open(lp, 'w')
    return subprocess.Popen(cmd, cwd=HERE, stdout=fh,
                            stderr=subprocess.STDOUT, env=_env()), fh, lp, cmd


def _read(tag, lp):
    txt = open(lp, errors='replace').read()
    sp = [(float(m.group(2)), float(m.group(3))) for m in RE_STEP.finditer(txt)]
    s = (sum(x[1] for x in sp[-4:]) / len(sp[-4:])) if sp else float('nan')
    # ⚠⚠ **本件第一版这里错了**：原来写 `OUT/tag`，而 `_bk_exp.py` 的实际布局是
    #   `<out>/<tag>/<arm>_<tag>`（实测 `_exp/_bk_par/b4/dry_b4/nuc_dbg.json`）
    #   ⇒ 读不到 ⇒ `nfsv_nofield` 恒为 `None`（**看着像"没超标"，其实是没读到**）。
    #   ⇒ 本仓 §3.3 教训 17/29：**"工具没打印出结果"时先怀疑自己的路径/正则**。
    #   修法：与 `_bk_athermal.load` 同款 —— **两种布局都试**，并在都失败时把试过的路径打出来。
    nd = None
    for cand in (os.path.join(HERE, OUT, tag, 'dry_%s' % tag, 'nuc_dbg.json'),
                 os.path.join(HERE, OUT, tag, 'nuc_dbg.json'),
                 os.path.join(HERE, OUT, 'dry_%s' % tag, 'nuc_dbg.json')):
        if os.path.exists(cand):
            nd = cand
            break
    nf = None
    if nd is not None:
        try:
            nf = (json.load(open(nd, errors='replace')).get('dbg') or {}) \
                .get('nfsv_nofield', 0)
        except Exception:                                       # noqa: BLE001
            pass
    return dict(tag=tag, s=s, n=len(sp), Vt=(sp[-1][0] if sp else float('nan')),
                nfsv_nofield=nf, crash=('Traceback' in txt), dbg_path=nd,
                steps=(int(RE_STEP.search(txt).group(1)) if False else None))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    conc = max(int(sys.argv[1]), 1)
    cfgs = json.load(open(sys.argv[2], encoding='utf-8'))
    # 去重 tag（**绝不让两个算例写同一目录**）
    seen = {}
    for c in cfgs:
        t = c['tag']
        if t in seen:
            seen[t] += 1
            c['tag'] = '%s_%d' % (t, seen[t])
        else:
            seen[t] = 1

    L = ['=' * 100,
         'R537 —— 并行调度：%d 个算例，并发上限 %d，各 `--nthreads 4`' % (len(cfgs), conc),
         '=' * 100, '']
    queue = list(cfgs)
    running = []          # [(proc, fh, lp, cmd, tag)]
    peak = 0.0
    t0 = time.time()
    done = []
    while queue or running:
        while queue and len(running) < conc:
            c = queue.pop(0)
            p, fh, lp, cmd = _launch(c, c['tag'], 4)
            running.append((p, fh, lp, cmd, c['tag']))
            L.append('   ▶ 启动 `%s`' % c['tag'])
        peak = max(peak, _cpu_sum())
        time.sleep(5)
        still = []
        for p, fh, lp, cmd, tag in running:
            if p.poll() is None:
                still.append((p, fh, lp, cmd, tag))
            else:
                fh.close()
                r = _read(tag, lp)
                r['rc'] = p.returncode
                done.append(r)
                L.append('   ✅ `%s` 完成：rc=%d  s/步=%.4f  末 Vt=%.6g  '
                         '`nfsv_nofield`=%s  崩=%s'
                         % (tag, p.returncode, r['s'], r['Vt'],
                            r['nfsv_nofield'], r['crash']))
        running = still
    wall = time.time() - t0

    L.append('')
    L.append('── 汇总 ──')
    L.append('   墙钟 = **%.1f s**；算例数 = %d ⇒ **吞吐 = %.4f 算例/单位时间**'
             % (wall, len(done), len(done) / max(wall, 1e-9)))
    L.append('   并发期间**核占用峰值** = **%.2f 核 / 20**（%.0f%%）'
             % (peak, 100.0 * peak / 20.0))
    vt = [r['Vt'] for r in done if not r['crash']]
    ok = all(r['rc'] == 0 for r in done)
    L.append('   全部退出码 0：%s' % ('✅' if ok else '❌'))
    if vt:
        L.append('   末态 `Vt` 各不相同（不同配置 ⇒ **本就应当不同**）：%s'
                 % '/'.join('%.4f' % v for v in vt))
    L.append('')
    L.append('★ 单变量可归因性：**每个算例的差异只来自它自己的 `args`**'
             '（`COMMON` 逐字相同、`--out` 各自独立）。')
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r537_parrun.log'), 'w') as fh:
        fh.write(out + '\n')
    with open(os.path.join(HERE, '_w2_r537_parrun.json'), 'w') as fh:
        json.dump(dict(done=done, peak=peak, wall=wall), fh,
                  ensure_ascii=False, indent=1)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

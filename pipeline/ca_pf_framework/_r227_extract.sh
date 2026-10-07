#!/bin/bash
# _r227_extract.sh —— 从 `_r210` 的日志里抽出**全部**三项量级读数，算三类面积占比。
cd "$(dirname "$0")" || exit 1
/root/miniconda3/envs/ml/bin/python - <<'PY'
import re, sys
p = '_w2_r210_saSet2_run.log'
txt = open(p, encoding='utf-8', errors='replace').read()
# 按 step 切块
blocks = re.split(r'★★ \*\*三项量级\*\*（`§135\.7`）@step (\d+)', txt)
rows = []
for i in range(1, len(blocks), 2):
    step = int(blocks[i]); body = blocks[i + 1]
    rec = {'step': step}
    for lab, key in (('F2 异变体', 'f2'), ('F3 同变体', 'f3'), ('F1 含母相', 'f1')):
        m = re.search(re.escape(lab) + r'\s+胞数\s+(\d+)\s+`\|Δed\|` 中位 \*\*([\d.eE+-]+)\*\*'
                      r'（`Δed`≡0 占 ([\d.]+)%）\s+`\|stk·κ\|` 中位 \*\*([\d.eE+-]+)\*\*'
                      r'\s+\*\*比值中位 ([\d.]+)%\*\*（99 分位 ([\d.]+)%）', body)
        if m:
            rec[key] = dict(n=int(m.group(1)), med_ed=float(m.group(2)),
                            f0=float(m.group(3)), med_sk=float(m.group(4)),
                            ratio=float(m.group(5)), p99=float(m.group(6)))
        else:
            m2 = re.search(re.escape(lab) + r'\s+胞数\s+(\d+)', body)
            rec[key] = dict(n=int(m2.group(1))) if m2 else dict(n=0)
    rows.append(rec)

print('=' * 108)
print('_r210 `saSet2DT`（**真实 R165 几何**）三类界面的胞数与比值')
print('=' * 108)
print('  %-5s | %-30s | %-30s | %s' % ('step', 'F2 异变体', 'F3 同变体', 'F1 含母相'))
print('  %-5s | %-30s | %-30s | %s' % ('', '胞数  比值中位  Δed≡0%', '胞数  比值中位  Δed≡0%',
                                      '胞数  比值中位'))
for r in rows:
    f2, f3, f1 = r.get('f2', {}), r.get('f3', {}), r.get('f1', {})
    def c(d):
        if 'ratio' in d:
            return '%6d  %8.2f%%  %5.1f%%' % (d['n'], d['ratio'], d['f0'])
        return '%6d  %s' % (d.get('n', 0), '（胞数不足）'.ljust(14))
    def c1(d):
        if 'ratio' in d:
            return '%6d  %8.3f%%' % (d['n'], d['ratio'])
        return '%6d  %s' % (d.get('n', 0), '（不足）')
    print('  %-5d | %-30s | %-30s | %s' % (r['step'], c(f2), c(f3), c1(f1)))

print()
print('=' * 108)
print('  ## ★ 三类界面**胞数占比**（≈ 面积占比；`series.csv` 原先只有 f2/f3 面积）')
print('=' * 108)
print('  %-5s %-10s %-10s %-10s  %s' % ('step', 'F1 占', 'F2 占', 'F3 占', 'F2/(F1+F2+F3)'))
for r in rows:
    n1 = r.get('f1', {}).get('n', 0)
    n2 = r.get('f2', {}).get('n', 0)
    n3 = r.get('f3', {}).get('n', 0)
    tot = n1 + n2 + n3
    if tot == 0:
        continue
    print('  %-5d %-10.2f%% %-10.2f%% %-10.2f%%  **%.2f%%**'
          % (r['step'], 100 * n1 / tot, 100 * n2 / tot, 100 * n3 / tot,
             100 * n2 / tot))
print()
print('  ⇒ **`§137.5` 的候选解释 (a) 是否成立，看最后一行。**')
PY

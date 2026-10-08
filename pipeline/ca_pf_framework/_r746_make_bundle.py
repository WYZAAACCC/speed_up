#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r746_make_bundle.py —— 把**最小可运行主仿真集**导出成一个自包含目录。

## 纪律（`R629 E1`）
**只读源目录、只写新目录。** 源目录里一个字节都不改。
每个复制件都记 SHA256 ⇒ 可核对"复制的是原件"。

## 组成（**自动推导，不手工列清单**）
1. 从入口 `_bk_exp.py` 用 `ast` 做**传递闭包**（20 个 `.py`）；
2. **C 扩展**：`_r581_ufv.c` + `_r581_ufv.so`（`windowB_surface.py:116` 按需载入）
   + `_r581_ufvc_build.txt`（构建记录）；
3. **自检脚本** `_smoke.py`（跑一个最小算例，证明"完整可运行"）；
4. **`README_BUNDLE.md`**（怎么跑、依赖什么）。

## 用法
    python3 _r746_make_bundle.py --dest /mnt/f/speed_up/winb_core
"""
import argparse
import ast
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRY = '_bk_exp.py'
CEXT = ['_r581_ufv.c', '_r581_ufv.so', '_r581_ufvc_build.txt']


def imports_of(path):
    try:
        tree = ast.parse(open(path, encoding='utf-8', errors='replace').read())
    except (OSError, SyntaxError):
        return set()
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name.split('.')[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            out.add(n.module.split('.')[0])
    return out


def closure():
    allpy = {f[:-3] for f in os.listdir(HERE) if f.endswith('.py')}
    seen, stack = set(), [ENTRY[:-3]]
    while stack:
        m = stack.pop()
        if m in seen or m not in allpy:
            continue
        seen.add(m)
        stack += list(imports_of(os.path.join(HERE, m + '.py')))
    return sorted(seen)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


SMOKE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_smoke.py —— 最小冒烟：证明这个包**能完整跑起来**（不依赖源目录）。

跑一个小算例（N=32、20 步、单变体），检查：
  1) 引擎能构造；2) 能推进 20 步；3) 落盘 `series.csv` / `meta.json`；
  4) **没有** `JIT compile failed` / `ImportError` / `FileNotFoundError`。
⚠ 参数极小 ⇒ 只证明"能跑通"，**不用于任何物理结论**。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '_smoke_out')
PY = sys.executable

cmd = [PY, '-u', os.path.join(HERE, '_bk_exp.py'),
       '--N', '32', '--dx-nm', '62.5', '--steps', '20',
       '--every', '10', '--snap-every', '20', '--pair-every', '20',
       '--norm-smooth', '0', '--nthreads', '2', '--arm', 'dry',
       '--laths', '1', '--nuc-init', '0', '--nuc-every', '0',
       '--plate-L', '2000.0', '--plate-W', '2000.0', '--plate-T', '2000.0',
       '--facet-proj', '0', '--band-cells', '20',
       '--out', OUT, '--tag', 'smoke']

print('CMD: %s' % ' '.join(cmd))
os.makedirs(OUT, exist_ok=True)
log = os.path.join(OUT, 'smoke.log')
with open(log, 'w') as fh:
    rc = subprocess.call(cmd, cwd=HERE, stdout=fh, stderr=subprocess.STDOUT)
print('rc = %d   （日志 %s）' % (rc, log))

bad = ('JIT compile failed', 'ImportError', 'ModuleNotFoundError',
       'FileNotFoundError', 'Traceback')
txt = open(log, encoding='utf-8', errors='replace').read()
hits = [b for b in bad if b in txt]
print()
print('  `series.csv` 存在？ %s'
      % os.path.isfile(os.path.join(OUT, 'dry_smoke', 'series.csv')))
print('  `meta.json`  存在？ %s'
      % os.path.isfile(os.path.join(OUT, 'dry_smoke', 'meta.json')))
print('  可疑串： %s' % (hits if hits else '（无）'))
print()
ok = (rc == 0 and not hits
      and os.path.isfile(os.path.join(OUT, 'dry_smoke', 'series.csv')))
print('⇒ **%s**' % ('✅ 包可完整运行' if ok else '⛔ 有问题，见日志'))
sys.exit(0 if ok else 1)
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dest', default='/mnt/f/speed_up/winb_core')
    a = ap.parse_args()
    mods = closure()
    os.makedirs(a.dest, exist_ok=True)
    rows = []
    for m in mods:
        src = os.path.join(HERE, m + '.py')
        dst = os.path.join(a.dest, m + '.py')
        shutil.copy2(src, dst)
        rows.append((m + '.py', len(open(src, 'rb').read()), sha(dst)))
    for c in CEXT:
        src = os.path.join(HERE, c)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(a.dest, c))
            rows.append((c, os.path.getsize(src), sha(os.path.join(a.dest, c))))
        else:
            rows.append((c, 0, '⛔源缺'))
    open(os.path.join(a.dest, '_smoke.py'), 'w').write(SMOKE)

    # 清单（可核对）
    with open(os.path.join(a.dest, 'MANIFEST.sha256'), 'w') as f:
        for n, sz, h in sorted(rows):
            f.write('%s  %s  %d\n' % (h, n, sz))

    readme = os.path.join(a.dest, 'README_BUNDLE.md')
    with open(readme, 'w') as f:
        f.write('# Window B 最小可运行主仿真集\n\n')
        f.write('由 `pipeline/ca_pf_framework/_r746_make_bundle.py` 导出。\n')
        f.write('**源目录未被修改**（只读）；每个文件的 SHA256 见 `MANIFEST.sha256`。\n\n')
        f.write('## 内容（%d 个 .py + %d 个 C 扩展件）\n\n'
                % (len(mods), sum(1 for c in CEXT
                                  if os.path.isfile(os.path.join(HERE, c)))))
        f.write('| 文件 | 字节 | sha256[:12] |\n|---|---:|---|\n')
        for n, sz, h in sorted(rows):
            f.write('| `%s` | %d | `%s` |\n' % (n, sz, h[:12]))
        f.write('\n## 怎么跑\n\n```bash\n'
                'PY=/root/miniconda3/envs/ml/bin/python\n'
                'cd %s\n'
                '$PY _smoke.py                       # 先证明能跑通\n'
                '$PY -u _bk_exp.py --help            # 全部参数\n```\n\n' % a.dest)
        f.write('## 依赖\n\n')
        f.write('* Python 3.12 + numpy（本机用 `/root/miniconda3/envs/ml/bin/python`）\n')
        f.write('* `_r581_ufv.so`（可选 C 融合核；`windowB_surface.py:116` 按需载入）\n')
        f.write('* **无外部数据文件依赖**（已实测：唯一的读依赖是同一目录内的 '
                '`WINDOWB_VARIANTS.txt`，而那两行在 `main()` 内、`import` 不执行）\n')
        f.write('\n⚠ 本包**只含主仿真**；`_exp/` 归档、问题台账、审计脚本等**不在包内**。\n')

    print('=' * 80)
    print('已导出 → %s' % a.dest)
    print('=' * 80)
    tot = 0
    for n, sz, h in sorted(rows):
        tot += sz
        print('  %-30s %8d  %s' % (n, sz, h[:12]))
    print('  ' + '-' * 56)
    print('  %-30s %8d 字节' % ('合计 (%d 件)' % len(rows), tot))
    print('  + _smoke.py, MANIFEST.sha256, README_BUNDLE.md')
    print()
    print('  源目录改动 = 0（只读）')
    return 0


if __name__ == '__main__':
    sys.exit(main())

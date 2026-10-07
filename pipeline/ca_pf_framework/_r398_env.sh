#!/usr/bin/env bash
# _r398_env.sh -- 绘图环境盘点
PY=/root/miniconda3/envs/ml/bin/python
$PY - <<'PY'
import importlib, sys
mods = ['numpy', 'matplotlib', 'scipy', 'skimage', 'pyvista', 'mayavi',
        'vtk', 'plotly', 'PIL', 'imageio']
for m in mods:
    try:
        mod = importlib.import_module(m)
        print('  %-12s %s' % (m, getattr(mod, '__version__', 'ok')))
    except Exception as e:
        print('  %-12s ❌ %s' % (m, type(e).__name__))
print('python', sys.version.split()[0])
PY
echo
echo "=== 中文字体 ==="
fc-list 2>/dev/null | grep -iE 'cjk|noto.*sc|wqy|simhei|simsun|source han' | head -6
echo "(fc-list 条数: $(fc-list 2>/dev/null | wc -l))"
echo
echo "=== matplotlib 自带字体里的 CJK ==="
/root/miniconda3/envs/ml/bin/python - <<'PY'
import matplotlib.font_manager as fm
names = sorted({f.name for f in fm.fontManager.ttflist})
cjk = [n for n in names if any(k in n.lower() for k in
       ('cjk', 'han', 'hei', 'song', 'kai', 'ming', 'yahei', 'noto sans sc'))]
print('  找到 CJK 候选:', cjk if cjk else '（无）')
print('  字体总数:', len(names))
PY

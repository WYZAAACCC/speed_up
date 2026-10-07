#!/bin/bash
# 查 WSL 里有没有 PDF 文本提取库（决定"PDF 文献"这条路通不通）
for e in ml base; do
  P="/root/miniconda3/envs/$e/bin/python"
  echo "== env $e =="
  if [ -x "$P" ]; then
    "$P" - <<'PY'
import importlib
for m in ('pypdf', 'PyPDF2', 'pdfminer', 'fitz', 'pdfplumber'):
    try:
        importlib.import_module(m)
        print('  OK  ', m)
    except Exception:
        print('  --  ', m)
PY
  else
    echo "  (缺 $P)"
  fi
done
echo "== 系统 python3 =="
python3 -c "
import importlib
for m in ('pypdf','fitz','pdfminer'):
    try:
        importlib.import_module(m); print('  OK  ', m)
    except Exception: print('  --  ', m)
" 2>/dev/null || echo "  (无 python3 或失败)"

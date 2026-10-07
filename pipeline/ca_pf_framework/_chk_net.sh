#!/bin/bash
# 关掉代理后，WSL 能否直连下载网页/PDF？—— 决定"PDF 文献"这条路是否通
cd /tmp
echo "== 1) HTTP 头（arxiv 首页）=="
curl -sS -m 20 -o /dev/null -w '  http_code=%{http_code} time=%{time_total}s\n' https://arxiv.org/ || echo "  失败"
echo "== 2) 下载 PDF（arxiv 2404.09806）=="
curl -sS -m 60 -o t.pdf -w '  http_code=%{http_code} bytes=%{size_download}\n' https://arxiv.org/pdf/2404.09806 || echo "  失败"
ls -la t.pdf 2>/dev/null
echo "== 3) 用 pypdf 抽文本（前 3 行）=="
/root/miniconda3/envs/ml/bin/python - <<'PY'
try:
    from pypdf import PdfReader
    r = PdfReader('/tmp/t.pdf')
    print('  pages =', len(r.pages))
    t = r.pages[0].extract_text() or ''
    for ln in [x for x in t.splitlines() if x.strip()][:3]:
        print('  |', ln[:100])
except Exception as e:
    print('  抽取失败:', type(e).__name__, e)
PY

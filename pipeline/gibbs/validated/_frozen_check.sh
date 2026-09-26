#!/bin/bash
cd /mnt/f/speed_up/pipeline/frozen
echo "=== SHA256SUMS 内容 ==="
cat SHA256SUMS
echo
echo "=== 逐项校验（-c 会自己报 OK/FAILED）==="
sha256sum -c SHA256SUMS 2>&1 | head -20
echo
echo "=== 返回码 ==="
sha256sum -c SHA256SUMS >/dev/null 2>&1 && echo "全部通过 ✓（生产链的冻结门禁完好）" || echo "有失败 ✗"
#!/bin/bash
# _r186_early.sh —— 惰性复现的**早期信号**：只比 step 0（初态）。
# 初态由播种（几何+种子）决定，与演化无关 ⇒ **step 0 不同就说明播种路径变了**，
# 那时不必等 120 步跑完。（硬规则：**先拿早期证据，别干等**。）
cd "$(dirname "$0")" || exit 1
A=_exp/_bk_mb/dry_saSet2/series.csv
B=_exp/_bk_mb/dry_saSet2INERT/series.csv
mkdir -p /tmp/r186
head -1 "$A" > /tmp/r186/ha; head -1 "$B" > /tmp/r186/hb
echo "=== 表头是否逐字节相同 ==="
if cmp -s /tmp/r186/ha /tmp/r186/hb; then echo "  ✅ 表头相同"; else
  echo "  ❌ 表头不同："; diff /tmp/r186/ha /tmp/r186/hb | head -10; fi
grep -m1 '^0,' "$A" > /tmp/r186/r0a
grep -m1 '^0,' "$B" > /tmp/r186/r0b
echo
echo "=== step 0 行 ==="
if cmp -s /tmp/r186/r0a /tmp/r186/r0b; then
  echo "  ✅ **step 0 逐字节相同**（播种路径未变）"
else
  echo "  ❌ step 0 不同 ⇒ **播种路径变了** ⇒ R165 的对照有混杂"
  echo "  --- 逐字段差异（只列不同的）---"
  /root/miniconda3/envs/ml/bin/python - <<'PY'
a = open('/tmp/r186/r0a').read().strip().split(',')
b = open('/tmp/r186/r0b').read().strip().split(',')
h = open('/tmp/r186/ha').read().strip().split(',')
n = 0
for i, (x, y) in enumerate(zip(a, b)):
    if x != y:
        n += 1
        if n <= 40:
            print('     %-22s 归档=%-24s 新=%-24s' %
                  (h[i] if i < len(h) else '?', x[:24], y[:24]))
print('     ⇒ 不同字段数 = %d / %d' % (n, len(a)))
PY
fi
echo
echo "=== 新跑已写到第几行 ==="
wc -l "$B" 2>/dev/null

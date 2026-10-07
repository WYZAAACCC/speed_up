#!/usr/bin/env python3
"""R67: 把 BLOCK_SELFAC.md 里**被 heredoc 截断的 §8** 修好。

## 为什么要这个脚本
上一次用 `cat >> ... <<'EOF'` 追加，**shell 把反引号当命令替换吃掉了**，
而且 heredoc 被截断 ⇒ 文件停在半句话（"⇒ **"）。
⇒ 规程（又一次）：**写文档不要用 shell heredoc**，用 `write` 工具写文件 +
用 Python 拼接（`AGENTS.md §3.9` 的同源教训）。
"""
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
MAIN = 'BLOCK_SELFAC.md'
SEC = '_r67_facet_sec.md'
KEEP = 776                      # §8 之前原有的行数（追加前 wc -l 的值）

lines = open(MAIN, encoding='utf-8').read().split('\n')
print('当前 %d 行' % len(lines))
# 1) 截断回 KEEP 行（去掉被写坏的 §8）
if len(lines) > KEEP:
    head = lines[:KEEP]
    print('截断 %d → %d 行' % (len(lines), len(head)))
else:
    head = lines
# 2) 接上正确的 §8
sec = open(SEC, encoding='utf-8').read()
out = '\n'.join(head).rstrip('\n') + '\n' + sec
open(MAIN, 'w', encoding='utf-8').write(out)
lines2 = open(MAIN, encoding='utf-8').read().split('\n')
print('写入后 %d 行' % len(lines2))
print('末 6 行：')
for x in lines2[-6:]:
    print('   ', x[:100])
# 3) 检查坏痕迹
bad = [i + 1 for i, x in enumerate(lines2)
       if x.strip().endswith('⇒ **') or 'here-document' in x]
print('可疑截断行: %s' % (bad if bad else '无 ✅'))

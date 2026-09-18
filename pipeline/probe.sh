#!/bin/bash
# 探针：当前在跑什么？修复版训练跑过没有？

echo "===== 全部相关进程 ====="
ps -eo pid,etime,pcpu,rss,args --sort=-pcpu | grep -E 'phase_field-opt|python3|mpirun' | grep -v grep | head -30

echo
echo "===== python 进程明细 ====="
pgrep -af python3 || echo "  （无 python3 在跑）"

echo
echo "===== 模型文件 tb.pt / op_batch.pt ====="
ls -la /root/work/tb.pt /root/work/op_batch.pt /root/work/*.pt 2>/dev/null

echo
echo "===== 是否有 batched 训练的日志 ====="
ls -la /root/work/*batch* /root/work/*roll* 2>/dev/null

echo
echo "===== 最近的 shell 历史（最后 40 条）====="
tail -40 /root/.bash_history 2>/dev/null || echo "  （无历史）"

echo
echo "===== ds_full 里 op_roll2.pt 的内容摘要 ====="
source /root/miniconda3/etc/profile.d/conda.sh
conda activate ml 2>/dev/null
python3 - <<'PY'
import torch, glob, os
for f in sorted(glob.glob('/root/work/ds_full/*.pt')) + ['/root/work/tb.pt']:
    if not os.path.exists(f):
        print(f"  {f}: 不存在"); continue
    try:
        ck = torch.load(f, map_location='cpu', weights_only=False)
        keys = list(ck.keys()) if isinstance(ck, dict) else 'not-dict'
        extra = ''
        if isinstance(ck, dict) and 'sd' in ck:
            sd = ck['sd']
            extra = f" sd_min={float(min(sd)):.3g} sd_max={float(max(sd)):.3g}"
        n = sum(v.numel() for v in ck['state'].values()) if isinstance(ck, dict) and 'state' in ck else '?'
        print(f"  {os.path.basename(f)}: keys={keys} 参数量={n}{extra}")
    except Exception as e:
        print(f"  {f}: 读取失败 {e}")
PY

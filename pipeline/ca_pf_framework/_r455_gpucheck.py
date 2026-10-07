#!/usr/bin/env python3
"""_r455_gpucheck.py —— 环境侧：有没有 GPU 库、GPU 是不是真的闲着。"""
import importlib
import shutil
import subprocess

P = print
P('=' * 84)
P('_r455 —— GPU 环境核查')
P('=' * 84)

P('\n[1] Python 库')
for m in ('cupy', 'torch', 'numba', 'pycuda', 'jax', 'scipy', 'numpy'):
    try:
        mod = importlib.import_module(m)
        P('    %-8s ✅  ver=%s' % (m, getattr(mod, '__version__', '?')))
    except Exception as e:
        P('    %-8s ❌  %s' % (m, type(e).__name__))

P('\n[2] torch 能不能看见 GPU')
try:
    import torch
    P('    cuda.is_available() = %s' % torch.cuda.is_available())
    if torch.cuda.is_available():
        P('    设备数 = %d；名称 = %s' % (torch.cuda.device_count(),
                                          torch.cuda.get_device_name(0)))
        free, tot = torch.cuda.mem_get_info()
        P('    显存：空闲 %.2f GB / 共 %.2f GB' % (free / 2**30, tot / 2**30))
    else:
        P('    ⇒ **torch 看不到 GPU**（可能是 CPU-only 版，或驱动/WSL 直通没配好）')
except Exception as e:
    P('    torch 检查失败：%r' % e)

P('\n[3] nvidia-smi')
if shutil.which('nvidia-smi'):
    try:
        out = subprocess.run(['nvidia-smi',
                              '--query-gpu=name,memory.total,memory.used,utilization.gpu',
                              '--format=csv,noheader'],
                             capture_output=True, text=True, timeout=20).stdout.strip()
        P('    %s' % out)
    except Exception as e:
        P('    调用失败：%r' % e)
else:
    P('    ✗ WSL 里没有 nvidia-smi')

P('\n[4] 当前引擎用的 FFT 后端')
import inspect
import windowB_surface as W
src = inspect.getsource(W)
for kw in ('sfft', 'scipy.fft', 'np.fft', 'cupy', 'torch'):
    P('    `%s` 在 `windowB_surface.py` 里出现 **%d** 次'
      % (kw, src.count(kw)))
P('=' * 84)

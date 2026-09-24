# -*- coding: utf-8 -*-
import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/_v1_worker.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("""    return dict(pred='r/ℓ = 1/Σ（与理想律的最大偏离 <=1.2 胞）',
                n=len(rows), slope=float(A[0]), intercept=float(A[1]), r2=float(ss),""",
"""    return dict(pred='r/ℓ = 1/Σ（与理想律的最大偏离 <=1.2 胞）',
                rows=[[round(a, 5), round(b, 5), round(e, 2)] for a, b, e in rows],
                n=len(rows), slope=float(A[0]), intercept=float(A[1]), r2=float(ss),""")
io.open(P, "w", encoding="utf-8").write(s)
print("t3 现在保存原始测点")
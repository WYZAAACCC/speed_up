import io
H = "/mnt/f/speed_up/pipeline/ca_pf_framework"
src = io.open(H + "/demo_meltpool_growth.py", encoding="utf-8").read()
# 归一化：先还原成 dx=3um 的标准版
std = src.replace("DX = 1.5e-6", "DX = 3.0e-6")
std = std.replace("NX, NY, NZ = 134, 200, 134          # 201 x 300 x 201 um（同尺寸，dx 减半）",
                  "NX, NY, NZ = 67, 100, 67            # 201 x 300 x 201 um")
std = std.replace("meltpool_growth_fine.npz", "meltpool_growth_gid.npz")
std = std.replace("FIG_meltpool_growth_process_fine.png", "FIG_meltpool_growth_process.png")
io.open(H + "/demo_meltpool_growth.py", "w", encoding="utf-8").write(std)
# 细网格版
fine = std.replace("DX = 3.0e-6", "DX = 1.5e-6")
fine = fine.replace("NX, NY, NZ = 67, 100, 67            # 201 x 300 x 201 um",
                    "NX, NY, NZ = 134, 200, 134          # 201 x 300 x 201 um, dx=1.5um")
fine = fine.replace("meltpool_growth_gid.npz", "meltpool_growth_fine.npz")
fine = fine.replace("FIG_meltpool_growth_process.png", "FIG_meltpool_growth_process_fine.png")
io.open(H + "/demo_meltpool_fine.py", "w", encoding="utf-8").write(fine)
print("std DX:", [l for l in std.splitlines() if l.startswith("DX")][0])
print("std NX:", [l for l in std.splitlines() if l.startswith("NX")][0])
print("fine DX:", [l for l in fine.splitlines() if l.startswith("DX")][0])
print("fine NX:", [l for l in fine.splitlines() if l.startswith("NX")][0])
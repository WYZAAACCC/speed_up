import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/demo_meltpool_growth.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("DX = 3.0e-6\nNX, NY, NZ = 67, 100, 67            # 201 x 300 x 201 um",
              "DX = 1.5e-6\nNX, NY, NZ = 134, 200, 134          # 201 x 300 x 201 um（同尺寸，dx 减半）", 1)
s = s.replace('"meltpool_growth_gid.npz"', '"meltpool_growth_fine.npz"')
s = s.replace('"FIG_meltpool_growth_process.png"', '"FIG_meltpool_growth_process_fine.png"')
io.open(P, "w", encoding="utf-8").write(s.replace("demo_meltpool_growth", "demo_meltpool_fine"))
print("made demo_meltpool_fine.py (dx=1.5um)")
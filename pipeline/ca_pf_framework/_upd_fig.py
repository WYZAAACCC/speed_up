import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/fig_pool_grains_3d_v2.py"
s = io.open(P, encoding="utf-8").read()
old = '''def main():
    d = np.load(os.path.join(HERE, "meltpool_growth_gid.npz"))'''
new = '''def main():
    npz = sys.argv[1] if len(sys.argv) > 1 else "meltpool_growth_gid.npz"
    outp = sys.argv[2] if len(sys.argv) > 2 else "FIG_pool_grains_3d_v2.png"
    d = np.load(npz if os.path.isabs(npz) else os.path.join(HERE, npz))'''
if old not in s: print("!! 1"); raise SystemExit(1)
s = s.replace(old, new)
s = s.replace('''    p = os.path.join(HERE, "FIG_pool_grains_3d_v2.png")''',
              '''    p = outp if os.path.isabs(outp) else os.path.join(HERE, outp)''')
s = s.replace("import os\nimport numpy as np", "import os\nimport sys\nimport numpy as np")
io.open(P, "w", encoding="utf-8").write(s)
print("fig 脚本支持 npz/png 参数")
import numpy as np
d = np.load("/mnt/f/speed_up/pipeline/ca_pf_framework/meltpool_growth_gid.npz")
s0 = d["snaps"][0]; pool = (s0 == 0); g = d["gid"].astype(np.int32)
pc = pool.sum(axis=(0,1))
print("z 平面上的池胞数 (z=0..%d):" % (len(pc)-1))
print(" ".join("%d:%d" % (z, c) for z, c in enumerate(pc) if c > 0))
print("非零 z 范围:", np.nonzero(pc)[0][[0,-1]], " 峰值 z =", int(pc.argmax()))
xc = pool.sum(axis=(1,2)); yc = pool.sum(axis=(0,2))
print("x 范围:", np.nonzero(xc)[0][[0,-1]], " y 范围:", np.nonzero(yc)[0][[0,-1]])
# 池顶部（最高 z 层）的形状
zt = np.nonzero(pc)[0][-1]
print("最顶层 z=%d: 池胞 %d, 其 x 范围 %s y 范围 %s" % (zt, int(pool[:,:,zt].sum()),
      np.nonzero(pool[:,:,zt].any(1))[0][[0,-1]], np.nonzero(pool[:,:,zt].any(0))[0][[0,-1]]))
# 每一层 z 的 (x,y) 矩形范围
for z in range(40, 67, 3):
    m = pool[:,:,z]
    if m.any():
        print("  z=%2d: 胞 %5d, x %2d..%2d, y %2d..%2d" % (z, m.sum(),
              np.nonzero(m.any(1))[0][0], np.nonzero(m.any(1))[0][-1],
              np.nonzero(m.any(0))[0][0], np.nonzero(m.any(0))[0][-1]))
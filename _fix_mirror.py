import io
P = "/mnt/f/speed_up/_mine_mirror.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("""VECS = np.loadtxt(D + '/GrainOrientationVectors.csv', delimiter=',', skiprows=1)
VECS /= np.linalg.norm(VECS, axis=1)[:, None]
print('取向表: %d 条' % len(VECS))""",
"""VECS = np.loadtxt(D + '/GrainOrientationVectors.csv', delimiter=',', skiprows=1)
VECS = VECS.reshape(-1, 3, 3)          # 每行 9 个数 = 3 个晶轴（完整取向基）
print('取向表: %d 条取向（每条 3 个正交单位向量）' % len(VECS))""")
# 用 P 直接构造四元数（不用再从向量正交化）
s = s.replace("""        v = VECS[rng.integers(len(VECS))]
        seed_gids.append(ca.add_grain(i, j, 0, quat=q_from_v(v)))""",
"""        Pp = VECS[rng.integers(len(VECS))]
        seed_gids.append(ca.add_grain(i, j, 0, quat=quat_from_P(Pp)))""")
s = s.replace("""                g = ca.add_grain(nn[0], nn[1], nn[2], quat=q_from_v(VECS[rng.integers(len(VECS))]))""",
"""                Pp = VECS[rng.integers(len(VECS))]
                g = ca.add_grain(nn[0], nn[1], nn[2], quat=quat_from_P(Pp))""")
# 把 q_from_v 换成 quat_from_P（接受 3x3，列=晶轴）
s = s.replace("def q_from_v(v):", "def quat_from_P(P):")
s = s.replace("""    a1 = v / np.linalg.norm(v)
    tmp = np.array([0.0, 0.0, 1.0]) if abs(a1[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    a2 = np.cross(a1, tmp); a2 /= np.linalg.norm(a2); a3 = np.cross(a1, a2)
    P = np.column_stack([a1, a2, a3])
    tr""", """    P = P / np.linalg.norm(P[:, 0]) if P.shape == (3, 3) else P
    tr""")
io.open(P, "w", encoding="utf-8").write(s)
print('patched')
import io, sys
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py'
s = io.open(P, encoding='utf-8').read()
# 1) 新增开关
old = "        self.lg_percentile = float(lg_percentile)   # l_g 驱动量取前沿 V 的该分位（规划 D1）"
new = ("        self.lg_percentile = float(lg_percentile)   # l_g 驱动量取前沿 V 的该分位（规划 D1）\n"
       "        # capture=\"cell\" 的裁决规则：\"ratio\"（取 ℓ/crit 最大，与顺序无关；本框架默认）\n"
       "        #                          \"firstcome\"（ExaCA 口径：按源胞索引+偏移顺序先到先得）\n"
       "        self.cell_tiebreak = \"ratio\"")
if old not in s: print('!! 1'); sys.exit(1)
s = s.replace(old, new, 1)

# 2) 分支里按开关切换
old = """                    bf = best.reshape(-1)
                    sf = bsrc.reshape(-1)
                    bgid = np.full(gid.size, 1 << 30, np.int32)
                    for o, _ in OFFSETS:"""
new = """                    bf = best.reshape(-1)
                    sf = bsrc.reshape(-1)
                    bgid = np.full(gid.size, 1 << 30, np.int32)
                    for oi, (o, _) in enumerate(OFFSETS):"""
if old not in s: print('!! 2'); sys.exit(1)
s = s.replace(old, new, 1)

old = """                        ratio = LL2 / np.maximum(crit2, 1e-30)
                        fidx = (cx * self.ny + cy) * self.nz + cz
                        prev = bf[fidx]; prevg = bgid[fidx]
                        upd = (ratio > prev) | ((ratio == prev) & (gg2 < prevg))
                        bf[fidx[upd]] = ratio[upd]
                        sf[fidx[upd]] = sfl2[upd]
                        bgid[fidx[upd]] = gg2[upd]"""
new = """                        fidx = (cx * self.ny + cy) * self.nz + cz
                        if self.cell_tiebreak == "firstcome":
                            # ExaCA 口径：key = 源胞索引*26 + 偏移序号，取最小（= 先到先得）
                            key = sfl2.astype(np.float64) * 26.0 + oi
                            upd = key < bf[fidx]
                            bf[fidx[upd]] = key[upd]
                            sf[fidx[upd]] = sfl2[upd]
                        else:
                            ratio = LL2 / np.maximum(crit2, 1e-30)
                            prev = bf[fidx]; prevg = bgid[fidx]
                            upd = (ratio > prev) | ((ratio == prev) & (gg2 < prevg))
                            bf[fidx[upd]] = ratio[upd]
                            sf[fidx[upd]] = sfl2[upd]
                            bgid[fidx[upd]] = gg2[upd]"""
if old not in s: print('!! 3'); sys.exit(1)
s = s.replace(old, new, 1)
io.open(P, 'w', encoding='utf-8').write(s)
print('已加 cell_tiebreak 开关; 行数 =', s.count(chr(10)) + 1)
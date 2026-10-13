# rt_pxrt_e_extra

## Findings

**pxrt_e_extra.lua:17-19** - high - CWormParams.SetPosition has wrong parameter signature. The native method accepts (self, super, x, y) but transpiled code calls it with (self, Health, x, y, flag). This causes Health to be stored as PosX and x to be stored as PosY, while the actual y coordinate and flag are ignored. - Change signature to `function(self, super, Health, x, y, flag)` and store x/y (not Health/x): `rawset(self, "PosX", tf(x)); rawset(self, "PosY", tf(y))`. The Health and flag parameters appear to be used for actual worm spawning in real PX but are not needed for the stub struct.

**pxrt_e_extra.lua:25** - med - IsInBox uses inclusive boundary checks (>= and <=) but PX semantics require exclusive checks (> and <). A position exactly on left/top/right/bottom should return false, not true. The transpiled utils.lua:300-301 overrides this with correct exclusive comparisons, masking the bug for packages that include utils, but the native implementation is still wrong. - Change to: `return (x > tf(l) and x < tf(r) and y > tf(t) and y < tf(b)) and 1 or 0`

## Notes

All three bag classes (CLightSource, CRespawnState, CRespawnTeam) rely on scriptMTFor's __index returning 0 for unknown fields, which is correct. Native methods are only called through mc() wrapper which handles nil objects safely (logs once and returns 0), so no nil-index crashes despite methods not checking self. No per-frame allocations or hot-path waste detected.

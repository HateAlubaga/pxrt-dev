p = 'C:/Users/Admin/Projects/worms-modding-lab/sources/wkJellyWorm/src/Weapons.cpp'
s = open(p, encoding='utf-8').read()
BS = chr(92)

old_inc = '#include "entities/gametasks/CTaskMissile.h"\n'
new_inc = old_inc + '#include "MemAccess.h"\n#include "PxWeaponArt.h"\n#include <unordered_map>\n'
assert old_inc in s
s = s.replace(old_inc, new_inc, 1)

old = '''	int ret = PackageManager::getInstance().handleFireWeapon(worm, weaponstruct, launchparams);
	if(ret) return ret;
'''
new = '''	logFiredWeapon(weaponstruct);
	int ret = PackageManager::getInstance().handleFireWeapon(worm, weaponstruct, launchparams);
	if(ret) return ret;
'''
assert old in s
s = s.replace(old, new, 1)

old = '''	int ret = PackageManager::getInstance().handleCreateWeaponProjectile(This, projectileParams, launchParams);
	if(ret) return 0;
	return origCreateWeaponProjectile(This, EDX, projectileParams, launchParams);
}
'''
new = '''	int ret = PackageManager::getInstance().handleCreateWeaponProjectile(This, projectileParams, launchParams);
	if(ret) return 0;
	CTaskMissile *missile = origCreateWeaponProjectile(This, EDX, projectileParams, launchParams);
	logCreatedProjectile(projectileParams, missile);
	return missile;
}

// ---------------------------------------------------------------------------
// Projectile sprite diagnostics (jelly@@pxweapons.log).
//
// Custom weapons whose projectile slot holds a custom sprite id (851+) fire
// fine but nothing is drawn, while the same ids work as worm aim poses. The
// static path (WeaponStruct+0x60 -> missile+0x2EC -> render 0x5091A0 ->
// display vtable+0x4C) says they should draw, so log what the game actually
// holds at each step. Capped so a long match cannot grow the log unbounded.
// ---------------------------------------------------------------------------
static int projectileDiagLines = 0;
static const int kProjectileDiagMax = 400;

static DWORD readDword(DWORD addr) {
	if(!addr || !jellyProbeRead(addr, sizeof(DWORD)))
		return 0xDEADDEAD;
	return *(DWORD *)addr;
}

// Sprite table entry for `sprite` (flags stripped): object pointer and its
// frame count; spr=0 and alt=0 means WA has nothing to draw for that id.
static void describeSprite(DWORD sprite, char *out, size_t outSize) {
	DWORD id = sprite & 0xFFFF;
	DWORD display = Game::getAddrDdDisplay();
	if(!display || id < 1 || id > 0x3FF) {
		sprintf_s(out, outSize, "id=%u (outside sprite table)", id);
		return;
	}
	DWORD primary = readDword(display + 0x1008 + id * 4);
	DWORD alternate = readDword(display + 0x2008 + id * 4);
	WORD frames = 0;
	if(primary && primary != 0xDEADDEAD && jellyProbeRead(primary + 0x16, sizeof(WORD)))
		frames = *(WORD *)(primary + 0x16);
	sprintf_s(out, outSize, "id=%u flags=0x%X spr=0x%X alt=0x%X frames=%u", id, sprite & 0xFFFF0000, primary, alternate, frames);
}

void Weapons::logFiredWeapon(CustomWeapons::WeaponStruct *ws) {
	if(!ws || projectileDiagLines >= kProjectileDiagMax || !jellyProbeRead((DWORD)ws, sizeof(CustomWeapons::WeaponStruct)))
		return;
	const int *f = reinterpret_cast<const int *>(ws);
	const char *name = (ws->name1 && jellyProbeRead((DWORD)ws->name1, 1)) ? ws->name1 : "?";
	char spr[160];
	describeSprite((DWORD)f[0x60 / 4], spr, sizeof(spr));
	projectileDiagLines++;
	PxWeaponArt::log("fire '%s' ws=0x%X type=%d/%d/%d/%d 5C=%d 60=%d 64=%d A4=%d AC=%d 124=%d 128=%d 170=%d | %s@@n",
		name, (DWORD)ws, f[0x30 / 4], f[0x34 / 4], f[0x38 / 4], f[0x3C / 4], f[0x5C / 4], f[0x60 / 4], f[0x64 / 4],
		f[0xA4 / 4], f[0xAC / 4], f[0x124 / 4], f[0x128 / 4], f[0x170 / 4], spr);
}

void Weapons::logCreatedProjectile(WeaponProjectileParams *params, CTaskMissile *missile) {
	if(projectileDiagLines >= kProjectileDiagMax)
		return;
	projectileDiagLines++;
	DWORD m = (DWORD)missile;
	DWORD p = (DWORD)params;
	PxWeaponArt::log("  projectile params=0x%X [+0C]=%d [+20]=%d [+24]=%d [+28]=%d -> missile=0x%X +2E8=%d +2EC=%d +2F0=%d +330=%d +338=%d@@n",
		p, (int)readDword(p + 0x0C), (int)readDword(p + 0x20), (int)readDword(p + 0x24), (int)readDword(p + 0x28),
		m, (int)readDword(m + 0x2E8), (int)readDword(m + 0x2EC), (int)readDword(m + 0x2F0), (int)readDword(m + 0x330), (int)readDword(m + 0x338));
}

// WA's missile draw (0x5091A0): __stdcall, one argument (the missile), no
// register inputs. Logs the first two draws of each missile, then passes on.
static void (__stdcall *origMissileRender)(DWORD missile);
static std::unordered_map<DWORD, int> missileRenderSeen;
static void __stdcall hookMissileRender(DWORD m) {
	if(projectileDiagLines < kProjectileDiagMax && m && jellyProbeRead(m, 0x3F0)) {
		if(missileRenderSeen.size() > 4096)
			missileRenderSeen.clear();
		int &seen = missileRenderSeen[m];
		if(seen < 2) {
			seen++;
			projectileDiagLines++;
			bool alt = readDword(m + 0x100) != 0;
			DWORD block = m + (alt ? 0x334 : 0x2E8);
			DWORD sprite = readDword(block + 4);
			DWORD spriteOverride = readDword(m + 0x3A4) ? readDword(m + 0x368) : 0;
			char spr[160];
			describeSprite(spriteOverride ? spriteOverride : sprite, spr, sizeof(spr));
			PxWeaponArt::log("  draw missile=0x%X block=+%X sprite=%d mode=%d +330=%d +3A4=%d +368=%d +3E8=0x%X +B0=%d +A4=%d pos=%d,%d | %s@@n",
				m, alt ? 0x334 : 0x2E8, (int)sprite, (int)readDword(block + 8), (int)readDword(m + 0x330),
				(int)readDword(m + 0x3A4), (int)readDword(m + 0x368), readDword(m + 0x3E8), (int)readDword(m + 0xB0),
				(int)readDword(m + 0xA4), (int)readDword(m + 0x84) >> 16, (int)readDword(m + 0x88) >> 16, spr);
		}
	}
	origMissileRender(m);
}
'''
assert old in s
s = s.replace(old, new.replace('@@', BS + BS if False else BS), 1)

old = '''	Hooks::polyhook("CreateWeaponProjectile", addrCreateWeaponProjectile, (DWORD *) &hookCreateWeaponProjectile, (DWORD *) &origCreateWeaponProjectile);
'''
pat = ''.join(BS + 'x%02X' % b for b in bytes.fromhex('83ec20538b5c242883bb00010000008b83c8030000555657894424208db3e8020000'))
mask = '??????' + 'x' * (34 - 6)
new = old + '''	DWORD addrMissileRender = Hooks::scanPattern("MissileRender", "%s", "%s", 0x5091A0);
	Hooks::polyhook("MissileRender", addrMissileRender, (DWORD *) &hookMissileRender, (DWORD *) &origMissileRender);
''' % (pat, mask)
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)
print('ok')

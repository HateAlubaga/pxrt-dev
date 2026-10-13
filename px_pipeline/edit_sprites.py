import os
os.chdir(r'C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm\src')
s = ''
def rep(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

p = 'Sprites.h'
s = open(p, encoding='utf-8').read()
rep("""		std::string file;           // resolved image path
		Sprites *sprite = nullptr;  // loaded per game, owned by no slot
	};""", """		std::string file;           // resolved image path ("" with sourceId)
		int sourceId = 0;           // >0: borrow that native slot's sprite instead
		Sprites *sprite = nullptr;  // per game; a loaded file is owned by no slot
	};""")
rep("""		const std::string &filename, int frames = 0, int flags = -1);
""", """		const std::string &filename, int frames = 0, int flags = -1);
	// Same, but the slot borrows the sprite of native slot `sourceId`.
	static void setWeaponSpriteOverrideNative(int weaponId, const std::string &weaponName, int targetId, int sourceId);
""")
open(p, 'w', encoding='utf-8', newline='').write(s)

p = 'Sprites.cpp'
s = open(p, encoding='utf-8').read()
rep('#include "Config.h"\n', '#include "Config.h"\n#include "CustomWeapons.h"\n')
rep("""void Sprites::onConstructGlobalContext(int a1) {
	if(!Config::customSpritesEnabled || (customSprites.empty() && fileOverrides.empty()) || !Game::isValidDdGame())
		return;
""", """void Sprites::onConstructGlobalContext(int a1) {
	// The last game's weapon sprites died with its sprite table.
	weaponSwapped.clear();
	activeOverrideWeapon = -1;
	for(auto &o : weaponOverrides)
		o.sprite = nullptr;
	if(!Config::customSpritesEnabled || (customSprites.empty() && fileOverrides.empty() && weaponOverrides.empty())
	   || !Game::isValidDdGame())
		return;
""")
rep("""		auto loaded = weaponSprites.find(o.file);
		if(loaded == weaponSprites.end()) {
			Sprites *sprite = loadViaScratchSlot(addrDD_Display, addrPC_FileArchive, o.file);
			if(sprite)
				inheritNativeAnimation(addrDD_Display, sprite, o.targetId, o.file);
			loaded = weaponSprites.emplace(o.file, sprite).first;
		}
		o.sprite = loaded->second;
		if(o.sprite)
			spriteLog("SetWeaponSpriteOverride: weapon %d slot %d <- '%s' %d frames %dx%d flags=0x%X\\n",
				o.weaponId, o.targetId, o.file.c_str(), o.sprite->max_frames_word16,
				o.sprite->width_wordC, o.sprite->height_wordE, o.sprite->flags_word10);
	}""", """		if(o.sourceId > 0) {
			DWORD sourceSlot = addrDD_Display + kSpriteTableOffset + (DWORD)o.sourceId * 4;
			Sprites *source = jellyProbeRead(sourceSlot, 4) ? *(Sprites **)sourceSlot : nullptr;
			o.sprite = (source && jellyProbeRead((DWORD)source, sizeof(Sprites))) ? source : nullptr;
			spriteLog("SetWeaponSpriteOverride: weapon %d slot %d <- native %d (0x%X)\\n",
				o.weaponId, o.targetId, o.sourceId, (DWORD)o.sprite);
			continue;
		}
		auto loaded = weaponSprites.find(o.file);
		if(loaded == weaponSprites.end()) {
			Sprites *sprite = loadViaScratchSlot(addrDD_Display, addrPC_FileArchive, o.file);
			if(sprite)
				inheritNativeAnimation(addrDD_Display, sprite, o.targetId, o.file);
			loaded = weaponSprites.emplace(o.file, sprite).first;
		}
		o.sprite = loaded->second;
		if(o.sprite)
			spriteLog("SetWeaponSpriteOverride: weapon %d slot %d <- '%s' %d frames %dx%d flags=0x%X\\n",
				o.weaponId, o.targetId, o.file.c_str(), o.sprite->max_frames_word16,
				o.sprite->width_wordC, o.sprite->height_wordE, o.sprite->flags_word10);
		else
			spriteLog("SetWeaponSpriteOverride: weapon %d slot %d: '%s' failed to load\\n",
				o.weaponId, o.targetId, o.file.c_str());
	}""")
rep("""	for(auto &o : weaponOverrides) {
		if(o.weaponId == weaponId && o.weaponName == weaponName && o.targetId == targetId) {
			o.file = resolved;
			return;
		}
	}
	WeaponOverride o;
	o.weaponId = weaponId;
	o.weaponName = weaponName;
	o.targetId = targetId;
	o.file = resolved;
	weaponOverrides.push_back(o);
}
""", """	for(auto &o : weaponOverrides) {
		if(o.weaponId == weaponId && o.weaponName == weaponName && o.targetId == targetId) {
			o.file = resolved;
			o.sourceId = 0;
			return;
		}
	}
	WeaponOverride o;
	o.weaponId = weaponId;
	o.weaponName = weaponName;
	o.targetId = targetId;
	o.file = resolved;
	weaponOverrides.push_back(o);
}

void Sprites::setWeaponSpriteOverrideNative(int weaponId, const std::string &weaponName, int targetId, int sourceId) {
	if(targetId < kMinSpriteId || targetId > kMaxSpriteId || sourceId < kMinSpriteId || sourceId > kMaxSpriteId ||
	   (weaponId < 0 && weaponName.empty())) {
		spriteLog("SetWeaponSpriteOverride: invalid weapon=%d '%s' target=%d source=%d\\n",
			weaponId, weaponName.c_str(), targetId, sourceId);
		return;
	}
	for(auto &o : weaponOverrides) {
		if(o.weaponId == weaponId && o.weaponName == weaponName && o.targetId == targetId) {
			o.file.clear();
			o.sourceId = sourceId;
			return;
		}
	}
	WeaponOverride o;
	o.weaponId = weaponId;
	o.weaponName = weaponName;
	o.targetId = targetId;
	o.sourceId = sourceId;
	weaponOverrides.push_back(o);
}
""")
rep("""void Sprites::resetConfig() {
	customSprites.clear();
	resolvedSpriteIds.clear();
	spriteOverrides.clear();
	fileOverrides.clear();
	frameHints.clear();
	flagHints.clear();
}""", """void Sprites::resetConfig() {
	customSprites.clear();
	resolvedSpriteIds.clear();
	spriteOverrides.clear();
	fileOverrides.clear();
	frameHints.clear();
	flagHints.clear();
	DWORD addrDD_Display = Game::getAddrDdDisplay();
	if(addrDD_Display)
		restoreWeaponSlots(addrDD_Display);
	weaponSwapped.clear();
	weaponOverrides.clear();
	activeOverrideWeapon = -1;
	weaponSwapLogLines = 0;
}""")
rep("""DWORD __fastcall hookDestroySprite(Sprites* sprite, int, int flags) {
	auto alias = Sprites::aliases.find(sprite);""", """Sprites *Sprites::onDestroyWeaponSprite(Sprites *sprite) {
	for(auto it = weaponSwapped.begin(); it != weaponSwapped.end(); ++it) {
		if(it->sprite == sprite) {
			// WA is freeing the slot our weapon sprite borrowed: the native it
			// displaced is the slot's real owner. Ours is freed with the rest.
			Sprites *displaced = it->displaced;
			weaponSwapped.erase(it);
			return displaced;
		}
	}
	return sprite;
}

void Sprites::onDestroyGlobalContext() {
	DWORD addrDD_Display = Game::getAddrDdDisplay();
	if(addrDD_Display)
		restoreWeaponSlots(addrDD_Display);
	weaponSwapped.clear();
	activeOverrideWeapon = -1;
	// Loaded weapon sprites sit in no slot, so WA never frees them.
	std::vector<Sprites *> freed;
	for(auto &o : weaponOverrides) {
		if(o.sprite && o.sourceId <= 0 && std::find(freed.begin(), freed.end(), o.sprite) == freed.end()) {
			freed.push_back(o.sprite);
			destroyOneSprite(o.sprite, 1);
		}
		o.sprite = nullptr;
	}
}

DWORD __fastcall hookDestroySprite(Sprites* sprite, int, int flags) {
	sprite = Sprites::onDestroyWeaponSprite(sprite);
	if(!sprite)
		return 0;
	auto alias = Sprites::aliases.find(sprite);""")
rep("""	lua->set_function("SetSpriteOverride", spriteOverrideLua);
	lua->set_function("setSpriteOverride", spriteOverrideLua);
""", """	lua->set_function("SetSpriteOverride", spriteOverrideLua);
	lua->set_function("setSpriteOverride", spriteOverrideLua);
	// SetWeaponSpriteOverride(weapon, target, file|nativeId[, frames[, flags]]):
	// weapon is a custom weapon id or its registered name.
	auto weaponSpriteOverrideLua = [](sol::object weapon, int targetId, sol::object source,
			sol::optional<int> frames, sol::optional<int> flags) {
		int weaponId = -1;
		std::string weaponName;
		if(weapon.is<int>())
			weaponId = weapon.as<int>();
		else if(weapon.is<std::string>())
			weaponName = weapon.as<std::string>();
		if(weaponId < 0 && weaponName.empty()) {
			spriteLog("SetWeaponSpriteOverride: target %d: weapon is neither id nor name\\n", targetId);
			return;
		}
		if(source.is<std::string>())
			setWeaponSpriteOverride(weaponId, weaponName, targetId, source.as<std::string>(),
				frames.value_or(0), flags.value_or(-1));
		else if(source.is<int>())
			setWeaponSpriteOverrideNative(weaponId, weaponName, targetId, source.as<int>());
		else
			spriteLog("SetWeaponSpriteOverride: target %d: source is neither sprite id nor file name\\n", targetId);
	};
	lua->set_function("SetWeaponSpriteOverride", weaponSpriteOverrideLua);
	lua->set_function("setWeaponSpriteOverride", weaponSpriteOverrideLua);
""")
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')

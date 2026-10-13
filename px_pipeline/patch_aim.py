p = r'C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm\src\CustomWeapons.cpp'
s = open(p, 'rb').read().decode('utf-8')
crlf = '\r\n' in s
s = s.replace('\r\n', '\n')
a = s.index('static void __stdcall aimPoseAfter(DWORD worm, int phase0) {')
b = s.index('// Replaces `call 0x51CFC0` in the worm frame handler.')
new = r'''static void __stdcall aimPoseAfter(DWORD worm, int phase0) {
	typedef CustomWeapons CW;
	if(!CW::customWeaponsEnabled || aimPoseSprite0 < 0)
		return;
	DWORD wsAddr = *(DWORD *)(worm + 0x36C);
	if(!wsAddr || !jellyProbeRead(wsAddr, 0x64))
		return;
	CW::WeaponStruct *ws = (CW::WeaponStruct *)wsAddr;
	int idx = CW::weaponIdOf(ws);
	if(idx < CW::maxStandardWeapons || idx >= CW::numAllWeapons)
		return;
	DWORD anim = *(DWORD *)(worm + 0x368);
	int sprite, phase;
	if(!wormAnimGet(anim, sprite, phase))
		return;
	int expected = callWormAimSprite(wsAddr, worm);
	int target = *(int *)(worm + 0x24C);
	int aimMode = *(int *)(worm + 0x268);
	int selected = *(int *)(worm + 0x170);
	int state = *(int *)(worm + 0x44);
	int side = *(int *)(worm + 0x1A8);
	// Bit 0x800000 of an animator sprite is the reverse-playback flag (the
	// weapon put-away animation), not part of the sprite id.
	int spriteId = sprite & 0x7FFFFF;
	bool idle = state == 0x65;
	bool aimStates = state == 0x67 || state == 0x68;
	const char *action = "none";

	if(expected > 0 && spriteId == expected) {
		aimPoseMismatchFrames.erase(worm);
		// Idle/aiming/charging only: the fired states (0x69..0x6B) play the
		// weapon's own sequence in phases past 0x10000, which easing would flatten.
		// With aim mode 0 WA's update returns early, so the easing is ours alone.
		bool follow = (phase == phase0) || (aimStates && aimMode == 0);
		if((idle || aimStates) && follow && phase <= 0x10000 && phase != target) {
			int next = target;
			if(abs(phase - target) >= 0x16C)
				next = (int)(((long long)0x4CCC * target + (long long)0xB333 * phase) >> 16);
			DWORD vt = *(DWORD *)anim;
			((WormAnimSetPhaseFn)*(DWORD *)(vt + 0x10))(anim, next);
			action = "phase";
		}
	} else if(expected > 0 && selected != 0 && ((ws->unknown30 == 1 && aimMode != 0 && idle) || aimStates)) {
		// The animator holds some other sprite while the worm aims (for
		// instance the end frame of a previous throw swing, sprite 415 against
		// 412). WA's draw-weapon link animations end well within a second; past
		// that, put the animator back on the aim sprite.
		int &frames = aimPoseMismatchFrames[worm];
		if(++frames > (aimStates ? 30 : 50)) {
			frames = 0;
			DWORD vt = *(DWORD *)anim;
			((WormAnimSetFn)*(DWORD *)(vt + 0x18))(anim, expected, 0x8000);
			action = "reset";
		} else {
			action = "wait";
		}
	} else {
		aimPoseMismatchFrames.erase(worm);
	}

	// Log when the situation changes, plus a sample every 45 frames while aiming.
	static int last[11] = {0};
	static int sampleTick = 0;
	int now[11] = {idx, ws->unknown30, ws->unknown34, selected, aimMode, sprite, expected, state,
		(int)(action[0]), (int)(phase == target), side};
	bool changed = memcmp(now, last, sizeof(now)) != 0 || action[0] == 'r';
	bool sample = aimStates && ++sampleTick >= 45;
	if(sample)
		sampleTick = 0;
	if(changed || sample) {
		memcpy(last, now, sizeof(now));
		aimPoseLog("%s worm=%08X wpn=%d type=%d sub=%d sel=%d aimMode=%d side=%d state=0x%X sprite=%d(before %d) expected=%d phase0=0x%X phase=0x%X aim=0x%X smooth=0x%X action=%s\n",
			changed ? "chg" : "smp", worm, idx, ws->unknown30, ws->unknown34, selected, aimMode, side, state, sprite,
			aimPoseSprite0, expected, phase0, phase, target, *(int *)(worm + 0x270), action);
	}
}

'''
s = s[:a] + new + s[b:]
assert 'aimPoseLogLines >= 400' in s
s = s.replace('aimPoseLogLines >= 400', 'aimPoseLogLines >= 3000')
if crlf:
    s = s.replace('\n', '\r\n')
open(p, 'wb').write(s.encode('utf-8'))
print('patched, crlf =', crlf)

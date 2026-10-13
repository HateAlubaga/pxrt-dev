p = r"C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm\src\packages\PackageManager.cpp"
s = open(p, encoding="utf-8").read()
inc = '#include <sol/sol.hpp>\n'
hdrs = ['gametasks/CTaskMissile', 'gametasks/CTaskMine', 'gametasks/CTaskCrate', 'gametasks/CTaskOildrum',
        'gametasks/CTaskArrow', 'gametasks/CTaskCanister', 'gametasks/CTaskCross', 'gametasks/CTaskLand',
        'gametasks/CTaskOldWorm', 'tasks/CTaskTeam', 'tasks/CTaskTurnGame']
extra = ''.join('#include "../entities/%s.h"\n' % h for h in hdrs)
assert inc in s
s = s.replace(inc, inc + extra + '\nstatic int callbackGeneration = 1;\n', 1)
old = """	CTask::CTask_vtableHooks<CTaskWorm>::clearCallbacks();
	CTask::CTask_vtableHooks<CTaskTeam>::clearCallbacks();
	CGameTask::CGameTask_vtableHooks<CTaskWorm>::clearCallbacks();
}"""
lines = ["""	CTask::CTask_vtableHooks<CTaskWorm>::clearCallbacks();
	CTask::CTask_vtableHooks<CTaskTeam>::clearCallbacks();
	CGameTask::CGameTask_vtableHooks<CTaskWorm>::clearCallbacks();
	// Lua vtable callbacks on every other class must go too: a reload
	// re-runs each package, which registers them again, so leftovers
	// would fire twice and keep closures from the old package env alive.
	CTask::CTask_vtableHooks<CTaskTurnGame>::clearCallbacks();"""]
for c in ['CTaskMissile', 'CTaskMine', 'CTaskCrate', 'CTaskOildrum', 'CTaskArrow', 'CTaskCanister',
          'CTaskCross', 'CTaskLand', 'CTaskOldWorm']:
    lines.append("	CTask::CTask_vtableHooks<%s>::clearCallbacks();" % c)
    lines.append("	CGameTask::CGameTask_vtableHooks<%s>::clearCallbacks();" % c)
lines.append("	++callbackGeneration;\n}")
assert old in s
s = s.replace(old, "\n".join(lines))
old2 = '	lua->set_function("registerCallback_onTurnStart", &Callbacks<&onTurnStart_t>::registerCallback);\n'
assert old2 in s
s = s.replace(old2, old2 + '	// Bumped by clearCallbacks(): lets Lua libraries notice that every\n'
              '	// hook they registered is gone and must be registered again.\n'
              '	lua->set_function("getCallbackGeneration", []() { return callbackGeneration; });\n')
open(p, "w", encoding="utf-8").write(s)
print("ok")

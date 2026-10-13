// Mirrors LuaNative.cpp callRaw/invoke and the CTask vtable hook pattern.
// ehtest_old: catch-all __except and the original sol.hpp (code before the fix).
// ehtest_new: Lua-depth filter and the patched sol.hpp (protected std::function callbacks).
// Run: ehtest_X.exe <scenario 1..3>; prints RESULT ok / RESULT crash.
#include <sol/sol.hpp>
#include <Windows.h>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <stdexcept>
#include <vector>

static sol::state * g_lua;
static std::vector<std::function<int(int)>> g_callbacks;
static int g_afterCallbacks = 0;

static void * luaCurrentCi(lua_State * L) {
	lua_Debug ar;
	return (L && lua_getstack(L, 0, &ar)) ? (void *)ar.i_ci : nullptr;
}
struct LuaMark { lua_State * caller, * main; void * callerCi, * mainCi; };
static LuaMark luaMark(lua_State * caller) {
	LuaMark m;
	m.main = g_lua->lua_state();
	m.caller = caller ? caller : m.main;
	m.callerCi = luaCurrentCi(m.caller);
	m.mainCi = luaCurrentCi(m.main);
	return m;
}
static int callRawFilter(const LuaMark * m) {
#ifdef OLD_CALLRAW
	(void)m;
	return EXCEPTION_EXECUTE_HANDLER;
#else
	if(luaCurrentCi(m->caller) != m->callerCi || luaCurrentCi(m->main) != m->mainCi)
		return EXCEPTION_CONTINUE_SEARCH;
	return EXCEPTION_EXECUTE_HANDLER;
#endif
}
typedef int (__cdecl * NativeFn)(int);
static bool callRaw(NativeFn f, int a, int * out, const LuaMark & mark) {
	__try {
		*out = f(a);
		return true;
	} __except(callRawFilter(&mark)) {
		return false;
	}
}

// "WA code": runs the registered hooks like CTask_vtableHooks::hookVtable8.
static int __cdecl fakeWaFunction(int a) {
	int ret = 0;
	for(auto & cb : g_callbacks) {
		try {
			ret |= cb(a);
		} catch(std::exception & e) {
			printf("  hook caught: %s\n", e.what());
		}
	}
	g_afterCallbacks++;
	return ret + 1000;
}
// "WA code" that faults by itself (no Lua nested).
static int __cdecl faultingWaFunction(int) {
	volatile int * p = nullptr;
	return *p;
}

static const char * g_script;
static void runScript() {
	sol::protected_function_result r = g_lua->safe_script(g_script, sol::script_pass_on_error);
	if(!r.valid()) {
		sol::error err = r;
		printf("  script error: %s\n", err.what());
	}
}
static bool runGuarded() {
	__try {
		runScript();
		return true;
	} __except(printf("  UNHANDLED SEH 0x%08lX\n", GetExceptionCode()), EXCEPTION_EXECUTE_HANDLER) {
		return false;
	}
}

int main(int argc, char ** argv) {
	setvbuf(stdout, nullptr, _IONBF, 0);
	int scenario = argc > 1 ? atoi(argv[1]) : 1;
	sol::state lua;
	g_lua = &lua;
	lua.open_libraries(sol::lib::base);
	lua.set_function("registerHook", [](std::function<int(int)> cb) { g_callbacks.push_back(cb); });
	lua.set_function("callNative", [](int which, sol::variadic_args va) {
		NativeFn f = which == 1 ? fakeWaFunction : faultingWaFunction;
		int out = 0;
		if(!callRaw(f, 7, &out, luaMark(va.lua_state())))
			throw std::runtime_error("callNative: access violation");
		return out;
	});
	lua.set_function("badRead", [](int addr) { return *(volatile int *)addr; });
	const char * scripts[] = {
		"",
		// 1: fault in WA code called from Lua: must become a Lua error (both builds)
		"local ok, e = pcall(callNative, 2) print('  s1 pcall:', ok, e)",
		// 2: hook callback raises a Lua error inside a native call made under pcall
		"registerHook(function(a) error('boom in hook') end)\n"
		"local ok, e = pcall(callNative, 1) print('  s2 pcall:', ok, e)",
		// 3: AV inside a Lua-bound function in a nested pcall in a hook, then a later Lua error
		"registerHook(function(a) local ok, e = pcall(badRead, 0) print('  s3 nested pcall:', ok, e) return 0 end)\n"
		"local ok, e = pcall(callNative, 1) print('  s3 first pcall:', ok, e)\n"
		"local ok2, e2 = pcall(error, 'later error') print('  s3 later pcall:', ok2, e2)",
	};
	if(scenario < 1 || scenario > 3)
		return 1;
	printf("scenario %d\n", scenario);
	g_script = scripts[scenario];
	bool ok = runGuarded();
	g_callbacks.clear(); // drop Lua references before the state closes
	if(!ok) {
		printf("RESULT crash\n");
		return 2;
	}
	printf("  native code after hooks ran %d time(s)\n", g_afterCallbacks);
	printf("RESULT ok\n");
	return 0;
}

#pragma once
#include <sol/sol.hpp>
struct Lua {
	static Lua &getInstance() { static Lua l; return l; }
	sol::state *getState() { static sol::state s; return &s; }
};

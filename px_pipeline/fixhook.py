p = r'C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm\src\LuaNative.cpp'
s = open(p, encoding='utf-8', newline='').read()
crlf = '\r\n' in s
s = s.replace('\r\n', '\n')


def rep(a, b):
    global s
    assert s.count(a) == 1, a
    s = s.replace(a, b)


rep('''	g_frames.push_back({h, regs, stack, false, 0});
	DWORD result = 0;''', '''	g_frames.push_back({h, regs, stack, false, 0});
	size_t fi = g_frames.size() - 1;
	DWORD result = 0;''')
rep('''				done = true;
				if(res.return_count() > 0) {
					sol::object o = res.get<sol::object>(0);
					result = toDword(o);
				}''', '''				done = true;
				sol::object o = res.return_count() > 0 ? res.get<sol::object>(0) : sol::object();
				// No return value after callHookOriginal passes the original's EAX through.
				if(o.valid() && o.get_type() != sol::type::lua_nil)
					result = toDword(o);
				else if(g_frames[fi].calledOriginal)
					result = g_frames[fi].originalResult;''')
rep('''		HookFrame & f = g_frames.back();
		if(f.calledOriginal) {
			result = f.originalResult;''', '''		if(g_frames[fi].calledOriginal) {
			result = g_frames[fi].originalResult;''')
rep('''	h->fn = fn;
	h->thunk = buildThunk(h);
	g_hooks.push_back(h);
	h->id = (int)g_hooks.size();
	try {
		Hooks::minhook("lua:" + name, addr, (DWORD *)h->thunk, &h->trampoline);
	} catch(...) {
		h->enabled = false;
		h->fn = sol::nil;
		throw;
	}
	return h->id;''', '''	h->fn = fn;
	h->thunk = buildThunk(h);
	try {
		Hooks::minhook("lua:" + name, addr, (DWORD *)h->thunk, &h->trampoline);
	} catch(...) {
		VirtualFree(h->thunk, 0, MEM_RELEASE);
		delete h;
		throw;
	}
	g_hooks.push_back(h);
	h->id = (int)g_hooks.size();
	return h->id;''')
rep('''	HookFrame * frame = nullptr;
	for(auto it = g_frames.rbegin(); it != g_frames.rend(); ++it) {
		if(it->hook == h) {
			frame = &*it;
			break;
		}
	}''', '''	// Index, not pointer: nested hooks fired by the original may grow g_frames.
	int fi = -1;
	for(int i = (int)g_frames.size() - 1; i >= 0; i--) {
		if(g_frames[i].hook == h) {
			fi = i;
			break;
		}
	}
	HookFrame * frame = fi >= 0 ? &g_frames[fi] : nullptr;''')
rep('''	DWORD out = callHookOriginalRaw(h, r, stack.data());
	if(frame) {
		frame->calledOriginal = true;
		frame->originalResult = out;''', '''	DWORD out = callHookOriginalRaw(h, r, stack.data());
	if(fi >= 0) {
		g_frames[fi].calledOriginal = true;
		g_frames[fi].originalResult = out;''')
if crlf:
    s = s.replace('\n', '\r\n')
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok', crlf)

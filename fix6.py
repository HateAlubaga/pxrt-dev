p = 'patch6.py'
s = open(p, encoding='utf-8').read()
old1 = "s = rrep(s, r'const char \*kHelp =.*?mlog\(|const char \*kHelp =\n.*?reload \(re-read \[music\] from the ini\)\";', HELP_NEW)"
new1 = "s = rrep(s, r'const char \*kHelp =\s*\".*?reload \(re-read \[music\] from the ini\)\";', HELP_NEW)"
assert old1 in s, 'kHelp line'
s = s.replace(old1, new1)
old2 = "s = rep(s, 'std::mutex g_startMutex;',\n            'std::mutex g_startMutex;\n'"
new2 = "s = rep(s, 'std::mutex g_startMutex;        // serialises startManagedSync',\n            'std::mutex g_startMutex;        // serialises startManagedSync\n'"
assert old2 in s, 'mutex line'
s = s.replace(old2, new2)
open(p, 'w', encoding='utf-8').write(s)
print('fixed')

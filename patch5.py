import re

R = r'C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm' + '\\'


def rw(name, fn):
    p = R + name
    raw = open(p, encoding='utf-8', newline='').read()
    crlf = '\r\n' in raw
    s = raw.replace('\r\n', '\n')
    s2 = fn(s)
    assert s2 != s, name + ' unchanged'
    if crlf:
        s2 = s2.replace('\n', '\r\n')
    open(p, 'w', encoding='utf-8', newline='').write(s2)


def rep(s, old, new, count=1):
    assert old in s, 'anchor missing: ' + old[:80]
    return s.replace(old, new) if count == 0 else s.replace(old, new, count)


def rrep(s, pat, new):
    m = re.search(pat, s, re.S)
    assert m, 'regex anchor missing: ' + pat[:80]
    return s[:m.start()] + new + s[m.end():]


def music(s):
    s = rep(s, 'std::unordered_map<int, std::unique_ptr<TrackerTrack>> g_tracks;',
            '// Leaked on purpose: a TrackerTrack owns a std::thread, and a static destructor that\n'
            '\t// runs ~thread on a joinable thread at process exit would call std::terminate.\n'
            '\tstd::unordered_map<int, std::shared_ptr<TrackerTrack>> &g_tracks =\n'
            '\t\t*new std::unordered_map<int, std::shared_ptr<TrackerTrack>>();')
    s = rep(s, 'int g_nextTrackId = 1;', 'std::atomic<int> g_nextTrackId{1};')
    s = rep(s, 'std::atomic<int> g_epoch{0};',
            'std::atomic<int> g_epoch{0};\n'
            '\t// Newest managed start wins. A download that finishes after a newer start is dropped.\n'
            '\tstd::atomic<int> g_startToken{0};\n'
            '\tstd::atomic<int> g_pending{0};  // downloads in flight\n'
            '\tstd::mutex g_startMutex;        // serialises startManagedSync')
    s = rep(s, 'TrackerTrack *findTrack(int id) {', 'std::shared_ptr<TrackerTrack> findTrack(int id) {')
    s = rep(s, 'return it->second.get();', 'return it->second;')
    s = rep(s, 'auto *track = findTrack(', 'auto track = findTrack(', 0)
    s = rep(s, 'std::thread(playbackThread, track)', 'std::thread(playbackThread, track.get())')
    s = rep(s, 'std::make_unique<TrackerTrack>()', 'std::make_shared<TrackerTrack>()')
    s = rep(s, 'std::unique_ptr<TrackerTrack>', 'std::shared_ptr<TrackerTrack>', 0)
    s = rrep(s, r'\n\s*if \(g_tracks\.empty\(\)\) \{\s*g_nextTrackId = 1;\s*\}', '')
    s = rep(s, 'findTrack(id)->skipRequested = true;', 'if (auto t = findTrack(id)) {\n\t\t\t\tt->skipRequested = true;\n\t\t\t}')

    # --- managed start: token, mutex, pending flag
    s = rep(s, 'std::string startManagedSync(const std::string &target, bool shuffle, bool loop, int volumePercent, int epoch) {',
            'std::string startManagedSync(const std::string &target, bool shuffle, bool loop, int volumePercent, int epoch, int token) {\n'
            '\t\tstd::lock_guard<std::mutex> startLock(g_startMutex);\n'
            '\t\tif (token != g_startToken.load()) {\n'
            '\t\t\tthrow std::runtime_error("superseded by a newer music start");\n'
            '\t\t}')
    s = rrep(s, r'std::string startManaged\(const std::string &target, bool shuffle, bool loop, int volumePercent\) \{.*?return startManagedSync\(target, shuffle, loop, volumePercent, epoch\);\s*\}',
             'std::string startManaged(const std::string &target, bool shuffle, bool loop, int volumePercent) {\n'
             '\t\tconst int epoch = g_epoch.load();\n'
             '\t\tconst int token = ++g_startToken;\n'
             '\t\tif (isUrl(target)) {\n'
             '\t\t\t++g_pending;\n'
             '\t\t\tstd::thread([=]() {\n'
             '\t\t\t\ttry {\n'
             '\t\t\t\t\tconst auto path = Music::resolveTrackerPath(target);\n'
             '\t\t\t\t\tif (epoch == g_epoch.load() && token == g_startToken.load()) {\n'
             '\t\t\t\t\t\tmlog("%s", startManagedSync(path, shuffle, loop, volumePercent, epoch, token).c_str());\n'
             '\t\t\t\t\t}\n'
             '\t\t\t\t} catch (const std::exception &e) {\n'
             '\t\t\t\t\tmlog("download/play failed: %s", e.what());\n'
             '\t\t\t\t}\n'
             '\t\t\t\t--g_pending;\n'
             '\t\t\t}).detach();\n'
             '\t\t\treturn "downloading " + target + " (starts when ready)";\n'
             '\t\t}\n'
             '\t\treturn startManagedSync(target, shuffle, loop, volumePercent, epoch, token);\n'
             '\t}')
    s = rep(s, 'if (isTrackPlaying(managedId())) {',
            'if (g_pending.load() > 0) {\n'
            '\t\t\tmlog("autoplay(%s): download in progress", why);\n'
            '\t\t\treturn;\n'
            '\t\t}\n'
            '\t\tif (isTrackPlaying(managedId())) {')

    # --- download: status check, .part + rename, sane cache extension
    s = rrep(s, r'bool ok = false;\s*if \(WinHttpSendRequest\(request.*?WinHttpCloseHandle\(request\);',
             'bool ok = false;\n'
             '\t\tconst std::string partPath = destPath + ".part";\n'
             '\t\tif (WinHttpSendRequest(request, WINHTTP_NO_ADDITIONAL_HEADERS, 0,\n'
             '\t\t                       WINHTTP_NO_REQUEST_DATA, 0, 0, 0) &&\n'
             '\t\t    WinHttpReceiveResponse(request, nullptr)) {\n'
             '\t\t\tDWORD status = 0;\n'
             '\t\t\tDWORD statusSize = sizeof(status);\n'
             '\t\t\tif (!WinHttpQueryHeaders(request, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,\n'
             '\t\t\t                         WINHTTP_HEADER_NAME_BY_INDEX, &status, &statusSize, WINHTTP_NO_HEADER_INDEX)) {\n'
             '\t\t\t\tstatus = 0;\n'
             '\t\t\t}\n'
             '\t\t\tif (status != 200) {\n'
             '\t\t\t\tmlog("download failed: HTTP status %lu for %s", static_cast<unsigned long>(status), url.c_str());\n'
             '\t\t\t} else {\n'
             '\t\t\t\tstd::ofstream out(partPath, std::ios::binary);\n'
             '\t\t\t\tif (out.good()) {\n'
             '\t\t\t\t\tbool complete = false;\n'
             '\t\t\t\t\tstd::vector<char> chunk(64 * 1024);\n'
             '\t\t\t\t\tfor (;;) {\n'
             '\t\t\t\t\t\tDWORD available = 0;\n'
             '\t\t\t\t\t\tif (!WinHttpQueryDataAvailable(request, &available)) {\n'
             '\t\t\t\t\t\t\tbreak;\n'
             '\t\t\t\t\t\t}\n'
             '\t\t\t\t\t\tif (available == 0) {\n'
             '\t\t\t\t\t\t\tcomplete = true;\n'
             '\t\t\t\t\t\t\tbreak;\n'
             '\t\t\t\t\t\t}\n'
             '\t\t\t\t\t\tDWORD read = 0;\n'
             '\t\t\t\t\t\tconst DWORD toRead = (std::min)(available, static_cast<DWORD>(chunk.size()));\n'
             '\t\t\t\t\t\tif (!WinHttpReadData(request, chunk.data(), toRead, &read) || read == 0) {\n'
             '\t\t\t\t\t\t\tbreak;\n'
             '\t\t\t\t\t\t}\n'
             '\t\t\t\t\t\tout.write(chunk.data(), read);\n'
             '\t\t\t\t\t}\n'
             '\t\t\t\t\tout.close();\n'
             '\t\t\t\t\tstd::error_code ec;\n'
             '\t\t\t\t\tconst auto size = fs::file_size(partPath, ec);\n'
             '\t\t\t\t\tif (complete && !out.fail() && !ec && size > 0) {\n'
             '\t\t\t\t\t\tfs::remove(destPath, ec);\n'
             '\t\t\t\t\t\tfs::rename(partPath, destPath, ec);\n'
             '\t\t\t\t\t\tok = !ec;\n'
             '\t\t\t\t\t}\n'
             '\t\t\t\t\tif (!ok) {\n'
             '\t\t\t\t\t\tmlog("download incomplete or not writable: %s", url.c_str());\n'
             '\t\t\t\t\t\tfs::remove(partPath, ec);\n'
             '\t\t\t\t\t}\n'
             '\t\t\t\t}\n'
             '\t\t\t}\n'
             '\t\t}\n'
             '\n'
             '\t\tWinHttpCloseHandle(request);')
    s = rep(s, 'return ss.str() + extensionFromPath(url);',
            '// Extension from the URL path only (not the query string or the host), and only a\n'
            '\t\t// tracker extension, so the cache file name is always valid.\n'
            '\t\tconst std::string pathPart = url.substr(0, url.find_first_of("?#"));\n'
            '\t\tconst auto slash = pathPart.find_last_of(\'/\');\n'
            '\t\tconst std::string leaf = slash == std::string::npos ? pathPart : pathPart.substr(slash + 1);\n'
            '\t\tstd::string ext = ".mod";\n'
            '\t\tconst auto dot = leaf.rfind(\'.\');\n'
            '\t\tif (dot != std::string::npos && isTrackerExtension(leaf.substr(dot))) {\n'
            '\t\t\text = toLower(leaf.substr(dot));\n'
            '\t\t}\n'
            '\t\treturn ss.str() + ext;')
    # readConfig runs from Config::readPrivateProfile before the module-enabled check: stay quiet while off
    s = rep(s, 'mlog("config: Enabled=%d', 'if (g_cfg.enabled) mlog("config: Enabled=%d')
    return s


def scheme(s):
    s = rep(s, "if(line.empty() || line[0] == ';' || line[0] == '#')", "if(line.empty() || line[0] == ';')")
    s = rep(s, '\t\tfor(char c : value) {\n\t\t\tif(c == \',\' || c == \';\' || c == \' \' || c == \'\\t\')',
            '\t\tstd::string v = value;  // an inline "; comment" is not part of the module list\n'
            '\t\tconst size_t comment = v.find(\';\');\n'
            '\t\tif(comment != std::string::npos)\n'
            '\t\t\tv.erase(comment);\n'
            '\t\tfor(char c : v) {\n\t\t\tif(c == \',\' || c == \' \' || c == \'\\t\')')
    # persist the set of scheme-enabled modules: session.jelly restores them as ordinary explicit packages
    s = rep(s, '\t// Enable the modules bound to `sel`, disable the ones the previous scheme brought in.',
            '\tstd::string addedFile() {\n'
            '\t\treturn Config::jellyDir + "\\\\scheme_added.txt";\n'
            '\t}\n\n'
            '\tvoid loadAdded() {\n'
            '\t\tstd::ifstream in(addedFile());\n'
            '\t\tstd::string line;\n'
            '\t\twhile(std::getline(in, line)) {\n'
            '\t\t\tline = trim(line);\n'
            '\t\t\tif(!line.empty())\n'
            '\t\t\t\tg_schemeAdded.insert(line);\n'
            '\t\t}\n'
            '\t}\n\n'
            '\tvoid saveAdded() {\n'
            '\t\tstd::error_code ec;\n'
            '\t\tfs::create_directories(Config::jellyDir, ec);\n'
            '\t\tstd::ofstream out(addedFile(), std::ios::trunc);\n'
            '\t\tfor(auto &n : g_schemeAdded)\n'
            '\t\t\tout << n << "\\n";\n'
            '\t}\n\n'
            '\t// Enable the modules bound to `sel`, disable the ones the previous scheme brought in.')
    s = rep(s, '\t\tstd::set<std::string> keep;\n\t\tstd::stringstream report;',
            '\t\tstd::set<std::string> keep;\n\t\tconst auto autostart = PackageManager::autostartEnabledNames();\n\t\tstd::stringstream report;')
    s = rep(s, '\t\t\tif(pm.isExplicitlyEnabled(*it)) {\n\t\t\t\tstd::string err = pm.disableForScheme(*it);',
            '\t\t\tif(pm.isExplicitlyEnabled(*it) && !autostart.count(*it)) {\n\t\t\t\tstd::string err = pm.disableForScheme(*it);')
    s = rep(s, '\t\tg_appliedValid = true;\n\t\tg_appliedKey = state;\n',
            '\t\tg_appliedValid = true;\n\t\tg_appliedKey = state;\n\t\tsaveAdded();\n')
    s = rep(s, '\tslog("install: Enabled=%d", g_enabled);\n', '\tslog("install: Enabled=%d", g_enabled);\n\tloadAdded();\n')
    s = rep(s, '\t\tif(cmd == "apply") {\n\t\t\tif(!s.valid)\n\t\t\t\treturn "no scheme selected yet";\n',
            '\t\tif(cmd == "apply") {\n\t\t\tif(!s.valid)\n\t\t\t\treturn "no scheme selected yet";\n'
            '\t\t\tif(Game::getAddrDDGame() || !screenAllowsApply(Lobby::getFrontendScreen()))\n'
            '\t\t\t\treturn "apply works in the lobby only, not in a match";\n')
    return s


def chat(s):
    s = rep(s, '\tstd::string norm;\n\tif(msg && msg[0]) {\n\t\tnorm = msg;\n\t\twhile(!norm.empty() && norm[0] == \' \') norm.erase(0, 1);\n',
            '\tstd::string norm;\n\tbool hadSlash = false;  // a chat line that merely starts with the word "music" is not a command\n'
            '\tif(msg && msg[0]) {\n\t\tnorm = msg;\n\t\twhile(!norm.empty() && norm[0] == \' \') norm.erase(0, 1);\n'
            '\t\thadSlash = !norm.empty() && norm[0] == \'/\';\n')
    s = rep(s, 'if(!norm.empty() && (norm == "/scheme" ||', 'if(hadSlash && (norm == "/scheme" ||')
    s = rep(s, 'if(!norm.empty() && (norm == "/music" ||', 'if(hadSlash && (norm == "/music" ||')
    return s


def config(s):
    return rep(s, '\t\t\tPackageManager::getInstance().markAllEnabledExplicit();\n\t\t\treturn 0;',
               '\t\t\tPackageManager::getInstance().markAllEnabledExplicit();\n\t\t\tSchemeBind::onConfigReset();\n\t\t\treturn 0;')


rw('src/SchemeBind.cpp', scheme)
rw('src/Chat.cpp', chat)
rw('src/Config.cpp', config)
print('ok')

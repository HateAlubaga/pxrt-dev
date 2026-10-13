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


def rep(s, old, new):
    assert s.count(old) == 1, 'anchor count %d: %s' % (s.count(old), old[:80])
    return s.replace(old, new, 1)


def rrep(s, pat, new, flags=re.S):
    ms = list(re.finditer(pat, s, flags))
    assert len(ms) == 1, 'regex anchor count %d: %s' % (len(ms), pat[:80])
    m = ms[0]
    return s[:m.start()] + new + s[m.end():]


ONLINE_BLOCK = r'''	// ---- online source: The Mod Archive (modarchive.org) ---------------------------------

	bool isOnlineTarget(const std::string &target) {
		const std::string t = toLower(trim(target));
		return t == "modarchive" || t == "online" || t == "random";
	}

	unsigned long long onlineMaxBytes() {
		return static_cast<unsigned long long>((std::max)(g_cfg.maxSizeKB, 64)) * 1024ull;
	}

	bool recentlyPlayed(int id) {
		std::lock_guard<std::mutex> lock(g_recentMutex);
		return std::find(g_recentIds.begin(), g_recentIds.end(), id) != g_recentIds.end();
	}

	void rememberPlayed(int id) {
		std::lock_guard<std::mutex> lock(g_recentMutex);
		g_recentIds.push_back(id);
		while (g_recentIds.size() > 30) {
			g_recentIds.pop_front();
		}
	}

	// No network: a random cached track, else something from the local folder.
	std::string offlineFallbackFile() {
		auto files = collectTrackerFiles(Config::musicCacheDir);
		if (files.empty()) {
			files = collectTrackerFiles(kDefaultMusicDir);
		}
		if (files.empty()) {
			return "";
		}
		thread_local std::mt19937 gen(std::random_device{}());
		return files[std::uniform_int_distribution<size_t>(0, files.size() - 1)(gen)];
	}

	// Worker thread: fetch a module (random, or exactId > 0), then play it as the managed track.
	// Newer starts and match end make it stale: it then stops quietly.
	void onlineWorker(int token, int epoch, int exactId, int volumePercent, bool loopTrack) {
		struct PendingGuard {
			~PendingGuard() { --g_pending; }
		} guard;
		auto stale = [&]() { return epoch != g_epoch.load() || token != g_startToken.load(); };
		const MusicOnline::LogFn logFn = [](const std::string &m) { mlog("%s", m.c_str()); };
		try {
			for (int attempt = 0; attempt < 3 && !stale(); ++attempt) {
				MusicOnline::Fetched fetched;
				if (exactId > 0) {
					fetched = MusicOnline::fetchModArchiveId(Config::musicCacheDir, exactId, onlineMaxBytes(), logFn);
				} else {
					thread_local std::mt19937 gen(std::random_device{}());
					fetched = MusicOnline::fetchRandomModArchive(Config::musicCacheDir, g_cfg.maxId, onlineMaxBytes(), 10, gen,
					                                             recentlyPlayed, stale, logFn);
				}
				if (stale()) {
					return;
				}
				if (!fetched.ok) {
					mlog("online fetch failed: %s", fetched.error.c_str());
					if (exactId > 0) {
						announce("music: Mod Archive #" + std::to_string(exactId) + ": " + fetched.error);
						return;
					}
					const std::string file = offlineFallbackFile();
					if (file.empty()) {
						announce("music: no network and nothing cached (" + fetched.error + ")");
						return;
					}
					startManagedSync(file, false, loopTrack, volumePercent, epoch, token, true);
					announce("music: offline, playing " + fs::path(file).filename().string());
					return;
				}
				rememberPlayed(fetched.id);
				try {
					startManagedSync(fetched.path, false, loopTrack, volumePercent, epoch, token, true);
				} catch (const StartCancelled &) {
					return;
				} catch (const std::exception &e) {
					mlog("module #%d does not load: %s", fetched.id, e.what());
					std::error_code ec;
					fs::remove(fetched.path, ec);
					if (exactId > 0) {
						announce("music: Mod Archive #" + std::to_string(exactId) + " cannot be played");
						return;
					}
					continue;
				}
				announce("music: now playing " + fetched.name + " (Mod Archive #" + std::to_string(fetched.id) + ")");
				MusicOnline::pruneCache(Config::musicCacheDir, static_cast<size_t>((std::max)(g_cfg.cacheKeep, 5)));
				return;
			}
		} catch (const StartCancelled &) {
		} catch (const std::exception &e) {
			mlog("online start failed: %s", e.what());
		}
	}

	// Starts the online worker. Returns at once; the music starts when the download is done.
	std::string startOnline(int exactId) {
		const int epoch = g_epoch.load();
		const int token = ++g_startToken;
		const bool loopTrack = g_cfg.radio == 0 && g_cfg.loop != 0;
		const int volume = g_cfg.volume;
		++g_pending;
		try {
			std::thread(onlineWorker, token, epoch, exactId, volume, loopTrack).detach();
		} catch (...) {
			--g_pending;
			throw;
		}
		return exactId > 0 ? "fetching Mod Archive #" + std::to_string(exactId) + " ..."
		                   : std::string("fetching a new track from modarchive.org ...");
	}

	// Playback thread, natural end of a track. Radio: the next track is a new download.
	void onTrackFinished(TrackerTrack *track) {
		if (!track->online || !g_cfg.radio || g_userStopped) {
			return;
		}
		if (track->epoch != g_epoch.load() || managedId() != track->id) {
			return;
		}
		if (GetTickCount() - track->startTick < 10000) {
			if (++g_fastEnds >= 3) {
				mlog("radio: stopped, tracks end within seconds");
				return;
			}
		} else {
			g_fastEnds = 0;
		}
		mlog("radio: track %d ended, fetching a new one", track->id);
		try {
			startOnline(0);
		} catch (...) {
		}
	}

'''

HELP_NEW = '''const char *kHelp =
		"/music new - download a NEW random track from modarchive.org and play it (also /music n)\\n"
		"/music mod <id> - play Mod Archive module #id\\n"
		"/music play [file|url|folder|N|cache] - play tracker music (no argument = [music] Track from wkJellyWorm.ini)\\n"
		"/music stop | pause | resume | next (online: a new track)\\n"
		"/music vol <0-100>\\n"
		"/music list - files in jelly\\\\music (N for /music play N)\\n"
		"/music cache - downloaded tracks (/music play cache plays them all)\\n"
		"/music status | reload (re-read [music] from the ini)";'''


def music(s):
    s = rep(s, '#include "Music.h"\n', '#include "Music.h"\n#include "MusicOnline.h"\n')
    s = rep(s, '#include <cstring>\n', '#include <cstring>\n#include <deque>\n')

    # extension list now lives in MusicOnline
    s = rrep(s, r'bool isTrackerExtension\(const std::string &ext\) \{.*?\n\t\}\n',
             'bool isTrackerExtension(const std::string &ext) {\n\t\treturn MusicOnline::isTrackerExtension(ext);\n\t}\n')
    # shared WinHTTP code
    s = rrep(s, r'\tstd::wstring toWide\(const std::string &value\) \{.*?\n\t\}\n\n', '')
    s = rrep(s, r'bool downloadUrlToFile\(const std::string &url, const std::string &destPath\) \{.*?\n\t\}\n',
             'bool downloadUrlToFile(const std::string &url, const std::string &destPath) {\n'
             '\t\tconst auto result = MusicOnline::download(url, destPath, 64ull * 1024 * 1024);\n'
             '\t\tif (!result.ok) {\n'
             '\t\t\tmlog("download failed: %s (%s)", result.error.c_str(), url.c_str());\n'
             '\t\t}\n'
             '\t\treturn result.ok;\n'
             '\t}\n')

    s = rep(s, 'std::string track = kDefaultMusicDir;',
            'std::string track = kDefaultMusicDir;\n'
            '\t\t// online source (Track=modarchive)\n'
            '\t\tint radio = 1;          // a finished online track is followed by a new download\n'
            '\t\tint maxId = 215000;     // random Mod Archive ids are drawn from 1..maxId\n'
            '\t\tint maxSizeKB = 3072;   // bigger modules are skipped\n'
            '\t\tint cacheKeep = 40;     // downloaded modules kept in jelly\\cache\\music')
    s = rep(s, 'std::string currentFile;\n',
            'std::string currentFile;\n\n'
            '\t\tbool online = false;  // fetched by the online source: radio replaces it when it ends\n'
            '\t\tint epoch = 0;        // g_epoch when playback started\n'
            '\t\tDWORD startTick = 0;\n')
    s = rep(s, 'std::mutex g_startMutex;        // serialises startManagedSync',
            'std::mutex g_startMutex;        // serialises startManagedSync\n'
            '\tstd::atomic<int> g_fastEnds{0};  // consecutive online tracks that ended within seconds\n'
            '\tstd::mutex g_recentMutex;\n'
            '\tstd::deque<int> g_recentIds;     // latest Mod Archive ids, so "new" does not repeat itself\n'
            '\tstd::mutex g_announceMutex;\n'
            '\tstd::vector<std::string> g_announce;  // shown in the chat from the game thread\n'
            '\tstd::atomic<bool> g_announcePending{false};')
    # tiny exception type + announce(), after mlog
    s = rep(s, '\tbool isUrl(const std::string &value) {',
            '\t// A start that was overtaken by a newer one, or by the end of the match. Not an error.\n'
            '\tstruct StartCancelled : std::runtime_error {\n'
            '\t\texplicit StartCancelled(const char *what) : std::runtime_error(what) {}\n'
            '\t};\n\n'
            '\t// Worker threads must not touch the game UI: queue the text for the game thread.\n'
            '\tvoid announce(const std::string &message) {\n'
            '\t\tmlog("%s", message.c_str());\n'
            '\t\tstd::lock_guard<std::mutex> lock(g_announceMutex);\n'
            '\t\tg_announce.push_back(message);\n'
            '\t\twhile (g_announce.size() > 3) {\n'
            '\t\t\tg_announce.erase(g_announce.begin());\n'
            '\t\t}\n'
            '\t\tg_announcePending = true;\n'
            '\t}\n\n'
            '\tbool isUrl(const std::string &value) {')

    s = rep(s, 'void playbackThread(TrackerTrack *track) {',
            'void onTrackFinished(TrackerTrack *track);\n\n\tvoid playbackThread(TrackerTrack *track) {')
    s = rrep(s, r'if \(!track->stopRequested\) \{\s*mlog\("track %d finished", track->id\);\s*\}\s*track->playing = false;',
             'const bool finished = !track->stopRequested;\n'
             '\t\tif (finished) {\n'
             '\t\t\tmlog("track %d finished", track->id);\n'
             '\t\t}\n'
             '\t\ttrack->playing = false;\n'
             '\t\tif (finished) {\n'
             '\t\t\tonTrackFinished(track);\n'
             '\t\t}')

    s = rep(s, 'std::string startManagedSync(const std::string &target, bool shuffle, bool loop, int volumePercent, int epoch, int token) {',
            'std::string startManagedSync(const std::string &target, bool shuffle, bool loop, int volumePercent, int epoch, int token,\n'
            '\t                             bool online = false) {')
    s = rep(s, 'throw std::runtime_error("superseded by a newer music start");', 'throw StartCancelled("superseded by a newer music start");')
    s = rep(s, 'throw std::runtime_error("match ended while loading music");', 'throw StartCancelled("match ended while loading music");')
    s = rep(s, 'if (Music::playTrackerMusic(id, loop, volumePercent / 100.0f) != 0) {',
            'if (auto loaded = findTrack(id)) {\n'
            '\t\t\tloaded->online = online;\n'
            '\t\t}\n'
            '\t\tif (Music::playTrackerMusic(id, loop, volumePercent / 100.0f) != 0) {')

    s = rep(s, '\t// URL targets download first; do that off the game thread so a slow server', ONLINE_BLOCK + '\t// URL targets download first; do that off the game thread so a slow server')
    s = rep(s, 'std::string startManaged(const std::string &target, bool shuffle, bool loop, int volumePercent) {\n',
            'std::string startManaged(const std::string &target, bool shuffle, bool loop, int volumePercent) {\n'
            '\t\tif (isOnlineTarget(target)) {\n'
            '\t\t\treturn startOnline(0);\n'
            '\t\t}\n')

    s = rrep(s, r'const char \*kHelp =\s*".*?reload \(re-read \[music\] from the ini\)";', HELP_NEW)

    s = rrep(s, r'track->playing = true;\s*track->playThread = std::thread\(playbackThread, track\.get\(\)\);',
             'track->epoch = g_epoch.load();\n'
             '\ttrack->startTick = GetTickCount();\n'
             '\ttrack->playing = true;\n'
             '\ttrack->playThread = std::thread(playbackThread, track.get());')

    s = rep(s, 'g_cfg.track = track.empty() ? kDefaultMusicDir : track;',
            'g_cfg.track = track.empty() ? kDefaultMusicDir : track;\n'
            '\tg_cfg.radio = GetPrivateProfileIntA("music", "Radio", 1, ini);\n'
            '\tg_cfg.maxId = std::clamp(static_cast<int>(GetPrivateProfileIntA("music", "ModArchiveMaxId", 215000, ini)), 1000, 100000000);\n'
            '\tg_cfg.maxSizeKB = std::clamp(static_cast<int>(GetPrivateProfileIntA("music", "MaxSizeKB", 3072, ini)), 64, 65536);\n'
            '\tg_cfg.cacheKeep = std::clamp(static_cast<int>(GetPrivateProfileIntA("music", "CacheKeep", 40, ini)), 5, 1000);')
    s = rrep(s, r'if \(g_cfg\.enabled\) mlog\("config: Enabled=%d.*?g_cfg\.track\.c_str\(\)\);',
             'if (g_cfg.enabled) {\n'
             '\t\tmlog("config: Enabled=%d AutoplayMatch=%d AutoplayLobby=%d Volume=%d Loop=%d Shuffle=%d Radio=%d Track=%s", g_cfg.enabled,\n'
             '\t\t     g_cfg.autoplayMatch, g_cfg.autoplayLobby, g_cfg.volume, g_cfg.loop, g_cfg.shuffle, g_cfg.radio,\n'
             '\t\t     g_cfg.track.c_str());\n'
             '\t}')

    # commands
    s = rep(s, 'std::string Music::handleCommand(const std::string &argsIn) {', 'std::string Music::runCommand(const std::string &argsIn) {')
    s = rrep(s, r'out \+= std::string\("\\nini: Enabled="\) \+ std::to_string\(g_cfg\.enabled\) \+ " Track=" \+ g_cfg\.track;',
             'out += std::string("\\nini: Enabled=") + std::to_string(g_cfg.enabled) + " Track=" + g_cfg.track +\n'
             '\t\t\t       " Radio=" + std::to_string(g_cfg.radio);\n'
             '\t\t\tif (g_pending.load() > 0) {\n'
             '\t\t\t\tout += "\\n(a download is in progress)";\n'
             '\t\t\t}')
    s = rrep(s, r'const int id = managedId\(\);\s*if \(!findTrack\(id\)\) \{\s*return "nothing loaded\. /music play first";',
             'if (cmd == "new" || cmd == "n" || cmd == "random" || cmd == "online") {\n'
             '\t\t\tg_userStopped = false;\n'
             '\t\t\tg_fastEnds = 0;\n'
             '\t\t\treturn startOnline(0);\n'
             '\t\t}\n'
             '\t\tif (cmd == "mod" || cmd == "id") {\n'
             '\t\t\tif (rest.empty() || !std::all_of(rest.begin(), rest.end(), [](unsigned char c) { return std::isdigit(c); }) || rest.size() > 9) {\n'
             '\t\t\t\treturn "usage: /music mod <Mod Archive module id>";\n'
             '\t\t\t}\n'
             '\t\t\tg_userStopped = false;\n'
             '\t\t\tg_fastEnds = 0;\n'
             '\t\t\treturn startOnline(std::stoi(rest));\n'
             '\t\t}\n'
             '\t\tif (cmd == "cache") {\n'
             '\t\t\tconst auto files = collectTrackerFiles(Config::musicCacheDir);\n'
             '\t\t\tif (files.empty()) {\n'
             '\t\t\t\treturn "cache is empty (/music new downloads tracks into jelly\\\\cache\\\\music)";\n'
             '\t\t\t}\n'
             '\t\t\tstd::stringstream ss;\n'
             '\t\t\tss << files.size() << " cached tracks (/music play cache plays them):";\n'
             '\t\t\tfor (size_t i = 0; i < files.size() && i < 12; ++i) {\n'
             '\t\t\t\tss << "\\n" << fs::path(files[i]).filename().string();\n'
             '\t\t\t}\n'
             '\t\t\tif (files.size() > 12) {\n'
             '\t\t\t\tss << "\\n...";\n'
             '\t\t\t}\n'
             '\t\t\treturn ss.str();\n'
             '\t\t}\n\n'
             '\t\tconst int id = managedId();\n'
             '\t\tif (!findTrack(id)) {\n'
             '\t\t\treturn "nothing loaded. /music new or /music play first";')
    s = rrep(s, r'g_userStopped = false;\s*return startManaged\(target, shuffle, g_cfg\.loop != 0, g_cfg\.volume\);',
             'if (toLower(target) == "cache") {\n'
             '\t\t\t\ttarget = Config::musicCacheDir;\n'
             '\t\t\t\tshuffle = true;\n'
             '\t\t\t}\n'
             '\t\t\tg_userStopped = false;\n'
             '\t\t\tg_fastEnds = 0;\n'
             '\t\t\treturn startManaged(target, shuffle, g_cfg.loop != 0, g_cfg.volume);')
    s = rrep(s, r'if \(cmd == "next"\) \{\s*if \(auto t = findTrack\(id\)\) \{\s*t->skipRequested = true;\s*\}\s*return "next";\s*\}',
             'if (cmd == "next") {\n'
             '\t\t\tauto t = findTrack(id);\n'
             '\t\t\tif (t && t->online) {\n'
             '\t\t\t\tg_userStopped = false;\n'
             '\t\t\t\tg_fastEnds = 0;\n'
             '\t\t\t\treturn startOnline(0);\n'
             '\t\t\t}\n'
             '\t\t\tif (t) {\n'
             '\t\t\t\tt->skipRequested = true;\n'
             '\t\t\t}\n'
             '\t\t\treturn "next";\n'
             '\t\t}')

    s = rep(s, 'void Music::registerLuaBindings() {',
            '// Texts queued by worker threads ("now playing ...") come first in the reply.\n'
            'std::string Music::handleCommand(const std::string &args) {\n'
            '\tstd::string reply;\n'
            '\tfor (const auto &note : takeAnnouncements()) {\n'
            '\t\treply += note + "\\n";\n'
            '\t}\n'
            '\treturn reply + runCommand(args);\n'
            '}\n\n'
            'bool Music::hasAnnouncements() {\n'
            '\treturn g_announcePending.load();\n'
            '}\n\n'
            'std::vector<std::string> Music::takeAnnouncements() {\n'
            '\tstd::vector<std::string> out;\n'
            '\tstd::lock_guard<std::mutex> lock(g_announceMutex);\n'
            '\tout.swap(g_announce);\n'
            '\tg_announcePending = false;\n'
            '\treturn out;\n'
            '}\n\n'
            'void Music::registerLuaBindings() {')
    return s


def header(s):
    s = rep(s, '#include <string>\n', '#include <string>\n#include <vector>\n')
    s = rep(s, '//   * Chat:  /music play|stop|pause|resume|next|vol|list|status|reload\n',
            '//   * Chat:  /music new|mod|play|stop|pause|resume|next|vol|list|cache|status|reload\n'
            '//\n'
            '// Track=modarchive in [music] downloads a new random module from modarchive.org every time\n'
            '// (cached in jelly\\cache\\music); with Radio=1 the next track is a new download too.\n')
    s = rep(s, '\tstatic std::string handleCommand(const std::string &args);\n',
            '\tstatic std::string handleCommand(const std::string &args);\n'
            '\t// Texts from background threads (download finished, "now playing"). The worker threads must not\n'
            '\t// touch the game UI, so the game thread shows these: FrameScheduler in a match, handleCommand in a lobby.\n'
            '\tstatic bool hasAnnouncements();\n'
            '\tstatic std::vector<std::string> takeAnnouncements();\n'
            '\tstatic std::string runCommand(const std::string &args);\n')
    return s


def frame(s):
    s = rep(s, '#include "Hud.h"\n', '#include "Chat.h"\n#include "Hud.h"\n')
    s = rep(s, '#include "Lua.h"\n', '#include "Lua.h"\n#include "Music.h"\n')
    s = rep(s, '\ttickTimers(tick);\n',
            '\ttickTimers(tick);\n'
            '\tif(Music::hasAnnouncements()) {\n'
            '\t\tfor(const auto &note : Music::takeAnnouncements())\n'
            '\t\t\tChat::callShowChatMessage(note, 6);\n'
            '\t}\n')
    return s


def lobby(s):
    return rep(s, '"/music [play|stop|pause|resume|next|vol N|list|status] - tracker music (see [music] in wkJellyWorm.ini)\\n"',
               '"/music [new|play|stop|pause|resume|next|vol N|list|cache|status] - tracker music, /music new = a new random track (see [music] in wkJellyWorm.ini)\\n"')


def cmake(s):
    return rep(s, 'src/Music.cpp src/Music.h ', 'src/Music.cpp src/Music.h src/MusicOnline.cpp src/MusicOnline.h ')


rw('src/Music.cpp', music)
rw('src/Music.h', header)
rw('src/FrameScheduler.cpp', frame)
rw('src/Lobby.cpp', lobby)
rw('CMakeLists.txt', cmake)
print('ok')

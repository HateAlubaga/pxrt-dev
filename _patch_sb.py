import shutil, os
ROOT = r'C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm\src'
CPP = os.path.join(ROOT, 'packages', 'PackageManager.cpp')
H = os.path.join(ROOT, 'packages', 'PackageManager.h')
LOBBY = os.path.join(ROOT, 'Lobby.cpp')
for p in (CPP, H, LOBBY):
    if not os.path.exists(p + '.bak_sb'):
        shutil.copy2(p, p + '.bak_sb')


def patch(path, old, new):
    s = open(path, encoding='utf-8', newline='').read()
    if '\r\n' in s:
        old, new = old.replace('\n', '\r\n'), new.replace('\n', '\r\n')
    assert s.count(old) == 1, (path, old[:60])
    s = s.replace(old, new)
    open(path, 'w', encoding='utf-8', newline='').write(s)


# header: members + declaration
patch(H, '\tstd::set<std::string> initializedPackages;\n',
      '\tstd::set<std::string> initializedPackages;\n'
      '\t// /sb: explicit set (name -> version) saved before the first bundle switch, restored by /sb off\n'
      '\tstd::map<std::string, std::string> sbSaved;\n'
      '\tbool sbActive = false;\n'
      '\tstd::string sbCurrent;\n')
patch(H, '\tint handleJpxCommand(void *lobbyObj, const std::string &args);\n',
      '\tint handleJpxCommand(void *lobbyObj, const std::string &args);\n'
      '\tint handleSbCommand(void *lobbyObj, const std::string &args);\n')

# scan: jelly\jpx and jelly\sborniki\jpx
patch(CPP, '''	std::error_code ec;
	if(!fs::is_directory(Config::jpxDir, ec)) {
		printf("scanJpxPackages: %s missing, skip\\n", Config::jpxDir.c_str());
		return;
	}
	for(const auto & entry : fs::recursive_directory_iterator(Config::jpxDir, ec)) {
		if(ec)
			break;
		if(!entry.is_regular_file())
			continue;
		if(entry.path().filename() == "manifest.json")
			addJpxPackage(entry.path().string());
	}
''', '''	for(const std::string dir : {Config::jpxDir, Config::jellyDir + "\\\\sborniki\\\\jpx"}) {
		std::error_code ec;
		if(!fs::is_directory(dir, ec)) {
			printf("scanJpxPackages: %s missing, skip\\n", dir.c_str());
			continue;
		}
		for(const auto & entry : fs::recursive_directory_iterator(dir, ec)) {
			if(ec)
				break;
			if(!entry.is_regular_file())
				continue;
			if(entry.path().filename() == "manifest.json")
				addJpxPackage(entry.path().string());
		}
	}
''')

SB = r'''
// /sb <words>: switch the lobby to exactly one scheme bundle (sbornik_*). Every explicitly enabled package is turned
// off, then each bundle dependency is enabled on its own, so missing ones are skipped and reported instead of
// blocking the whole bundle. /sb off brings back the set that was enabled before the first switch.
int PackageManager::handleSbCommand(void *lobbyObj, const std::string &args) {
	auto feedback = [&](const std::string &msg) {
		if(lobbyObj)
			Lobby::showGreenText(lobbyObj, (char *) msg.c_str());
		else
			notifyGameChat("wkJellyWorm: " + msg);
	};
	auto lower = [](std::string s) {
		std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return (char) std::tolower(c); });
		return s;
	};
	auto shortName = [](const std::string &n) {
		return n.rfind("sbornik_", 0) == 0 ? n.substr(8) : n;
	};
	auto latest = [&](const std::string &name) -> std::shared_ptr<Package> {
		std::shared_ptr<Package> pack;
		auto it = jpxAllversions.find(name);
		if(it == jpxAllversions.end())
			return pack;
		for(auto & p : it->second)
			if(!pack || versionLess(pack->getVersionstr(), p->getVersionstr()))
				pack = p;
		return pack;
	};
	auto refreshLobby = [&]() {
		if(lobbyObj) {
			handleLobbyListPackages(lobbyObj, false, true, true);
			Lobby::sendConfigString(lobbyObj);
		}
	};
	auto disableAllExplicit = [&]() {
		std::vector<std::string> names;
		for(auto & it : enabledPackagesExplicit)
			names.push_back(it.first);
		for(auto & n : names) {
			try { disablePackage(n, true); } catch(const std::exception &e) { printf("sb: %s\n", e.what()); }
		}
		checkDependenciesRemove();
	};

	std::vector<std::string> argsSplit;
	Utils::split_in_args(argsSplit, args);
	if(jpxAllversions.empty())
		scanJpxPackages();

	if(argsSplit.empty() || argsSplit[0] == "list" || argsSplit[0] == "ls") {
		std::stringstream ss;
		ss << "sb: " << jpxAllversions.size() << " bundles";
		if(sbActive)
			ss << ", active: " << shortName(sbCurrent);
		ss << " — /sb <part of name>, /sb off\n";
		size_t col = 0;
		for(auto & it : jpxAllversions) {
			std::string n = shortName(it.first);
			if(col && col + n.size() + 2 > 110) {
				ss << "\n";
				col = 0;
			}
			ss << n << "  ";
			col += n.size() + 2;
		}
		feedback(ss.str());
		return 1;
	}

	if(argsSplit[0] == "off") {
		if(!sbActive) {
			feedback("sb: no bundle active");
			return 1;
		}
		disableAllExplicit();
		std::vector<std::string> failed;
		for(auto & it : sbSaved) {
			try { enablePackage(it.first, it.second, true); } catch(const std::exception &) { failed.push_back(it.first); }
		}
		checkDependenciesAdd();
		ensureAllEnabledInitialized();
		std::string msg = "sb: " + shortName(sbCurrent) + " off, restored " + std::to_string(sbSaved.size() - failed.size()) + " package(s)";
		for(auto & f : failed)
			msg += "\n  failed: " + f;
		sbSaved.clear();
		sbActive = false;
		sbCurrent.clear();
		feedback(msg);
		refreshLobby();
		return 1;
	}

	// match: exact name, else every word (split on spaces and '_') found in that order
	std::string query;
	for(auto & a : argsSplit)
		query += (query.empty() ? "" : " ") + a;
	std::vector<std::string> words;
	{
		std::string w;
		for(char c : lower(query) + " ") {
			if(c == ' ' || c == '_') {
				if(!w.empty())
					words.push_back(w);
				w.clear();
			} else
				w += c;
		}
	}
	std::vector<std::string> hits;
	for(auto & it : jpxAllversions) {
		if(it.first == query || shortName(it.first) == query) {
			hits = {it.first};
			break;
		}
		std::string n = lower(it.first);
		size_t pos = 0;
		bool ok = true;
		for(auto & w : words) {
			size_t f = n.find(w, pos);
			if(f == std::string::npos) {
				ok = false;
				break;
			}
			pos = f + w.size();
		}
		if(ok)
			hits.push_back(it.first);
	}
	if(hits.size() != 1) {
		std::string msg = hits.empty() ? "sb: no bundle matches '" + query + "' (/sb list)"
		                               : "sb: '" + query + "' matches " + std::to_string(hits.size()) + ":";
		for(size_t i = 0; i < hits.size() && i < 15; i++)
			msg += "\n  " + shortName(hits[i]);
		if(hits.size() > 15)
			msg += "\n  ...";
		feedback(msg);
		return 1;
	}

	std::string name = hits[0];
	auto bundle = latest(name);
	if(!bundle) {
		feedback("sb: bundle " + name + " has no manifest");
		return 1;
	}
	if(!sbActive) {
		sbSaved.clear();
		for(auto & it : enabledPackagesExplicit)
			sbSaved[it.first] = it.second->getVersionstr();
		sbActive = true;
	}
	disableAllExplicit();
	std::vector<std::string> failed;
	size_t total = 0;
	for(std::string dep : bundle->getManifest()["dependencies"]) {
		total++;
		try {
			enablePackage(dep, "latest", true);
		} catch(const std::exception &) {
			failed.push_back(dep);
		}
	}
	checkDependenciesAdd();
	ensureAllEnabledInitialized();
	sbCurrent = name;
	std::string msg = "sb: " + shortName(name);
	if(!bundle->getDescription().empty())
		msg += " — " + bundle->getDescription();
	msg += "\n  enabled " + std::to_string(total - failed.size()) + "/" + std::to_string(total) + ", everything else off. /sb off restores";
	if(!failed.empty()) {
		msg += "\n  missing:";
		for(auto & f : failed)
			msg += " " + f;
	}
	feedback(msg);
	refreshLobby();
	return 1;
}

std::vector<std::string> PackageManager::listEnabledPackageIds() const {'''
patch(CPP, '\nstd::vector<std::string> PackageManager::listEnabledPackageIds() const {', SB)

patch(CPP, '''	if(command == "jpx") {
		return handleJpxCommand(lobbyObj, args);
	}
''', '''	if(command == "jpx") {
		return handleJpxCommand(lobbyObj, args);
	}
	if(command == "sb") {
		return handleSbCommand(lobbyObj, args);
	}
''')

s = open(LOBBY, encoding='utf-8', newline='').read()
i = s.index('"/jpx [list|enable')
j = s.index('\n', i) + 1
s = s[:j] + '\t\t\t"/sb [list|<part of name>|off] - play one PX bundle: only its packages on, everything else off\\n" \\\n' + s[j:]
open(LOBBY, 'w', encoding='utf-8', newline='').write(s)
print('ok')

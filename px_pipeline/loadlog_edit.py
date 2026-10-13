import os
os.chdir(r"C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm\src")

def rep(path, old, new):
    raw = open(path, "rb").read()
    crlf = b"\r\n" in raw
    s = raw.decode("utf-8").replace("\r\n", "\n")
    assert s.count(old) == 1, (path, old[:70], s.count(old))
    s = s.replace(old, new)
    if crlf:
        s = s.replace("\n", "\r\n")
    open(path, "wb").write(s.encode("utf-8"))

rep("packages/PackageManager.h", "\tstatic PackageManager & getInstance();\n",
"""\tstatic PackageManager & getInstance();
\t// Appends to jelly\\selftest.log; the first write of each process
\t// truncates it. Always on: it is the only record of which package was
\t// loading when WA died, and costs one small file write per package.
\tstatic void loadLog(const char *fmt, ...);
""")

rep("packages/PackageManager.cpp", """int PackageManager::applyAutostart() {
	int applied = 0;
	auto entries = readIniSection(kAutostartSection, Config::iniFile);
	if(Config::selfTestEnabled) {
		FILE *f = nullptr;
		if(fopen_s(&f, "jelly\\\\selftest.log", "a") == 0 && f) {
			fprintf(f, "autostart section '%s' from '%s': %d entr(ies)\\n",
				kAutostartSection, Config::iniFile.c_str(), (int)entries.size());
			int shown = 0;
			for(auto &kv : entries) {
				if(shown++ >= 5) break;
				fprintf(f, "  entry: '%s' = '%s'\\n", kv.first.c_str(), kv.second.c_str());
			}
			fclose(f);
		}
	}
""", """void PackageManager::loadLog(const char *fmt, ...) {
	static bool firstWriteThisProcess = true;
	FILE *f = nullptr;
	if(fopen_s(&f, "jelly\\\\selftest.log", firstWriteThisProcess ? "w" : "a") == 0 && f) {
		firstWriteThisProcess = false;
		va_list args;
		va_start(args, fmt);
		vfprintf(f, fmt, args);
		va_end(args);
		fclose(f);
	}
}

int PackageManager::applyAutostart() {
	int applied = 0;
	ULONGLONG startAll = GetTickCount64();
	auto entries = readIniSection(kAutostartSection, Config::iniFile);
	loadLog("autostart section '%s' from '%s': %d entr(ies)\\n",
		kAutostartSection, Config::iniFile.c_str(), (int)entries.size());
""")

rep("packages/PackageManager.cpp", """		if(Config::selfTestEnabled) {
			FILE *f = nullptr;
			if(fopen_s(&f, "jelly\\\\selftest.log", "a") == 0 && f) {
				fprintf(f, "loading %s\\n", name.c_str());
				fflush(f);
				fclose(f);
			}
		}
		try {
			enablePackage(name, version, true);
			checkDependenciesAdd();
			applied++;
		} catch(std::exception & e) {""", """		loadLog("loading %s\\n", name.c_str());
		ULONGLONG start = GetTickCount64();
		try {
			enablePackage(name, version, true);
			checkDependenciesAdd();
			applied++;
			loadLog("  %s: %llu ms\\n", name.c_str(), GetTickCount64() - start);
		} catch(std::exception & e) {""")

rep("packages/PackageManager.cpp", """			printf("applyAutostart(%s=%s): %s\\n", name.c_str(), value.c_str(), e.what());
			if(Config::selfTestEnabled) {
				FILE *f = nullptr;
				if(fopen_s(&f, "jelly\\\\selftest.log", "a") == 0 && f) {
					fprintf(f, "FAILED %s=%s: %s\\n", name.c_str(), value.c_str(), e.what());
					fclose(f);
				}
			}
		}
	}
	if(applied > 0 && gameInitialized)
		ensureAllEnabledInitialized();
	return applied;
}""", """			printf("applyAutostart(%s=%s): %s\\n", name.c_str(), value.c_str(), e.what());
			loadLog("FAILED %s=%s: %s\\n", name.c_str(), value.c_str(), e.what());
		}
	}
	if(applied > 0 && gameInitialized)
		ensureAllEnabledInitialized();
	loadLog("autostart: %d package(s) in %llu ms\\n", applied, GetTickCount64() - startAll);
	return applied;
}""")

rep("packages/PackageManager.cpp", """void PackageManager::ensureAllEnabledInitialized() {
	for(auto & package : enabledPackagesAll)
		ensurePackageInitialized(package.second);
}""", """void PackageManager::ensureAllEnabledInitialized() {
	ULONGLONG start = GetTickCount64();
	for(auto & package : enabledPackagesAll)
		ensurePackageInitialized(package.second);
	ULONGLONG spent = GetTickCount64() - start;
	if(spent >= 50)
		loadLog("initialize(): %d package(s) in %llu ms\\n", (int)enabledPackagesAll.size(), spent);
}""")

rep("dllmain.cpp", """		FILE *f = nullptr;
		if(fopen_s(&f, "jelly\\\\selftest.log", "w") == 0 && f) {
			fprintf(f, "selftest: loading [autostart] packages\\n");
			fclose(f);
		}
		int applied = PackageManager::getInstance().applyAutostart();
		f = nullptr;
		if(fopen_s(&f, "jelly\\\\selftest.log", "a") == 0 && f) {
			fprintf(f, "selftest: applied %d package(s)\\n", applied);
			fclose(f);
		}""", """		PackageManager::loadLog("selftest: loading [autostart] packages\\n");
		int applied = PackageManager::getInstance().applyAutostart();
		PackageManager::loadLog("selftest: applied %d package(s)\\n", applied);""")

rep("Lobby.cpp", """					FILE *f = nullptr;
					if(fopen_s(&f, "jelly\\\\selftest.log", "a") == 0 && f) {
						fprintf(f, "applyAutostart screen=%d applied=%d\\n", screen, applied);
						fclose(f);
					}""", """					PackageManager::loadLog("applyAutostart screen=%d applied=%d\\n", screen, applied);""")
print("ok")

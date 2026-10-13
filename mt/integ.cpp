// Integration test of Music.cpp (real libxmp + waveOut at volume 0 + real Mod Archive), game stubs only.
#include "Config.h"
#include "Music.h"

#include <chrono>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <functional>
#include <random>
#include <string>
#include <thread>

namespace fs = std::filesystem;

std::string Config::jellyDir, Config::musicCacheDir, Config::iniFile;

static int g_fail = 0;
#define CHECK(cond, ...)                                  \
	do {                                                  \
		if (cond) {                                       \
			printf("  ok   %s\n", #cond);                 \
		} else {                                          \
			printf("  FAIL %s  ", #cond);                 \
			printf(__VA_ARGS__);                          \
			printf("\n");                                 \
			++g_fail;                                     \
		}                                                 \
	} while (0)

static std::string cmd(const std::string &c) {
	std::string r = Music::handleCommand(c);
	printf("  > /music %s\n    %s\n", c.c_str(), r.c_str());
	return r;
}

static std::string status() { return Music::runCommand("status"); }  // handleCommand would swallow the queued announcements

static bool waitFor(int seconds, const std::function<bool()> &pred) {
	for (int i = 0; i < seconds * 10; ++i) {
		if (pred()) {
			return true;
		}
		std::this_thread::sleep_for(std::chrono::milliseconds(100));
	}
	return pred();
}

static std::string playingFile() {
	const std::string s = status();
	const auto p = s.find("playing: ");
	if (p == std::string::npos) {
		return "";
	}
	const auto e = s.find(" [", p);
	return s.substr(p + 9, e == std::string::npos ? std::string::npos : e - p - 9);
}

static bool contains(const std::string &s, const std::string &part) { return s.find(part) != std::string::npos; }

int main() {
	fs::remove_all("jtest");
	fs::create_directories("jtest/cache/music");
	fs::create_directories("jtest/music");
	Config::jellyDir = "jtest";
	Config::musicCacheDir = "jtest\\cache\\music";
	Config::iniFile = (fs::current_path() / "jtest" / "wk.ini").string();
	{
		std::ofstream ini(Config::iniFile);
		ini << "[music]\nEnabled=1\nAutoplayMatch=1\nAutoplayLobby=0\nVolume=0\nLoop=1\nShuffle=1\nRadio=1\n"
		       "Track=modarchive\nMaxSizeKB=3072\nCacheKeep=40\n";
	}
	Music::readConfig();

	printf("== idle\n");
	CHECK(contains(status(), "no music track"), "status=%s", status().c_str());
	CHECK(contains(cmd("cache"), "cache is empty"), "cache");
	CHECK(contains(cmd("mod abc"), "usage"), "mod usage");
	CHECK(contains(cmd("bogus"), "unknown /music command"), "unknown");

	printf("== /music mod 120691 (32 s tune), then radio must pick another one\n");
	CHECK(contains(cmd("mod 120691"), "fetching Mod Archive #120691"), "reply");
	CHECK(waitFor(25, [] { return contains(playingFile(), "intro-tune10"); }), "status=%s", status().c_str());
	{
		auto notes = Music::takeAnnouncements();
		CHECK(!notes.empty() && contains(notes.back(), "now playing intro-tune10.mod"), "notes=%zu %s", notes.size(), notes.empty() ? "" : notes.back().c_str());
		CHECK(!Music::hasAnnouncements(), "flag not cleared");
	}
	const auto t0 = std::chrono::steady_clock::now();
	CHECK(waitFor(70, [] { const auto f = playingFile(); return !f.empty() && !contains(f, "intro-tune10"); }), "radio did not switch, status=%s", status().c_str());
	printf("    radio switched after %lld s to %s\n",
	       (long long)std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - t0).count(), playingFile().c_str());
	{
		auto notes = Music::takeAnnouncements();
		CHECK(!notes.empty() && contains(notes.back(), "now playing"), "radio announce");
	}

	printf("== new / next (online next = new track)\n");
	std::string before = playingFile();
	cmd("new");
	CHECK(waitFor(25, [&] { const auto f = playingFile(); return !f.empty() && f != before; }), "new did not switch, status=%s", status().c_str());
	before = playingFile();
	cmd("next");
	CHECK(waitFor(25, [&] { const auto f = playingFile(); return !f.empty() && f != before; }), "next did not switch, status=%s", status().c_str());
	CHECK(contains(cmd("pause"), "paused") && contains(status(), "paused"), "pause");
	CHECK(contains(cmd("resume"), "resumed"), "resume");
	CHECK(contains(cmd("vol 0"), "volume 0%"), "vol");
	CHECK(contains(cmd("vol abc"), "usage"), "vol usage");
	CHECK(contains(cmd("mod 0"), "usage") && contains(cmd("mod 000"), "usage"), "mod 0 usage");

	printf("== a play command that fails keeps the current music\n");
	CHECK(contains(cmd("play jtest/does-not-exist.xm"), "music error"), "bad file reply");
	CHECK(contains(status(), "playing:"), "old music was dropped: %s", status().c_str());

	printf("== stop must not be undone by radio or autoplay\n");
	before = playingFile();
	CHECK(contains(cmd("stop"), "stopped"), "stop");
	Music::onMatchStart();
	std::this_thread::sleep_for(std::chrono::seconds(4));
	CHECK(contains(status(), "stopped:") && !contains(status(), "download in progress"), "status=%s", status().c_str());

	printf("== resume of an online track under Radio=1 must not loop (the radio has to advance)\n");
	CHECK(contains(cmd("resume"), "playing:"), "resume");
	CHECK(!contains(status(), " loop"), "online track loops: %s", status().c_str());
	cmd("stop");

	printf("== stop cancels a download that is in flight\n");
	cmd("new");
	CHECK(contains(cmd("stop"), "download cancelled"), "stop reply");
	std::this_thread::sleep_for(std::chrono::seconds(8));
	CHECK(!contains(status(), "playing:") && !contains(status(), "download in progress"), "status=%s", status().c_str());

	printf("== new after stop works again\n");
	cmd("new");
	CHECK(waitFor(25, [] { return !playingFile().empty(); }), "status=%s", status().c_str());

	printf("== match end (shutdown) while a download is in flight: nothing starts afterwards\n");
	cmd("new");
	Music::shutdown();
	std::this_thread::sleep_for(std::chrono::seconds(8));
	CHECK(contains(status(), "no music track"), "status=%s", status().c_str());
	CHECK(!Music::hasAnnouncements(), "stale announcements after shutdown");

	printf("== stop with nothing loaded cancels the first download too\n");
	cmd("new");
	CHECK(contains(cmd("stop"), "download cancelled"), "stop reply");
	std::this_thread::sleep_for(std::chrono::seconds(8));
	CHECK(contains(status(), "no music track"), "status=%s", status().c_str());
	CHECK(contains(cmd("stop"), "nothing loaded"), "stop with nothing");

	printf("== volume set while a download runs is used by the track\n");
	CHECK(contains(cmd("vol 1"), "volume 1%"), "vol preset");
	cmd("new");
	CHECK(waitFor(25, [] { return !playingFile().empty(); }), "status=%s", status().c_str());
	CHECK(contains(status(), "vol 1%"), "status=%s", status().c_str());
	cmd("vol 0");

	printf("== autoplay at match start: two calls, one download\n");
	Music::shutdown();
	Music::onMatchStart();
	Music::onMatchStart();
	CHECK(waitFor(25, [] { return !playingFile().empty(); }), "status=%s", status().c_str());
	std::this_thread::sleep_for(std::chrono::seconds(2));
	int cachedMa = 0;
	for (auto &e : fs::directory_iterator(Config::musicCacheDir)) {
		if (e.path().filename().string().rfind("ma", 0) == 0) {
			++cachedMa;
		}
	}
	printf("    files in cache: %d\n", cachedMa);

	printf("== cache folder as playlist\n");
	CHECK(contains(cmd("cache"), "cached tracks"), "cache list");
	cmd("play cache");
	CHECK(waitFor(10, [] { return contains(status(), "playing:") && contains(status(), "/"); }), "status=%s", status().c_str());
	printf("    %s\n", status().c_str());

	printf("== unknown / invalid Mod Archive id\n");
	cmd("mod 999999");
	CHECK(waitFor(15, [] { return Music::hasAnnouncements(); }), "no announcement");
	{
		auto notes = Music::takeAnnouncements();
		CHECK(!notes.empty() && contains(notes.back(), "no such module"), "notes=%s", notes.empty() ? "" : notes.back().c_str());
	}

	printf("== stress: commands, match end and radio at random while downloads run (no crash, no deadlock)\n");
	{
		std::mt19937 rng(777);
		const char *kinds[] = {"new", "stop", "next", "resume", "pause", "vol 0", "mod 120691", "play cache", "status", "cache"};
		int shutdowns = 0;
		for (int i = 0; i < 120; ++i) {
			const int pick = std::uniform_int_distribution<int>(0, 12)(rng);
			if (pick == 10) {
				Music::shutdown();
				++shutdowns;
			} else if (pick == 11) {
				Music::resetConfig();
			} else if (pick == 12) {
				Music::onMatchStart();
			} else {
				Music::runCommand(kinds[pick]);
			}
			Music::takeAnnouncements();
			std::this_thread::sleep_for(std::chrono::milliseconds(std::uniform_int_distribution<int>(0, 120)(rng)));
		}
		printf("    120 random operations done (%d match ends)\n", shutdowns);
		Music::shutdown();
		std::this_thread::sleep_for(std::chrono::seconds(12));  // every stale worker has finished by now
		CHECK(contains(status(), "no music track"), "status=%s", status().c_str());
	}

	Music::shutdown();
	std::this_thread::sleep_for(std::chrono::seconds(1));
	printf("\n%s (%d failures)\n", g_fail ? "FAILED" : "ALL OK", g_fail);
	return g_fail ? 1 : 0;
}

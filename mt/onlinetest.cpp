#include "MusicOnline.h"

#include <xmp.h>

#include <chrono>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <random>
#include <set>
#include <string>

namespace fs = std::filesystem;

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

// no .dl / .part temp file is left in the cache folder
static bool noTemp(const std::string &dir) {
	for (auto &e : fs::directory_iterator(dir)) {
		const std::string n = e.path().filename().string();
		const auto ends = [&](const std::string &suffix) {
			return n.size() >= suffix.size() && n.compare(n.size() - suffix.size(), suffix.size(), suffix) == 0;
		};
		if (ends(".dl") || ends(".part")) {
			return false;
		}
	}
	return true;
}

static void logger(const std::string &m) { printf("    log: %s\n", m.c_str()); }

static bool loadsInLibxmp(const std::string &path, std::string &info) {
	xmp_context ctx = xmp_create_context();
	const int ret = xmp_load_module(ctx, path.c_str());
	if (ret != 0) {
		xmp_free_context(ctx);
		info = "xmp_load_module=" + std::to_string(ret);
		return false;
	}
	xmp_module_info mi;
	xmp_get_module_info(ctx, &mi);
	char buf[256];
	snprintf(buf, sizeof(buf), "'%s' type=%s dur=%ds", mi.mod->name, mi.mod->type, mi.seq_data[0].duration / 1000);
	info = buf;
	// render a bit to prove it plays
	xmp_start_player(ctx, 44100, 0);
	static short pcm[44100];
	int r = xmp_play_buffer(ctx, pcm, sizeof(pcm), 1);
	xmp_end_player(ctx);
	xmp_release_module(ctx);
	xmp_free_context(ctx);
	if (r < 0) {
		info += " (play_buffer<0)";
	}
	return true;
}

int main() {
	const std::string cache = "testcache";
	std::error_code ec;
	fs::remove_all(cache, ec);
	fs::create_directories(cache, ec);

	printf("== sanitize\n");
	CHECK(MusicOnline::sanitizeFileName("Some Song (v2).XM") == "Some_Song__v2_.XM", "got %s", MusicOnline::sanitizeFileName("Some Song (v2).XM").c_str());
	CHECK(MusicOnline::sanitizeFileName("../../evil.mod") == ".._.._evil.mod" || MusicOnline::sanitizeFileName("../../evil.mod").find('/') == std::string::npos, "got %s", MusicOnline::sanitizeFileName("../../evil.mod").c_str());
	CHECK(MusicOnline::sanitizeFileName("").size() > 0, "empty");
	CHECK(MusicOnline::isTrackerExtension(".XM") && MusicOnline::isTrackerExtension(".mod") && !MusicOnline::isTrackerExtension(".mptm") && !MusicOnline::isTrackerExtension(".html"), "ext");

	printf("== invalid id\n");
	auto bad = MusicOnline::fetchModArchiveId(cache, 999999, 3 << 20, logger);
	CHECK(!bad.ok && bad.error == "no such module", "err='%s'", bad.error.c_str());
	CHECK(noTemp(cache), "leftover temp");

	printf("== known id + cache hit\n");
	auto t0 = std::chrono::steady_clock::now();
	auto a = MusicOnline::fetchModArchiveId(cache, 41529, 3 << 20, logger);
	auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
	CHECK(a.ok, "err='%s'", a.error.c_str());
	printf("    took %lld ms, path %s name %s\n", (long long)ms, a.path.c_str(), a.name.c_str());
	CHECK(a.ok && fs::file_size(a.path) == 224342, "size");
	CHECK(a.ok && fs::path(a.path).filename().string() == "ma41529_elektric_funk.mod", "file name %s", a.path.c_str());
	std::string info;
	CHECK(a.ok && loadsInLibxmp(a.path, info), "%s", info.c_str());
	printf("    %s\n", info.c_str());
	auto a2 = MusicOnline::fetchModArchiveId(cache, 41529, 3 << 20, logger);
	CHECK(a2.ok && a2.path == a.path, "cache hit");

	printf("== size cap\n");
	auto big = MusicOnline::fetchModArchiveId(cache, 150000, 100000, logger);
	CHECK(!big.ok && big.error.rfind("too big", 0) == 0, "err='%s'", big.error.c_str());
	CHECK(noTemp(cache), "leftover part");

	printf("== plain download keeps the query string, drops the fragment\n");
	auto r = MusicOnline::download("https://api.modarchive.org/downloads.php?moduleid=100000#frag.xm", cache + "/plain.bin", 3 << 20);
	CHECK(r.ok && fs::file_size(cache + "/plain.bin") == 63470, "ok=%d err=%s", r.ok, r.error.c_str());
	CHECK(r.fileName == "para_nerve.mod", "fn=%s", r.fileName.c_str());

	printf("== 404, bad host, bad scheme\n");
	auto r404 = MusicOnline::download("https://api.modarchive.org/definitely-not-here.mod", cache + "/x.bin", 1 << 20);
	CHECK(!r404.ok && r404.error.rfind("HTTP", 0) == 0, "err=%s", r404.error.c_str());
	t0 = std::chrono::steady_clock::now();
	auto rbad = MusicOnline::download("http://127.0.0.1:9/x.mod", cache + "/x.bin", 1 << 20);
	ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
	CHECK(!rbad.ok && rbad.error.rfind("request failed", 0) == 0, "err=%s", rbad.error.c_str());
	printf("    refused connection took %lld ms\n", (long long)ms);
	auto rscheme = MusicOnline::download("ftp://example.com/x.mod", cache + "/x.bin", 1 << 20);
	CHECK(!rscheme.ok, "ftp accepted");
	CHECK(!MusicOnline::download("not a url", cache + "/x.bin", 1 << 20).ok, "garbage accepted");
	CHECK(!fs::exists(cache + "/x.bin") && !fs::exists(cache + "/x.bin.part"), "leftover");

	printf("== random x6, every one must load in libxmp\n");
	std::mt19937 rng(12345);
	std::set<int> recent;
	int okCount = 0;
	for (int i = 0; i < 6; ++i) {
		t0 = std::chrono::steady_clock::now();
		auto f = MusicOnline::fetchRandomModArchive(cache, 215000, 3 << 20, 10, rng, [&](int id) { return recent.count(id) != 0; },
		                                            [] { return false; }, logger);
		ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
		if (!f.ok) {
			printf("  FAIL random #%d: %s\n", i, f.error.c_str());
			++g_fail;
			continue;
		}
		recent.insert(f.id);
		std::string li;
		const bool loads = loadsInLibxmp(f.path, li);
		printf("    #%d id=%d %s  %lld ms  %s%s\n", i, f.id, f.name.c_str(), (long long)ms, loads ? "" : "LOAD FAIL ", li.c_str());
		if (loads) {
			++okCount;
		} else {
			++g_fail;
		}
	}
	printf("    loaded %d/6\n", okCount);

	printf("== cancel\n");
	auto c = MusicOnline::fetchRandomModArchive(cache, 215000, 3 << 20, 10, rng, nullptr, [] { return true; }, logger);
	CHECK(!c.ok && c.error == "cancelled", "err=%s", c.error.c_str());

	printf("== prune\n");
	int before = 0;
	for (auto &e : fs::directory_iterator(cache)) {
		if (e.path().filename().string().rfind("ma", 0) == 0) {
			++before;
		}
	}
	std::ofstream(cache + "/abc123.mod") << "user file";
	std::ofstream(cache + "/old.xm.part") << "stale";
	fs::last_write_time(cache + "/old.xm.part", fs::file_time_type::clock::now() - std::chrono::hours(1));
	std::ofstream(cache + "/fresh.xm.part") << "in progress";
	int removed = MusicOnline::pruneCache(cache, 2);
	int after = 0;
	for (auto &e : fs::directory_iterator(cache)) {
		if (e.path().filename().string().rfind("ma", 0) == 0) {
			++after;
		}
	}
	printf("    ma files before=%d after=%d removed=%d\n", before, after, removed);
	CHECK(after == 2, "after=%d", after);
	CHECK(fs::exists(cache + "/abc123.mod"), "user file removed");
	CHECK(!fs::exists(cache + "/old.xm.part"), "stale part kept");
	CHECK(fs::exists(cache + "/fresh.xm.part"), "fresh part removed");

	printf("\n%s (%d failures)\n", g_fail ? "FAILED" : "ALL OK", g_fail);
	return g_fail ? 1 : 0;
}

// Offline reproduction of the wkJellyWorm tracker playback loop.
// mode "old": loop exactly as shipped in Music.cpp (header.dwFlags = 0; rendered==0 => end)
// mode "new": fixed loop. Output goes to a silent waveOut (volume 0) so nothing is audible.
#include <windows.h>
#include <mmsystem.h>
#include <xmp.h>
#include <cstdio>
#include <cstring>
#include <vector>
#include <string>

#pragma comment(lib, "winmm.lib")

static const int kSampleRate = 44100, kChannels = 2, kBufferFrames = 2048;
static const int kBufferBytes = kBufferFrames * kChannels * 2;

int main(int argc, char **argv) {
	if (argc < 3) { printf("usage: musictest old|new file\n"); return 2; }
	const bool fixedLoop = std::string(argv[1]) == "new";
	xmp_context ctx = xmp_create_context();
	if (xmp_load_module(ctx, argv[2]) != 0) { printf("load failed\n"); return 3; }
	xmp_module_info mi; xmp_get_module_info(ctx, &mi);
	printf("module '%s' type '%s' len=%d pat=%d ins=%d\n", mi.mod->name, mi.mod->type, mi.mod->len, mi.mod->pat, mi.mod->ins);
	if (xmp_start_player(ctx, kSampleRate, 0) != 0) { printf("start_player failed\n"); return 4; }

	WAVEFORMATEX f{};
	f.wFormatTag = WAVE_FORMAT_PCM; f.nChannels = kChannels; f.nSamplesPerSec = kSampleRate;
	f.wBitsPerSample = 16; f.nBlockAlign = kChannels * 2; f.nAvgBytesPerSec = f.nSamplesPerSec * f.nBlockAlign;
	HWAVEOUT wo = nullptr;
	if (waveOutOpen(&wo, WAVE_MAPPER, &f, 0, 0, CALLBACK_NULL) != MMSYSERR_NOERROR) { printf("waveOutOpen failed (no audio device?)\n"); return 5; }
	waveOutSetVolume(wo, 0); // silent test

	WAVEHDR h[2]{};
	std::vector<short> b[2] = {std::vector<short>(kBufferBytes / 2), std::vector<short>(kBufferBytes / 2)};
	for (int i = 0; i < 2; ++i) {
		h[i].lpData = (LPSTR)b[i].data(); h[i].dwBufferLength = kBufferBytes; h[i].dwFlags = 0;
		waveOutPrepareHeader(wo, &h[i], sizeof(WAVEHDR));
		MMRESULT r = waveOutWrite(wo, &h[i], sizeof(WAVEHDR));
		if (r) printf("initial write %d -> err %u\n", i, r);
	}

	int idx = 0, written = 0, writeErrors = 0, restarts = 0, nonzeroBuffers = 0;
	std::vector<short> prev;
	int identicalConsecutive = 0;
	DWORD t0 = GetTickCount();
	while (GetTickCount() - t0 < 4000) {
		WAVEHDR &hd = h[idx];
		while (!(hd.dwFlags & WHDR_DONE) && GetTickCount() - t0 < 4000) Sleep(2);
		if (!(hd.dwFlags & WHDR_DONE)) break;
		if (!fixedLoop) hd.dwFlags = 0; // original behaviour
		auto &pcm = b[idx];
		int ret = xmp_play_buffer(ctx, pcm.data(), (int)(pcm.size() * 2), 0);
		int rendered;
		if (!fixedLoop) {
			rendered = ret; // original: treats return value as "bytes rendered"
			if (rendered == 0) {
				++restarts;
				xmp_restart_module(ctx);
				rendered = xmp_play_buffer(ctx, pcm.data(), (int)(pcm.size() * 2), 0);
			}
			if (rendered > 0 && rendered < kBufferBytes) { memset((char *)pcm.data() + rendered, 0, kBufferBytes - rendered); rendered = kBufferBytes; }
		} else {
			if (ret < 0) { ++restarts; xmp_restart_module(ctx); xmp_play_buffer(ctx, nullptr, 0, 0); ret = xmp_play_buffer(ctx, pcm.data(), (int)(pcm.size() * 2), 0); }
			rendered = kBufferBytes;
		}
		bool nz = false; for (short s : pcm) if (s) { nz = true; break; }
		if (nz) ++nonzeroBuffers;
		if (!prev.empty() && prev == pcm) ++identicalConsecutive;
		prev = pcm;
		hd.dwBufferLength = rendered > 0 ? rendered : kBufferBytes;
		MMRESULT r = waveOutWrite(wo, &hd, sizeof(WAVEHDR));
		if (r) { if (++writeErrors <= 3) printf("waveOutWrite err %u (WAVERR_UNPREPARED=%u)\n", r, WAVERR_UNPREPARED); }
		else ++written;
		idx ^= 1;
		if (writeErrors > 3) break;
	}
	printf("mode=%s written=%d writeErrors=%d restarts=%d nonzeroBuffers=%d identicalConsecutive=%d\n", argv[1], written, writeErrors, restarts, nonzeroBuffers, identicalConsecutive);
	waveOutReset(wo);
	waveOutClose(wo);
	return 0;
}

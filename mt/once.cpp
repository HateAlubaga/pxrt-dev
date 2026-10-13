#include <xmp.h>
#include <cstdio>
#include <vector>
int main(int argc, char **argv) {
	xmp_context c = xmp_create_context();
	if (xmp_load_module(c, argv[1])) { printf("load fail\n"); return 1; }
	for (int loopArg = 0; loopArg <= 1; ++loopArg) {
		xmp_start_player(c, 44100, 0);
		std::vector<short> b(4096);
		int n = 0, ret = 0;
		while (n < 20000 && (ret = xmp_play_buffer(c, b.data(), 8192, loopArg)) == 0) ++n;
		printf("loopArg=%d buffers=%d lastRet=%d (%.1fs)\n", loopArg, n, ret, n * 2048 / 44100.0);
		xmp_end_player(c);
	}
	return 0;
}

#pragma once
namespace sol {
	template <class T> struct optional {
		bool has = false; T v{};
		T value_or(T d) const { return has ? v : d; }
	};
	struct state {
		template <class F> void set_function(const char *, F &&) {}
	};
}

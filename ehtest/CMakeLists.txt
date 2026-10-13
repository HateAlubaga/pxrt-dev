# Reproduces the 2026-10-10 WA crash (STATUS_INVALID_UNWIND_TARGET) outside the game:
# Lua -> native call (callRaw __try) -> "WA" code -> std::function hook -> nested Lua pcall -> fault.
# Build: cmake -S . -B b -A Win32 -DJW=<wkJellyWorm dir>; cmake --build b --config Release
cmake_minimum_required(VERSION 3.15)
project(ehtest CXX)
set(CMAKE_CXX_STANDARD 17)
set(JW "C:/Users/Admin/Projects/worms-modding-lab/sources/wkJellyWorm" CACHE PATH "wkJellyWorm source dir")
option(EHA "build with /EHa" OFF)
if(EHA)
  string(REPLACE "/EHsc" "/EHa" CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}")
endif()
foreach(v old new)
  add_executable(ehtest_${v} ehtest.cpp)
  target_include_directories(ehtest_${v} PRIVATE ${JW}/include)
  target_link_libraries(ehtest_${v} ${JW}/lib/lua53.lib)
  set_target_properties(ehtest_${v} PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreaded")
endforeach()
target_compile_definitions(ehtest_old PRIVATE OLD_CALLRAW=1)
target_include_directories(ehtest_old BEFORE PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/old_inc)

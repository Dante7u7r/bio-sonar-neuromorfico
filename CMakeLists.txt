cmake_minimum_required(VERSION 3.15)
project(bio_sonar_neuromorfico VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_options(/W3 /O2 /EHsc)
else()
    add_compile_options(-Wall -Wextra -O3 -pthread)
endif()

set(SOURCE_FILES
    main.cpp
    cerebro.cpp
    synthetic_signal_adapter.cpp
    audio_sonar_adapter.cpp
)

add_executable(bio_sonar ${SOURCE_FILES})

if(WIN32)
    target_link_libraries(bio_sonar PRIVATE ws2_32)
else()
    target_link_libraries(bio_sonar PRIVATE pthread)
endif()

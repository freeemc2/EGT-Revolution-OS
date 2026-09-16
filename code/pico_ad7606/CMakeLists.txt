cmake_minimum_required(VERSION 3.13)
include(pico_sdk_import.cmake)
project(pico_ad7606 C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(PICO_BOARD pico_w)
pico_sdk_init()

add_executable(pico_ad7606 main.c)
target_link_libraries(pico_ad7606 pico_stdlib hardware_spi)

pico_enable_stdio_usb(pico_ad7606 1)
pico_enable_stdio_uart(pico_ad7606 0)
pico_add_extra_outputs(pico_ad7606)   # produces the .uf2 for drag-drop flash

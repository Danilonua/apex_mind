#!/bin/bash

# Переходим в директорию проекта
cd "$(dirname "$0")/.."

# Установка целевой платформы
rustup target add armv7-unknown-linux-gnueabihf

# Компиляция через кросс-компилятор
cross build --release --target armv7-unknown-linux-gnueabihf

# Проверка существования файла
if [ -f "target/armv7-unknown-linux-gnueabihf/release/libwasi_security_layer.so" ]; then
    echo "Build successful! Output file:"
    du -h target/armv7-unknown-linux-gnueabihf/release/libwasi_security_layer.so
else
    echo "Build failed! Output file not found."
    exit 1
fi
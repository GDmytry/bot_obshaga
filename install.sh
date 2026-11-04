#!/usr/bin/env bash
# ==============================================================================
# Smart-Общага 502 — Скрипт автоматической установки для Armbian / Debian
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================================${NC}"
echo -e "${BLUE}   Smart-Общага 502 — Установка на Armbian / Linux    ${NC}"
echo -e "${BLUE}=====================================================${NC}"

# 1. Проверка прав sudo
if ! command -v sudo &> /dev/null; then
    echo -e "${RED}Ошибка: утилита sudo не найдена. Запустите скрипт из-под пользователя с правами sudo или установите sudo.${NC}"
    exit 1
fi

# 2. Обновление пакетов и установка зависимостей
echo -e "\n${YELLOW}[1/4] Обновление пакетов и установка Docker...${NC}"
sudo apt-get update
sudo apt-get install -y curl git

# Установка Docker и Compose (в Debian Bookworm пакет называется docker-compose-v2)
echo -e "${YELLOW}Установка Docker и Docker Compose...${NC}"
if ! sudo apt-get install -y docker.io docker-compose-v2; then
    if ! sudo apt-get install -y docker.io docker-compose-plugin; then
        sudo apt-get install -y docker.io docker-compose
    fi
fi

# 3. Настройка и запуск Docker службы
echo -e "\n${YELLOW}[2/4] Запуск и автозагрузка службы Docker...${NC}"
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER" 2>/dev/null || true

# 4. Создание файла .env при его отсутствии
echo -e "\n${YELLOW}[3/4] Проверка конфигурации .env...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}Создан файл .env из шаблона .env.example.${NC}"
else
    echo -e "${GREEN}Файл .env уже существует.${NC}"
fi

# 5. Определение локального IP-адреса сервера
SERVER_IP=$(hostname -I | awk '{print $1}')

echo -e "\n${GREEN}=====================================================${NC}"
echo -e "${GREEN}        ✅ Базовая установка завершена!             ${NC}"
echo -e "${GREEN}=====================================================${NC}"
echo -e "IP-адрес вашего сервера в сети: ${BLUE}http://${SERVER_IP}${NC}\n"

echo -e "Дальнейшие шаги:"
echo -e "1. Отредактируйте настройки в файле .env:"
echo -e "   ${YELLOW}nano .env${NC}"
echo -e "   (вставьте туда ваш BOT_TOKEN и ADMIN_IDS)\n"

echo -e "2. Запустите все сервисы командой:"
echo -e "   ${YELLOW}docker compose up -d --build${NC}\n"

echo -e "3. Для обхода блокировок Telegram в РФ:"
echo -e "   Откройте в браузере с компьютера: ${BLUE}http://${SERVER_IP}:2017${NC}"
echo -e "   Вставьте ваш VLESS/Shadowsocks ключ в v2rayA и нажмите Start.\n"

echo -e "4. Веб-дашборд комнаты будет доступен по адресу:"
echo -e "   ${BLUE}http://${SERVER_IP}:8000${NC}\n"

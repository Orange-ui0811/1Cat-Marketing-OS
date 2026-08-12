#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"
[ -f .env ] || { echo "尚未初始化。请先运行 ./bin/1cat init"; exit 1; }
password=$(sed -n 's/^INITIAL_ADMIN_PASSWORD=//p' .env)
[ -n "$password" ] || { echo "缺少首次登录密码"; exit 1; }
cd apps/workspace
npm ci
npx playwright install chromium
ONECAT_ADMIN_PASSWORD="$password" npm run e2e

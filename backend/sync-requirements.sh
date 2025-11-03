#!/bin/bash

# اسکریپت همگام‌سازی requirements.txt
# این اسکریپت requirements.txt را نصب می‌کند و سپس با نسخه‌های واقعی به‌روز می‌کند

set -e

# رنگ‌ها
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}همگام‌سازی requirements.txt${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# بررسی وجود virtual environment
if [ -z "$VIRTUAL_ENV" ] && [ -d "venv" ]; then
    echo -e "${YELLOW}فعال‌سازی virtual environment...${NC}"
    source venv/bin/activate
fi

if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}⚠️  هشدار: virtual environment فعال نیست!${NC}"
    echo -e "${YELLOW}آیا می‌خواهید ادامه دهید؟ (y/n)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# مرحله 1: نصب requirements.txt
echo -e "${BLUE}📦 مرحله 1: نصب پکیج‌ها از requirements.txt...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo -e "${GREEN}✅ نصب پکیج‌ها با موفقیت انجام شد${NC}"
echo ""

# مرحله 2: به‌روزرسانی requirements.txt
echo -e "${BLUE}🔄 مرحله 2: به‌روزرسانی requirements.txt با نسخه‌های واقعی...${NC}"

# ایجاد backup
BACKUP_FILE="requirements.txt.backup.$(date +%Y%m%d_%H%M%S)"
cp requirements.txt "$BACKUP_FILE"
echo -e "${YELLOW}💾 Backup ایجاد شد: $BACKUP_FILE${NC}"

# اجرای اسکریپت Python
python3 sync_requirements.py

echo ""
echo -e "${GREEN}✅ همگام‌سازی کامل شد!${NC}"
echo -e "${BLUE}💡 می‌توانید requirements.txt را commit کنید${NC}"


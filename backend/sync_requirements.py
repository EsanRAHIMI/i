#!/usr/bin/env python3
"""
اسکریپت همگام‌سازی requirements.txt با پکیج‌های واقعاً نصب شده

این اسکریپت:
1. requirements.txt را نصب می‌کند
2. نسخه‌های واقعاً نصب شده را پیدا می‌کند
3. requirements.txt را با نسخه‌های واقعی به‌روز می‌کند
4. فقط پکیج‌های اصلی را نگه می‌دارد (وابستگی‌های فرعی را اضافه نمی‌کند)
"""

import subprocess
import re
import sys
from pathlib import Path
from typing import Dict, Optional, List, Tuple

def run_command(cmd: List[str], check: bool = True) -> Tuple[str, str, int]:
    """اجرای یک دستور و برگرداندن خروجی."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr, e.returncode

def get_installed_version(package_name: str) -> Optional[str]:
    """نسخه نصب شده یک پکیج را برمی‌گرداند."""
    stdout, stderr, code = run_command(
        [sys.executable, "-m", "pip", "show", package_name],
        check=False
    )
    if code != 0:
        return None
    
    for line in stdout.split('\n'):
        if line.startswith('Version:'):
            return line.split(':', 1)[1].strip()
    return None

def normalize_package_name(name: str) -> str:
    """نام پکیج را نرمالایز می‌کند."""
    # حذف [extras]
    name = re.sub(r'\[.*?\]', '', name).strip()
    return name.lower().replace('-', '_').replace('.', '-')

def parse_requirements_line(line: str) -> Tuple[Optional[str], Optional[str], str]:
    """
    یک خط از requirements.txt را پارس می‌کند.
    
    Returns:
        (package_name, version_spec, original_line)
    """
    original = line.strip()
    
    # نادیده گرفتن کامنت‌ها و خطوط خالی
    if not original or original.startswith('#'):
        return None, None, original
    
    # نادیده گرفتن فلگ‌ها
    if original.startswith('-'):
        return None, None, original
    
    # حذف کامنت inline
    if '#' in original:
        original = original.split('#')[0].strip()
    
    # پارس کردن نام و نسخه
    # فرمت‌ها: package==1.0.0, package>=1.0.0, package<2.0.0
    match = re.match(r'^([a-zA-Z0-9_-]+(?:\[[^\]]+\])?)(.*)$', original)
    if not match:
        return None, None, original
    
    package_name = match.group(1)
    rest = match.group(2).strip()
    
    # استخراج نام اصلی (بدون [extras])
    base_name = re.sub(r'\[.*?\]', '', package_name).strip()
    
    # استخراج version spec
    version_spec = None
    if rest:
        # اگر version spec دارد
        version_match = re.match(r'^(==|>=|<=|~=|!=|<|>)(.+)$', rest)
        if version_match:
            version_spec = rest
    else:
        # بدون version spec
        version_spec = None
    
    return base_name, version_spec, original

def install_requirements(requirements_file: Path) -> bool:
    """نصب requirements.txt"""
    print("📦 در حال نصب پکیج‌ها از requirements.txt...")
    stdout, stderr, code = run_command(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
        check=False
    )
    
    if code != 0:
        print(f"❌ خطا در نصب پکیج‌ها:")
        print(stderr)
        return False
    
    print("✅ نصب پکیج‌ها با موفقیت انجام شد")
    return True

def update_requirements_file(requirements_file: Path) -> bool:
    """به‌روزرسانی requirements.txt با نسخه‌های واقعاً نصب شده"""
    
    print("\n🔍 در حال خواندن requirements.txt...")
    
    if not requirements_file.exists():
        print(f"❌ فایل {requirements_file} پیدا نشد!")
        return False
    
    # خواندن فایل فعلی
    with open(requirements_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    updated_lines = []
    updated_count = 0
    not_found = []
    
    print("\n🔄 به‌روزرسانی نسخه‌های پکیج‌ها...")
    
    for line in lines:
        package_name, version_spec, original = parse_requirements_line(line)
        
        # اگر خط قابل پارس نیست (کامنت، فلگ، و غیره)، بدون تغییر نگه دار
        if package_name is None:
            updated_lines.append(line)
            continue
        
        # دریافت نسخه واقعی نصب شده
        installed_version = get_installed_version(package_name)
        
        if installed_version is None:
            print(f"   ⚠️  {package_name}: نصب نشده است")
            not_found.append(package_name)
            # خط را نگه دار (شاید بعداً نصب شود)
            updated_lines.append(line)
        else:
            # اگر نسخه تغییر کرده، به‌روزرسانی کن
            if version_spec and '==' in version_spec:
                old_version = version_spec.replace('==', '').strip()
                if old_version != installed_version:
                    # به‌روزرسانی نسخه
                    new_line = line.replace(f'=={old_version}', f'=={installed_version}')
                    updated_lines.append(new_line)
                    print(f"   ✏️  {package_name}: {old_version} → {installed_version}")
                    updated_count += 1
                else:
                    updated_lines.append(line)
            elif version_spec:
                # اگر محدودیت دیگری دارد (>=, <=, و غیره)، فقط نسخه را اضافه کن
                # اما فعلاً محدودیت را نگه دار
                updated_lines.append(line)
            else:
                # بدون نسخه بود، حالا اضافه کن
                base_line = original.split()[0]  # نام پکیج
                new_line = f"{base_line}=={installed_version}\n"
                updated_lines.append(new_line)
                print(f"   ➕ {package_name}: =={installed_version} (اضافه شد)")
                updated_count += 1
    
    # نوشتن فایل به‌روز شده
    if updated_count > 0 or not_found:
        backup_file = requirements_file.with_suffix('.txt.backup')
        print(f"\n💾 ایجاد backup: {backup_file}")
        
        # ذخیره backup
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        # نوشتن فایل جدید
        with open(requirements_file, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        
        print(f"✅ requirements.txt به‌روزرسانی شد!")
        print(f"   • {updated_count} پکیج به‌روزرسانی شد")
        if not_found:
            print(f"   • ⚠️  {len(not_found)} پکیج نصب نشده بودند")
        print(f"   • Backup در {backup_file} ذخیره شد")
        return True
    else:
        print("\n✅ همه نسخه‌ها قبلاً به‌روز بودند!")
        return False

def main():
    """تابع اصلی"""
    backend_dir = Path(__file__).parent
    requirements_file = backend_dir / "requirements.txt"
    
    print("=" * 80)
    print("🔄 همگام‌سازی requirements.txt با پکیج‌های نصب شده")
    print("=" * 80)
    print()
    
    # مرحله 1: نصب requirements.txt
    if not install_requirements(requirements_file):
        print("\n❌ عملیات نصب ناموفق بود!")
        sys.exit(1)
    
    # مرحله 2: به‌روزرسانی requirements.txt
    update_result = update_requirements_file(requirements_file)
    
    print("\n" + "=" * 80)
    print("✅ همگام‌سازی با موفقیت انجام شد!")
    print("=" * 80)
    
    if update_result:
        print("\n💡 نکته: فایل backup ایجاد شد. در صورت نیاز می‌توانید آن را بازیابی کنید.")
        print("\n📦 اکنون می‌توانید requirements.txt را commit کنید.")
    else:
        print("\n💡 همه نسخه‌ها قبلاً به‌روز بودند - نیازی به تغییر نیست!")

if __name__ == "__main__":
    main()


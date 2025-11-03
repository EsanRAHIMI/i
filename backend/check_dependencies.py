#!/usr/bin/env python3
"""
اسکریپت مقایسه پکیج‌های نصب شده با requirements.txt

این اسکریپت:
1. لیست پکیج‌های نصب شده در محیط را می‌خواند
2. requirements.txt را پارس می‌کند
3. اختلافات نسخه‌ها را پیدا می‌کند
4. پکیج‌های اضافی یا گم‌شده را نشان می‌دهد
"""

import subprocess
import re
import sys
from pathlib import Path
from typing import Dict, Set, Tuple, Optional

def get_installed_packages() -> Dict[str, str]:
    """لیست پکیج‌های نصب شده را برمی‌گرداند."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            capture_output=True,
            text=True,
            check=True
        )
        packages = {}
        for line in result.stdout.strip().split('\n'):
            if '==' in line:
                name, version = line.split('==', 1)
                packages[name.lower()] = version
        return packages
    except subprocess.CalledProcessError as e:
        print(f"❌ خطا در خواندن پکیج‌های نصب شده: {e}")
        return {}

def parse_requirements(requirements_file: str) -> Dict[str, Optional[str]]:
    """
    requirements.txt را پارس می‌کند و نام و نسخه پکیج‌ها را برمی‌گرداند.
    
    Returns:
        Dict با کلید نام پکیج و مقدار نسخه (یا None برای بدون نسخه)
    """
    packages = {}
    requirements_path = Path(requirements_file)
    
    if not requirements_path.exists():
        print(f"❌ فایل {requirements_file} پیدا نشد!")
        return packages
    
    with open(requirements_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # نادیده گرفتن کامنت‌ها و خطوط خالی
            if not line or line.startswith('#'):
                continue
            
            # نادیده گرفتن --extra-index-url و سایر فلگ‌ها
            if line.startswith('-'):
                continue
            
            # حذف کامنت‌های inline
            if '#' in line:
                line = line.split('#')[0].strip()
            
            # پارس کردن نام و نسخه
            # فرمت‌های مختلف: package==1.0.0, package>=1.0.0, package<2.0.0, package~=1.0.0
            match = re.match(r'^([a-zA-Z0-9_-]+(?:\[[^\]]+\])?)(?:==|>=|<=|~=|!=|<|>)(.+)$', line)
            if match:
                package_name = match.group(1).lower()
                # حذف [extras] از نام
                package_name = re.sub(r'\[.*?\]', '', package_name)
                version_spec = match.group(2).strip()
                packages[package_name] = version_spec
            else:
                # پکیج بدون نسخه
                package_name = line.split()[0].lower()
                package_name = re.sub(r'\[.*?\]', '', package_name)
                packages[package_name] = None
    
    return packages

def normalize_package_name(name: str) -> str:
    """نام پکیج را نرمالایز می‌کند (تبدیل - به _ و غیره)."""
    # در Python، نام‌های پکیج معمولاً case-insensitive هستند
    # و - و _ یکسان هستند
    return name.lower().replace('-', '_').replace('.', '-')

def compare_packages(
    installed: Dict[str, str],
    requirements: Dict[str, Optional[str]]
) -> Tuple[Dict[str, Tuple[str, str]], Set[str], Set[str], Dict[str, str]]:
    """
    مقایسه پکیج‌های نصب شده با requirements.
    
    Returns:
        Tuple of:
        - version_mismatches: Dict[name, (installed_version, required_version)]
        - missing: Set of missing package names
        - extra: Set of extra installed packages
        - matching: Dict of matching packages
    """
    version_mismatches = {}
    missing = set()
    extra = set(installed.keys())
    matching = {}
    
    # Normalize installed packages names
    installed_normalized = {}
    for name, version in installed.items():
        normalized = normalize_package_name(name)
        installed_normalized[normalized] = version
    
    for req_name, req_version in requirements.items():
        req_normalized = normalize_package_name(req_name)
        
        if req_normalized not in installed_normalized:
            missing.add(req_name)
            continue
        
        extra.discard(req_normalized)
        inst_version = installed_normalized[req_normalized]
        
        if req_version:
            # مقایسه نسخه‌ها
            # اگر req_version یک محدودیت است (>=, <=, <, >) بررسی می‌کنیم
            if '==' in req_version:
                required = req_version.replace('==', '')
                if inst_version != required:
                    version_mismatches[req_name] = (inst_version, required)
                else:
                    matching[req_name] = inst_version
            elif req_version.startswith('>=') or req_version.startswith('<='):
                # برای >= و <= فقط هشدار می‌دهیم
                matching[req_name] = inst_version
            else:
                # سایر محدودیت‌ها
                matching[req_name] = inst_version
        else:
            matching[req_name] = inst_version
    
    # حذف پکیج‌های استاندارد از extra
    stdlib_packages = {
        'pip', 'setuptools', 'wheel', 'distutils'
    }
    extra = {p for p in extra if p not in stdlib_packages}
    
    return version_mismatches, missing, extra, matching

def print_report(
    version_mismatches: Dict[str, Tuple[str, str]],
    missing: Set[str],
    extra: Set[str],
    matching: Dict[str, str]
):
    """گزارش اختلافات را چاپ می‌کند."""
    print("=" * 80)
    print("📦 گزارش مقایسه پکیج‌های نصب شده با requirements.txt")
    print("=" * 80)
    print()
    
    # پکیج‌های مطابق
    print(f"✅ پکیج‌های مطابق ({len(matching)}):")
    if matching:
        for name, version in sorted(matching.items())[:10]:  # فقط 10 تا اول
            print(f"   • {name}=={version}")
        if len(matching) > 10:
            print(f"   ... و {len(matching) - 10} پکیج دیگر")
    print()
    
    # عدم تطابق نسخه‌ها
    if version_mismatches:
        print(f"⚠️  عدم تطابق نسخه ({len(version_mismatches)}):")
        for name, (installed, required) in sorted(version_mismatches.items()):
            print(f"   • {name}:")
            print(f"     - نصب شده: {installed}")
            print(f"     - مورد نیاز: {required}")
        print()
    else:
        print("✅ همه نسخه‌ها مطابق هستند!")
        print()
    
    # پکیج‌های گم‌شده
    if missing:
        print(f"❌ پکیج‌های گم‌شده ({len(missing)}):")
        for name in sorted(missing):
            print(f"   • {name}")
        print()
    else:
        print("✅ همه پکیج‌های مورد نیاز نصب هستند!")
        print()
    
    # پکیج‌های اضافی
    if extra:
        print(f"ℹ️  پکیج‌های اضافی نصب شده ({len(extra)}):")
        for name in sorted(extra)[:20]:  # فقط 20 تا اول
            print(f"   • {name}")
        if len(extra) > 20:
            print(f"   ... و {len(extra) - 20} پکیج دیگر")
        print()
    else:
        print("✅ هیچ پکیج اضافی وجود ندارد!")
        print()
    
    # خلاصه
    print("=" * 80)
    print("📊 خلاصه:")
    print(f"   • مطابق: {len(matching)}")
    print(f"   • عدم تطابق نسخه: {len(version_mismatches)}")
    print(f"   • گم‌شده: {len(missing)}")
    print(f"   • اضافی: {len(extra)}")
    print("=" * 80)

def main():
    """تابع اصلی."""
    backend_dir = Path(__file__).parent
    requirements_file = backend_dir / "requirements.txt"
    
    print(f"🔍 بررسی پکیج‌های نصب شده در محیط Python...")
    print(f"📄 خواندن requirements.txt از: {requirements_file}")
    print()
    
    # خواندن پکیج‌های نصب شده
    installed = get_installed_packages()
    if not installed:
        print("❌ هیچ پکیجی پیدا نشد. مطمئن شوید که در یک محیط مجازی فعال هستید.")
        sys.exit(1)
    
    print(f"✅ {len(installed)} پکیج نصب شده پیدا شد")
    
    # پارس کردن requirements.txt
    requirements = parse_requirements(str(requirements_file))
    print(f"✅ {len(requirements)} پکیج از requirements.txt پارس شد")
    print()
    
    # مقایسه
    version_mismatches, missing, extra, matching = compare_packages(
        installed, requirements
    )
    
    # چاپ گزارش
    print_report(version_mismatches, missing, extra, matching)
    
    # خروجی با کد خطا در صورت وجود مشکل
    if version_mismatches or missing:
        print("\n⚠️  هشدار: اختلافاتی پیدا شد!")
        sys.exit(1)
    else:
        print("\n✅ همه چیز خوب است!")
        sys.exit(0)

if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from system_info import get_system_info, get_critical_packages
from updates import get_updates, install_updates
from failed_logins import get_failed_logins
from reporter import generate_report
from package_utils import get_installed_packages_with_versions
from nvd_analyzer import check_cve_for_packages

def main():
    parser = argparse.ArgumentParser(description='Аудит безопасности Linux')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Автоматически устанавливать обновления без подтверждения')
    parser.add_argument('--no-update', action='store_true',
                        help='Пропустить установку обновлений (только проверка)')
    parser.add_argument('--cve', action='store_true',
                        help='Проверить все установленные пакеты на наличие известных уязвимостей (CVE) через NVD API')
    parser.add_argument('--quick', action='store_true',
                        help='При проверке CVE проверять только критические пакеты (быстрее)')
    parser.add_argument('--refresh-cache', action='store_true',
                        help='Принудительно обновить кэш CVE (игнорировать сохранённые данные)')
    args = parser.parse_args()

    print("Начинаем аудит безопасности...")

    sys_info = get_system_info(interface='eth0')

    updates = get_updates()
    if updates is None:
        print("Ошибка определения менеджера пакетов.", file=sys.stderr)
        sys.exit(1)

    installed_pkgs = []
    if updates:
        print(f"Найдено {len(updates)} доступных обновлений.")
        if not args.no_update:
            if args.yes:
                print("Устанавливаем все обновления (флаг --yes)...")
                installed_pkgs = install_updates(updates, auto_yes=True)
            else:
                response = input("Установить все обновления? (y/n): ").strip().lower()
                if response in ('y', 'yes'):
                    installed_pkgs = install_updates(updates, auto_yes=False)
                else:
                    print("Установка пропущена.")
    else:
        print("Нет доступных обновлений.")

    cve_data = {}
    packages_to_check = {}
    success_count = 0
    packages_to_check_count = 0

    if args.cve:
        all_packages_with_versions = get_installed_packages_with_versions()
        if all_packages_with_versions is None:
            print("Ошибка получения списка пакетов.", file=sys.stderr)
            sys.exit(1)
        elif not all_packages_with_versions:
            print("Список установленных пакетов пуст.")
        else:
            if args.quick:
                print("Используем режим 'быстрой' проверки (только критические пакеты).")
                critical_list = set(get_critical_packages())
                packages_to_check = {pkg: ver for pkg, ver in all_packages_with_versions.items() if pkg in critical_list}
                if not packages_to_check:
                    print("Ни один из критических пакетов не установлен.")
                else:
                    print(f"Найдено {len(packages_to_check)} критических пакетов для проверки.")
            else:
                packages_to_check = all_packages_with_versions
                print(f"Найдено {len(packages_to_check)} установленных пакетов.")

    if packages_to_check:
        print("Проверка пакетов на уязвимости через NVD API...")
        cve_data, success_count = check_cve_for_packages(
            packages_to_check,
            timeout=90,
            max_workers=2,
            retries=7
        )
        if cve_data:
            print(f"Найдены уязвимости для {len(cve_data)} пакетов.")
        else:
            print("Уязвимостей не найдено или ошибка API.")
        packages_to_check_count = len(packages_to_check)
    else:
        if args.cve:
            print("Нет пакетов для проверки CVE.")

    failed = get_failed_logins()
    if failed is None:
        print("Не удалось прочитать лог-файл (возможно, нет прав).")
        failed = {}

    data = {
        'system': sys_info,
        'updates_available': updates if updates else [],
        'updates_installed': installed_pkgs,
        'failed_logins': dict(failed),
        'cve': cve_data,
        'cve_checked_count': packages_to_check_count,
        'cve_success_count': success_count,
        'cve_source': 'NVD NIST'
    }

    generate_report(data)
    print("Аудит завершён.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
from datetime import datetime

try:
    from modules import linux_audit
except ImportError:
    print("Ошибка: модуль linux_audit не найден.", file=sys.stderr)
    sys.exit(1)

def generate_report(data, output_dir='reports'):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_name = f"audit_report_{timestamp}"

    txt_path = os.path.join(output_dir, base_name + '.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        sysinfo = data.get('system', {})
        f.write("="*60 + "\n")
        f.write("         ОТЧЁТ ПО ИНФОРМАЦИОННОЙ БЕЗОПАСНОСТИ\n")
        f.write("="*60 + "\n\n")
        f.write(f"Дата:          {sysinfo.get('timestamp', 'N/A')}\n")
        f.write(f"Имя хоста:     {sysinfo.get('hostname', 'N/A')}\n")
        f.write(f"Тип ОС:        {sysinfo.get('os_name', 'N/A')}\n")
        f.write(f"Версия ОС:     {sysinfo.get('os_version', 'N/A')}\n")
        f.write(f"Версия ядра:   {sysinfo.get('kernel', 'N/A')}\n")
        f.write(f"Серийный N:    {sysinfo.get('serial', 'N/A')}\n")
        f.write(f"MAC-адрес:     {sysinfo.get('mac', 'N/A')}\n")
        f.write(f"IP-адрес:      {sysinfo.get('ip', 'N/A')}\n")
        f.write(f"Machine ID:    {sysinfo.get('machine_id', 'N/A')}\n")
        f.write("\n")

        # ---------- ОБНОВЛЕНИЯ ----------
        f.write("--- ОБНОВЛЕНИЯ ---\n")
        available = data.get('updates_available', [])
        installed = data.get('updates_installed', [])
        if available:
            f.write(f"Доступно обновлений: {len(available)}\n")
            for pkg in available:
                f.write(f"  - {pkg}\n")
            if installed:
                f.write(f"\nУстановлено обновлений: {len(installed)}\n")
                for pkg in installed:
                    f.write(f"  + {pkg}\n")
            else:
                f.write("\nОбновления не устанавливались.\n")
        else:
            f.write("Доступных обновлений не найдено.\n")
        f.write("\n")

        # ---------- УЯЗВИМОСТИ (CVE) ----------
        cve_data = data.get('cve', {})
        total_checked = data.get('cve_checked_count', 0)
        success_checked = data.get('cve_success_count', 0)
        updates_available = set(available)

        if cve_data or total_checked > 0:
            f.write("--- УЯЗВИМОСТИ (CVE) ---\n")
            f.write(f"Всего пакетов в проверке: {total_checked}\n")
            f.write(f"Успешно проверено: {success_checked}\n")
            if total_checked > success_checked:
                f.write(f"Ошибок при проверке: {total_checked - success_checked}\n")

            if cve_data:
                total_cves = 0
                fixable_cves = 0
                fixable_packages = set()
                for pkg, cves in cve_data.items():
                    for cve in cves:
                        if 'error' not in cve:
                            total_cves += 1
                            if pkg in updates_available:
                                fixable_cves += 1
                                fixable_packages.add(pkg)

                f.write(f"Всего найдено уязвимостей (соответствующих версии): {total_cves}\n")
                if fixable_cves > 0:
                    f.write(f"Из них могут быть устранены обновлением: {fixable_cves}\n")
                    f.write(f"Пакеты, доступные для обновления: {', '.join(sorted(fixable_packages))}\n")
                else:
                    f.write("Ни одна из найденных уязвимостей не может быть устранена обновлением.\n")

                f.write("\n--- Детали по пакетам ---\n")
                for pkg, cves in cve_data.items():
                    # Фильтруем только реальные CVE (не ошибки)
                    real_cves = [cve for cve in cves if 'error' not in cve]
                    errors = [cve for cve in cves if 'error' in cve]
                    if real_cves:
                        # Формируем строку с CVE ID и CVSS
                        cve_list = []
                        for cve in real_cves:
                            cve_id = cve.get('id', 'N/A')
                            cvss = cve.get('cvss_score', 'N/A')
                            cve_list.append(f"{cve_id} (CVSS: {cvss})")
                        cve_line = ", ".join(cve_list)
                        f.write(f"Пакет: {pkg} (найдено: {len(real_cves)} уязвимостей)\n")
                        f.write(f"  {cve_line}\n")
                        # Рекомендация для пакета
                        if pkg in updates_available:
                            f.write(f"  Рекомендация: найдены обновления для этого пакета. "
                                    f"Рекомендуется обновиться до актуальной версии.\n")
                        else:
                            f.write(f"  Рекомендация: обновлений для этого пакета не найдено. "
                                    f"Рекомендуется проверить наличие патча в репозитории или применить временные меры.\n")
                        f.write("\n")
                    # Если есть ошибки, выводим их отдельно
                    if errors:
                        f.write(f"Пакет: {pkg} (ошибки при проверке)\n")
                        for err in errors:
                            f.write(f"  Ошибка: {err['error']}\n")
                        f.write("\n")
            else:
                f.write("Уязвимостей не найдено.\n")
        else:
            f.write("--- УЯЗВИМОСТИ (CVE) ---\n")
            f.write("Проверка CVE не выполнялась.\n")

        f.write("\n")

        # ---------- НЕУДАЧНЫЕ ПОПЫТКИ ВХОДА ----------
        f.write("--- НЕУДАЧНЫЕ ПОПЫТКИ ВХОДА ---\n")
        logins = data.get('failed_logins', {})
        if logins:
            for ip, count in sorted(logins.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{ip:20} {count} раз(а)\n")
            f.write(f"Всего IP: {len(logins)}\n")
        else:
            f.write("Неудачных попыток не обнаружено.\n")

        # ---------- ПОДПИСЬ ----------
        f.write("\n" + "="*60 + "\n")
        f.write(f"Должность:               Специалист по информационной безопасности\n")
        f.write(f"Подпись:                 \n")
        f.write(f"ФИО:                     Илья Тришкин\n")
        f.write(f"Дата подписания:         {datetime.now().strftime('%d.%m.%Y')}\n")
        f.write("="*60 + "\n")

    # ---------- JSON-отчёт ----------
    json_path = os.path.join(output_dir, base_name + '.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"Отчёт сохранён: {txt_path}")
    print(f"JSON-отчёт сохранён: {json_path}")

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
    args = parser.parse_args()

    print("Начинаем аудит безопасности...")

    sys_info = linux_audit.get_system_info(interface='eth0')

    updates = linux_audit.get_updates()
    if updates is None:
        print("Ошибка определения менеджера пакетов.", file=sys.stderr)
        sys.exit(1)

    installed_pkgs = []
    if updates:
        print(f"Найдено {len(updates)} доступных обновлений.")
        if not args.no_update:
            if args.yes:
                print("Устанавливаем все обновления (флаг --yes)...")
                installed_pkgs = linux_audit.install_updates(updates, auto_yes=True)
            else:
                response = input("Установить все обновления? (y/n): ").strip().lower()
                if response in ('y', 'yes'):
                    installed_pkgs = linux_audit.install_updates(updates, auto_yes=False)
                else:
                    print("Установка пропущена.")
    else:
        print("Нет доступных обновлений.")

    cve_data = {}
    packages_to_check = {}
    success_count = 0
    packages_to_check_count = 0

    if args.cve:
        all_packages_with_versions = linux_audit.get_installed_packages_with_versions()
        if all_packages_with_versions is None:
            print("Ошибка получения списка пакетов.", file=sys.stderr)
            sys.exit(1)
        elif not all_packages_with_versions:
            print("Список установленных пакетов пуст.")
        else:
            if args.quick:
                print("Используем режим 'быстрой' проверки (только критические пакеты).")
                critical_list = set(linux_audit.get_critical_packages())
                packages_to_check = {pkg: ver for pkg, ver in all_packages_with_versions.items() if pkg in critical_list}
                if not packages_to_check:
                    print("Ни один из критических пакетов не установлен.")
                else:
                    print(f"Найдено {len(packages_to_check)} критических пакетов для проверки.")
            else:
                packages_to_check = all_packages_with_versions
                print(f"Найдено {len(packages_to_check)} установленных пакетов.")

    if packages_to_check:
        print("Проверка пакетов на уязвимости через NVD API (это может занять некоторое время)...")
        cve_data, success_count = linux_audit.check_cve_for_packages(
            packages_to_check,
            verbose=True,
            delay=1.0,
            retries=7,
            timeout=30
        )
        if cve_data:
            print(f"Найдены уязвимости для {len(cve_data)} пакетов.")
        else:
            print("Уязвимостей не найдено или ошибка API.")
        packages_to_check_count = len(packages_to_check)
    else:
        if args.cve:
            print("Нет пакетов для проверки CVE.")

    failed = linux_audit.get_failed_logins()
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
        'cve_success_count': success_count
    }

    generate_report(data)
    print("Аудит завершён.")

if __name__ == "__main__":
    main()

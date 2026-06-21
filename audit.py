#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import json
import os
import platform
import socket
from datetime import datetime
from collections import Counter
import re

# ---------- Функции для работы с обновлениями ----------
def get_updates():
    """Возвращает список пакетов с доступными обновлениями."""
    try:
        result = subprocess.run(['apt', 'list', '--upgradable'],
                                capture_output=True, text=True)
        if result.stdout.strip():
            lines = result.stdout.strip().split('\n')[1:]
            packages = []
            for line in lines:
                if line:
                    pkg = line.split('/')[0]
                    packages.append(pkg)
            return packages
        else:
            return []
    except FileNotFoundError:
        try:
            result = subprocess.run(['yum', 'check-update'],
                                    capture_output=True, text=True)
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                packages = []
                for line in lines:
                    if line and not line.startswith('Loaded') and not line.startswith('Last'):
                        parts = line.split()
                        if parts and parts[0].strip():
                            packages.append(parts[0])
                return packages
            else:
                return []
        except FileNotFoundError:
            return None

def install_updates(packages, auto_yes=False):
    """Устанавливает обновления. Возвращает список установленных пакетов."""
    if not packages:
        return []
    # Определяем менеджер
    try:
        subprocess.run(['apt', '--version'], capture_output=True, check=True)
        cmd = ['sudo', 'apt', 'install', '-y'] + packages if auto_yes else ['sudo', 'apt', 'install'] + packages
    except:
        try:
            subprocess.run(['yum', '--version'], capture_output=True, check=True)
            cmd = ['sudo', 'yum', 'update', '-y'] + packages if auto_yes else ['sudo', 'yum', 'update'] + packages
        except:
            print("Не найден менеджер пакетов", file=sys.stderr)
            return []
    if not auto_yes:
        # Если не auto_yes, мы уже запросили подтверждение в основном коде
        pass
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Ошибка установки:", result.stderr, file=sys.stderr)
        return []
    # Парсим вывод, чтобы понять, какие пакеты были установлены (упрощённо)
    # Можно просто вернуть переданный список, считая, что все установились успешно
    return packages

# ---------- Функции для сбора системной информации ----------
def get_system_info():
    hostname = socket.gethostname()
    os_name = platform.system() + " " + platform.release()
    serial = "N/A"
    try:
        with open('/sys/class/dmi/id/product_serial', 'r') as f:
            serial = f.read().strip()
    except:
        pass
    return {
        'hostname': hostname,
        'os': os_name,
        'serial': serial,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def get_failed_logins(log_path='/var/log/auth.log'):
    ip_pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+)')
    failed = []
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'Failed password' in line or 'authentication failure' in line:
                    match = ip_pattern.search(line)
                    if match:
                        failed.append(match.group(1))
    except FileNotFoundError:
        return None
    except PermissionError:
        return None
    return Counter(failed)

# ---------- Генерация отчёта ----------
def generate_report(data, output_dir='reports'):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_name = f"audit_report_{timestamp}"

    txt_path = os.path.join(output_dir, base_name + '.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("         ОТЧЁТ ПО ИНФОРМАЦИОННОЙ БЕЗОПАСНОСТИ\n")
        f.write("="*60 + "\n\n")
        sysinfo = data.get('system', {})
        f.write(f"Дата:          {sysinfo.get('timestamp', 'N/A')}\n")
        f.write(f"Имя хоста:     {sysinfo.get('hostname', 'N/A')}\n")
        f.write(f"ОС:            {sysinfo.get('os', 'N/A')}\n")
        f.write(f"Серийный N:    {sysinfo.get('serial', 'N/A')}\n")

        # Обновления
        f.write("\n--- ОБНОВЛЕНИЯ ---\n")
        available = data.get('updates_available', [])
        installed = data.get('updates_installed', [])
        if available:
            f.write(f"Доступно обновлений: {len(available)}\n")
            for pkg in available:
                f.write(f"  - {pkg}\n")
        else:
            f.write("Доступных обновлений не найдено.\n")
        if installed:
            f.write(f"\nУстановлено обновлений: {len(installed)}\n")
            for pkg in installed:
                f.write(f"  + {pkg}\n")
        else:
            f.write("\nОбновления не устанавливались.\n")

        # Логи
        f.write("\n--- НЕУДАЧНЫЕ ПОПЫТКИ ВХОДА ---\n")
        logins = data.get('failed_logins', {})
        if logins:
            for ip, count in sorted(logins.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{ip:20} {count} раз(а)\n")
            f.write(f"Всего IP: {len(logins)}\n")
        else:
            f.write("Неудачных попыток не обнаружено.\n")

        f.write("\n" + "="*60 + "\n")
        f.write(f"Подпись:       Илья Тришкин\n")
        f.write(f"Должность:     Специалист по информационной безопасности\n")
        f.write(f"Дата подписания: {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write("="*60 + "\n")

    # Сохраняем JSON (без изменений)
    json_path = os.path.join(output_dir, base_name + '.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"Отчёт сохранён: {txt_path}")
    print(f"JSON-отчёт сохранён: {json_path}")

# ---------- Основная функция ----------
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Аудит безопасности Linux')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Автоматически устанавливать обновления без подтверждения')
    parser.add_argument('--no-update', action='store_true',
                        help='Пропустить установку обновлений (только проверка)')
    args = parser.parse_args()

    print("Начинаем аудит безопасности...")

    # 1. Собираем системную информацию
    sys_info = get_system_info()

    # 2. Проверяем обновления
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

    # 3. Проверяем логи (после обновления)
    failed = get_failed_logins()
    if failed is None:
        print("Не удалось прочитать лог-файл (возможно, нет прав).")
        failed = {}

    # 4. Формируем данные для отчёта
    data = {
        'system': sys_info,
        'updates_available': updates if updates else [],
        'updates_installed': installed_pkgs,
        'failed_logins': dict(failed)
    }

    # 5. Генерируем отчёт
    generate_report(data)
    print("Аудит завершён.")

if __name__ == "__main__":
    main()

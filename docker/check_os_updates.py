#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import json
import argparse

def get_updates():
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

def install_updates_apt(packages):
    print(f"Устанавливаю {len(packages)} обновлений через apt...")
    cmd = ['sudo', 'apt', 'install', '-y'] + packages
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Ошибка при установке обновлений:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return False
    print("Обновления успешно установлены.")
    return True

def install_updates_yum(packages):
    print(f"Устанавливаю {len(packages)} обновлений через yum...")
    cmd = ['sudo', 'yum', 'update', '-y'] + packages
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Ошибка при установке обновлений:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return False
    print("Обновления успешно установлены.")
    return True

def install_updates(packages):
    try:
        subprocess.run(['apt', '--version'], capture_output=True, check=True)
        return install_updates_apt(packages)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    try:
        subprocess.run(['yum', '--version'], capture_output=True, check=True)
        return install_updates_yum(packages)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Не найден ни apt, ни yum. Установка невозможна.", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Проверка и установка обновлений пакетов в Linux-системах'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['text', 'json'],
        default='text',
        help='Формат вывода: text (по умолчанию) или json'
    )
    parser.add_argument(
        '--update', '-u',
        action='store_true',
        help='Установить все доступные обновления (повторять, пока есть)'
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Автоматически соглашаться на установку (без подтверждения)'
    )
    args = parser.parse_args()

    if args.update:
        while True:
            updates = get_updates()
            if updates is None:
                print("Ошибка: не найден менеджер пакетов.", file=sys.stderr)
                sys.exit(1)
            if not updates:
                print("Нет доступных обновлений. Система полностью обновлена.")
                break
            print(f"Найдено {len(updates)} пакетов для обновления.")
            if not args.yes:
                reply = input("Установить все обновления? (y/n): ").strip().lower()
                if reply not in ('y', 'yes'):
                    print("Установка отменена.")
                    break
            success = install_updates(updates)
            if not success:
                print("Ошибка при установке. Прерывание.", file=sys.stderr)
                sys.exit(1)
            print("Проверяю, остались ли ещё обновления...")
        return

    updates = get_updates()
    if updates is None:
        print("Ошибка: не найден менеджер пакетов (apt или yum).", file=sys.stderr)
        sys.exit(1)

    if args.format == 'json':
        print(json.dumps(updates, ensure_ascii=False, indent=2))
    else:
        if updates:
            print("Доступны обновления для следующих пакетов:")
            for pkg in updates:
                print(f"  - {pkg}")
            print(f"Всего: {len(updates)} пакетов.")
            print("\nДля установки выполните скрипт с флагом --update")
        else:
            print("Нет доступных обновлений.")

if __name__ == "__main__":
    main()

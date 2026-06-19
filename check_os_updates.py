#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import json
import argparse

def get_updates():
    """
    Возвращает список названий пакетов, для которых доступны обновления.
    Поддерживает apt (Debian/Ubuntu/Astra) и yum (CentOS/RedOS).
    Если менеджер не найден, возвращает None.
    """
    try:
        # Пробуем apt
        result = subprocess.run(['apt', 'list', '--upgradable'],
                                capture_output=True, text=True)
        if result.stdout.strip():
            lines = result.stdout.strip().split('\n')[1:]  # пропускаем заголовок
            packages = []
            for line in lines:
                if line:
                    # Формат: "package/version arch [upgradable from: ...]"
                    pkg = line.split('/')[0]
                    packages.append(pkg)
            return packages
        else:
            return []
    except FileNotFoundError:
        try:
            # Пробуем yum
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
            return None  # ошибка: ни apt, ни yum не найдены

def main():
    parser = argparse.ArgumentParser(
        description='Проверка доступных обновлений пакетов в Linux-системах'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['text', 'json'],
        default='text',
        help='Формат вывода: text (по умолчанию) или json'
    )
    args = parser.parse_args()

    updates = get_updates()
    if updates is None:
        print("Ошибка: не найден менеджер пакетов (apt или yum).", file=sys.stderr)
        sys.exit(1)

    if args.format == 'json':
        # Выводим в формате JSON
        print(json.dumps(updates, ensure_ascii=False, indent=2))
    else:
        # Текстовый вывод
        if updates:
            print("Доступны обновления для следующих пакетов:")
            for pkg in updates:
                print(f"  - {pkg}")
            print(f"Всего: {len(updates)} пакетов.")
        else:
            print("Нет доступных обновлений.")

if __name__ == "__main__":
    main()

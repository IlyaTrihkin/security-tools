#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import json
import argparse
from collections import Counter
from pathlib import Path

def parse_auth_log(log_path):
    """
    Парсит файл лога и возвращает Counter с IP-адресами,
    с которых были неудачные попытки входа (SSH).
    """
    ip_pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+)')
    failed_attempts = []

    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Ищем строки с неудачной попыткой входа
                if 'Failed password' in line or 'authentication failure' in line:
                    match = ip_pattern.search(line)
                    if match:
                        failed_attempts.append(match.group(1))
    except FileNotFoundError:
        print(f"Ошибка: файл {log_path} не найден.", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Ошибка: нет прав на чтение файла {log_path}.", file=sys.stderr)
        sys.exit(1)

    return Counter(failed_attempts)

def main():
    parser = argparse.ArgumentParser(
        description='Анализ неудачных попыток входа из логов (SSH)'
    )
    parser.add_argument(
        '--file', '-f',
        default='/var/log/auth.log',
        help='Путь к лог-файлу (по умолчанию: /var/log/auth.log)'
    )
    parser.add_argument(
        '--format', '-fmt',
        choices=['text', 'json'],
        default='text',
        help='Формат вывода: text (по умолчанию) или json'
    )
    parser.add_argument(
        '--min-count', '-m',
        type=int,
        default=1,
        help='Минимальное количество попыток для отображения (по умолчанию: 1)'
    )
    parser.add_argument(
        '--top', '-t',
        type=int,
        default=None,
        help='Показать только N самых активных IP'
    )
    args = parser.parse_args()

    # Проверяем существование файла
    log_file = Path(args.file)
    if not log_file.exists():
        print(f"Ошибка: файл {args.file} не существует.", file=sys.stderr)
        sys.exit(1)

    # Парсим лог
    counter = parse_auth_log(args.file)

    if not counter:
        print("Не найдено неудачных попыток входа.")
        return

    # Фильтруем по минимальному количеству
    filtered = {ip: count for ip, count in counter.items() if count >= args.min_count}

    if not filtered:
        print(f"Нет IP с количеством попыток >= {args.min_count}.")
        return

    # Сортируем по убыванию
    sorted_items = sorted(filtered.items(), key=lambda x: x[1], reverse=True)

    # Обрезаем по top
    if args.top:
        sorted_items = sorted_items[:args.top]

    # Вывод
    if args.format == 'json':
        result = {ip: count for ip, count in sorted_items}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Неудачные попытки входа (всего: {sum(filtered.values())})")
        print("-" * 40)
        for ip, count in sorted_items:
            print(f"{ip:20} {count} раз(а)")
        print("-" * 40)
        print(f"Уникальных IP: {len(sorted_items)}")

if __name__ == "__main__":
    main()

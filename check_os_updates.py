#!/usr/bin/env python3
import subprocess
import sys

def check_updates():
    try:
        # Пробуем apt (Debian/Astra/Ubuntu)
        print("Проверяем обновления через apt...")
        result = subprocess.run(['apt', 'list', '--upgradable'], 
                                capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        else:
            print("Нет доступных обновлений (или ошибка).")
            
    except FileNotFoundError:
        # Если apt не найден, пробуем yum (CentOS/RedOS/Astra special)
        try:
            print("Проверяем обновления через yum...")
            result = subprocess.run(['yum', 'check-update'], 
                                    capture_output=True, text=True)
            print(result.stdout)
        except FileNotFoundError:
            print("Не найден ни apt, ни yum. Установите менеджер пакетов.")
            sys.exit(1)

if __name__ == "__main__":
    check_updates()

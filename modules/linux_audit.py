#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import re
from collections import Counter

def get_updates():
    """Возвращает список пакетов с обновлениями (apt/yum)."""
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

def get_failed_logins(log_path='/var/log/auth.log'):
    """Анализирует лог SSH, возвращает Counter IP -> кол-во попыток."""
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

def get_system_info():
    """Возвращает базовую информацию о системе."""
    import platform
    import socket
    hostname = socket.gethostname()
    os_name = platform.system() + " " + platform.release()
    # Серийный номер (может потребоваться sudo)
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
        'timestamp': subprocess.check_output(['date', '+%Y-%m-%d %H:%M:%S']).decode().strip()
    }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess

def get_updates():
    try:
        result = subprocess.run(['apt', 'list', '--upgradable'],
                                capture_output=True, text=True)
        if result.stdout.strip():
            lines = result.stdout.strip().split('\n')[1:]
            return [line.split('/')[0] for line in lines if line]
        else:
            return []
    except FileNotFoundError:
        try:
            result = subprocess.run(['yum', 'check-update'],
                                    capture_output=True, text=True)
            if result.stdout.strip():
                packages = []
                for line in result.stdout.strip().split('\n'):
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
    if not packages:
        return []
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
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Ошибка установки:", result.stderr, file=sys.stderr)
        return []
    return packages

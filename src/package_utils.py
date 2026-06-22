#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess

def get_installed_packages_with_versions():
    """
    Возвращает словарь {имя_пакета: версия} для всех установленных пакетов.
    Поддерживает apt и yum.
    """
    packages = {}
    try:
        result = subprocess.run(['apt', 'list', '--installed'],
                                capture_output=True, text=True)
        if result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if line and not line.startswith('Listing'):
                    parts = line.split('/')
                    if len(parts) >= 2:
                        pkg = parts[0]
                        version = parts[1].split()[0]
                        packages[pkg] = version
        else:
            return {}
    except FileNotFoundError:
        try:
            result = subprocess.run(['yum', 'list', 'installed'],
                                    capture_output=True, text=True)
            if result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if line and not line.startswith('Installed') and not line.startswith('Loaded'):
                        parts = line.split()
                        if len(parts) >= 2:
                            pkg = parts[0].rsplit('.', 1)[0]
                            version = parts[1]
                            packages[pkg] = version
            else:
                return {}
        except FileNotFoundError:
            return None
    return packages

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import re
import socket
import platform
import requests
import time
import sys
from collections import Counter
from datetime import datetime
import json

# ---------- Попытка импортировать packaging для сравнения версий ----------
try:
    from packaging import version as pkg_version
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False

# ---------- Системная информация ----------
def get_mac_address(interface='eth0'):
    try:
        result = subprocess.run(['ip', 'link', 'show', interface],
                                capture_output=True, text=True)
        if result.returncode == 0:
            match = re.search(r'link/ether ([0-9a-fA-F:]{17})', result.stdout)
            if match:
                return match.group(1)
    except:
        pass
    return 'N/A'

def get_ip_address(interface='eth0'):
    try:
        result = subprocess.run(['ip', '-4', 'addr', 'show', interface],
                                capture_output=True, text=True)
        if result.returncode == 0:
            match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/\d+', result.stdout)
            if match:
                return match.group(1)
    except:
        pass
    return 'N/A'

def get_machine_id():
    try:
        with open('/etc/machine-id', 'r') as f:
            return f.read().strip()
    except:
        return 'N/A'

def get_system_info(interface='eth0'):
    hostname = socket.gethostname()
    kernel = platform.release()

    os_name = "Unknown"
    os_version = "Unknown"
    try:
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if line.startswith('NAME='):
                    os_name = line.split('=')[1].strip().strip('"')
                elif line.startswith('VERSION_ID='):
                    os_version = line.split('=')[1].strip().strip('"')
                elif line.startswith('VERSION=') and os_version == "Unknown":
                    os_version = line.split('=')[1].strip().strip('"')
    except:
        pass

    serial = "N/A"
    try:
        with open('/sys/class/dmi/id/product_serial', 'r') as f:
            serial = f.read().strip()
    except:
        pass

    mac = get_mac_address(interface)
    ip = get_ip_address(interface)
    machine_id = get_machine_id()

    return {
        'hostname': hostname,
        'os_name': os_name,
        'os_version': os_version,
        'kernel': kernel,
        'serial': serial,
        'mac': mac,
        'ip': ip,
        'machine_id': machine_id,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ---------- Работа с обновлениями ----------
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

# ---------- Получение списка установленных пакетов с версиями ----------
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
                        version = parts[1].split()[0]  # берем версию до пробела
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
                            pkg = parts[0].rsplit('.', 1)[0]  # убираем архитектуру
                            version = parts[1]
                            packages[pkg] = version
            else:
                return {}
        except FileNotFoundError:
            return None
    return packages

def get_installed_packages():
    result = get_installed_packages_with_versions()
    if result is None:
        return None
    return list(result.keys())

def get_critical_packages():
    critical = [
        'openssl', 'libssl', 'bash', 'sudo', 'systemd', 'linux', 'linux-image',
        'kernel', 'nginx', 'apache2', 'httpd', 'mysql', 'mariadb', 'postgresql',
        'redis', 'mongodb', 'openssh', 'ssh', 'dropbear', 'vsftpd', 'proftpd',
        'exim', 'sendmail', 'postfix', 'dovecot', 'bind', 'named', 'unbound',
        'isc-dhcp', 'dhcpcd', 'samba', 'smb', 'nfs', 'glibc', 'libc6',
        'python', 'python3', 'perl', 'ruby', 'php', 'nodejs', 'npm',
        'docker', 'containerd', 'kubernetes', 'kubelet', 'helm',
        'java', 'openjdk', 'jre', 'tomcat', 'jenkins', 'git', 'subversion',
        'curl', 'wget', 'gnupg', 'gpg', 'libgcrypt', 'libgpg-error', 'pam',
        'polkit', 'dbus', 'avahi', 'cups', 'systemd-resolved', 'NetworkManager',
        'firewalld', 'iptables', 'nftables', 'ufw', 'fail2ban', 'clamav',
        'rkhunter', 'aide', 'tripwire', 'ossec', 'wazuh', 'zabbix', 'prometheus',
        'grafana', 'elasticsearch', 'logstash', 'kibana', 'filebeat', 'metricbeat',
        'auditd', 'audit', 'syslog', 'rsyslog', 'syslog-ng', 'logrotate'
    ]
    return sorted(set(critical))

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
    except (FileNotFoundError, PermissionError):
        return None
    return Counter(failed)

# ---------- Сравнение версий ----------
def version_compare(v1, v2):
    """
    Сравнивает две версии. Использует packaging.version, если доступен,
    иначе пытается сравнить как числовые последовательности.
    Возвращает -1, 0, 1 или None при ошибке.
    """
    if not v1 or not v2:
        return None
    if HAS_PACKAGING:
        try:
            ver1 = pkg_version.parse(v1)
            ver2 = pkg_version.parse(v2)
            if ver1 < ver2:
                return -1
            elif ver1 > ver2:
                return 1
            else:
                return 0
        except:
            pass
    # fallback: попробуем разбить по точкам и сравнить числа
    try:
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]
        while len(v1_parts) < len(v2_parts):
            v1_parts.append(0)
        while len(v2_parts) < len(v1_parts):
            v2_parts.append(0)
        for a, b in zip(v1_parts, v2_parts):
            if a < b:
                return -1
            if a > b:
                return 1
        return 0
    except:
        return None

def is_version_affected(version, config_nodes):
    """
    Проверяет, попадает ли версия пакета в уязвимый диапазон на основе nodes из конфигурации CVE.
    nodes могут содержать 'cpeMatch' с 'versionStartIncluding', 'versionStartExcluding',
    'versionEndIncluding', 'versionEndExcluding'.
    Возвращает True, если версия затронута, False в противном случае.
    Если информация о версиях отсутствует, считаем, что уязвимость актуальна для всех версий (True).
    """
    if not version:
        # Если версия неизвестна, считаем, что уязвимость потенциально актуальна
        return True

    # Проверяем, есть ли вообще какие-либо ограничения по версиям
    has_version_constraints = False
    for node in config_nodes:
        if 'cpeMatch' in node:
            for cpe in node['cpeMatch']:
                if cpe.get('vulnerable', False):
                    if any(key in cpe for key in ['versionStartIncluding', 'versionStartExcluding',
                                                  'versionEndIncluding', 'versionEndExcluding']):
                        has_version_constraints = True
                        break
        if has_version_constraints:
            break

    # Если ограничений нет, уязвимость считается актуальной для всех версий
    if not has_version_constraints:
        return True

    # Если ограничения есть, проверяем, попадает ли наша версия в какой-либо диапазон
    for node in config_nodes:
        if 'cpeMatch' in node:
            for cpe in node['cpeMatch']:
                if cpe.get('vulnerable', False):
                    start_inc = cpe.get('versionStartIncluding')
                    start_exc = cpe.get('versionStartExcluding')
                    end_inc = cpe.get('versionEndIncluding')
                    end_exc = cpe.get('versionEndExcluding')
                    ok = True
                    if start_inc:
                        cmp = version_compare(version, start_inc)
                        if cmp is None or cmp < 0:
                            ok = False
                    if start_exc:
                        cmp = version_compare(version, start_exc)
                        if cmp is None or cmp <= 0:
                            ok = False
                    if end_inc:
                        cmp = version_compare(version, end_inc)
                        if cmp is None or cmp > 0:
                            ok = False
                    if end_exc:
                        cmp = version_compare(version, end_exc)
                        if cmp is None or cmp >= 0:
                            ok = False
                    if ok:
                        return True
    return False

# ---------- Проверка CVE через NVD API с фильтрацией по версиям ----------
def check_cve_for_packages(packages_with_versions, timeout=30, verbose=False, delay=1.0, retries=7):
    if not packages_with_versions:
        return {}, 0
    base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    results = {}
    total = len(packages_with_versions)
    success_count = 0
    start_time = time.time()
    found_cves = 0
    last_status = ""

    def print_progress(idx, elapsed, remaining, found, bar, percent, status_msg=""):
        el_min = int(elapsed // 60)
        el_sec = int(elapsed % 60)
        rem_min = int(remaining // 60) if remaining > 0 else 0
        rem_sec = int(remaining % 60) if remaining > 0 else 0
        line = (f"\r\033[KИдет проверка... {idx}/{total} | {bar} | {percent:5.1f}% | "
                f"Время: {el_min:02d}:{el_sec:02d} | Осталось: {rem_min:02d}:{rem_sec:02d} | "
                f"CVE: {found} | {status_msg if status_msg else ''}")
        if len(line) > 150:
            line = line[:147] + "..."
        sys.stdout.write(line)
        sys.stdout.flush()

    for idx, (pkg, version) in enumerate(packages_with_versions.items(), 1):
        elapsed = time.time() - start_time
        if idx > 1:
            avg_time = elapsed / (idx - 1)
            remaining = avg_time * (total - idx)
        else:
            remaining = (delay * 2) * (total - idx)

        percent = (idx / total) * 100
        bar_len = 30
        filled = int(bar_len * idx / total)
        bar = '█' * filled + '░' * (bar_len - filled)

        if verbose:
            print_progress(idx, elapsed, remaining, found_cves, bar, percent, "")

        success = False
        for attempt in range(retries):
            try:
                params = {'keywordSearch': pkg, 'resultsPerPage': 10}
                response = requests.get(base_url, params=params, timeout=timeout)
                if response.status_code == 200:
                    success_count += 1
                    data = response.json()
                    cves = []
                    for vuln in data.get('vulnerabilities', []):
                        cve_id = vuln.get('cve', {}).get('id', 'N/A')
                        description = vuln.get('cve', {}).get('descriptions', [{}])[0].get('value', 'No description')
                        metrics = vuln.get('cve', {}).get('metrics', {})
                        cvss_score = 'N/A'
                        if 'cvssMetricV31' in metrics:
                            cvss_score = metrics['cvssMetricV31'][0].get('cvssData', {}).get('baseScore', 'N/A')
                        elif 'cvssMetricV30' in metrics:
                            cvss_score = metrics['cvssMetricV30'][0].get('cvssData', {}).get('baseScore', 'N/A')
                        configurations = vuln.get('cve', {}).get('configurations', [])
                        affected = False
                        for config in configurations:
                            nodes = config.get('nodes', [])
                            if is_version_affected(version, nodes):
                                affected = True
                                break
                        if affected:
                            cves.append({
                                'id': cve_id,
                                'description': description[:200] + '...' if len(description) > 200 else description,
                                'cvss_score': cvss_score
                            })
                    if cves:
                        results[pkg] = cves
                        found_cves += len(cves)
                    success = True
                    if verbose:
                        elapsed_final = time.time() - start_time
                        if idx > 1:
                            avg_final = elapsed_final / (idx - 1)
                            remaining_final = avg_final * (total - idx)
                        else:
                            remaining_final = (delay * 2) * (total - idx)
                        percent_final = (idx / total) * 100
                        filled_final = int(bar_len * idx / total)
                        bar_final = '█' * filled_final + '░' * (bar_len - filled_final)
                        print_progress(idx, elapsed_final, remaining_final, found_cves, bar_final, percent_final, "")
                    break
                elif response.status_code in (429, 503):
                    wait = (2 ** attempt)
                    if verbose:
                        elapsed_wait = time.time() - start_time
                        if idx > 1:
                            avg_wait = elapsed_wait / (idx - 1)
                            remaining_wait = avg_wait * (total - idx)
                        else:
                            remaining_wait = (delay * 2) * (total - idx)
                        percent_wait = (idx / total) * 100
                        filled_wait = int(bar_len * idx / total)
                        bar_wait = '█' * filled_wait + '░' * (bar_len - filled_wait)
                        print_progress(idx, elapsed_wait, remaining_wait, found_cves, bar_wait, percent_wait,
                                       f"ошибка {response.status_code}, повтор через {wait}с")
                    time.sleep(wait)
                    continue
                else:
                    results[pkg] = [{'error': f'HTTP {response.status_code}'}]
                    success = True
                    if verbose:
                        elapsed_err = time.time() - start_time
                        if idx > 1:
                            avg_err = elapsed_err / (idx - 1)
                            remaining_err = avg_err * (total - idx)
                        else:
                            remaining_err = (delay * 2) * (total - idx)
                        percent_err = (idx / total) * 100
                        filled_err = int(bar_len * idx / total)
                        bar_err = '█' * filled_err + '░' * (bar_len - filled_err)
                        print_progress(idx, elapsed_err, remaining_err, found_cves, bar_err, percent_err,
                                       f"HTTP {response.status_code}")
                    break
            except requests.exceptions.Timeout:
                if attempt == retries - 1:
                    results[pkg] = [{'error': 'Timeout'}]
                    success = True
                    if verbose:
                        elapsed_to = time.time() - start_time
                        if idx > 1:
                            avg_to = elapsed_to / (idx - 1)
                            remaining_to = avg_to * (total - idx)
                        else:
                            remaining_to = (delay * 2) * (total - idx)
                        percent_to = (idx / total) * 100
                        filled_to = int(bar_len * idx / total)
                        bar_to = '█' * filled_to + '░' * (bar_len - filled_to)
                        print_progress(idx, elapsed_to, remaining_to, found_cves, bar_to, percent_to, "Таймаут")
                else:
                    wait = (2 ** attempt)
                    if verbose:
                        elapsed_wait = time.time() - start_time
                        if idx > 1:
                            avg_wait = elapsed_wait / (idx - 1)
                            remaining_wait = avg_wait * (total - idx)
                        else:
                            remaining_wait = (delay * 2) * (total - idx)
                        percent_wait = (idx / total) * 100
                        filled_wait = int(bar_len * idx / total)
                        bar_wait = '█' * filled_wait + '░' * (bar_len - filled_wait)
                        print_progress(idx, elapsed_wait, remaining_wait, found_cves, bar_wait, percent_wait,
                                       f"таймаут, повтор через {wait}с")
                    time.sleep(wait)
                    continue
            except Exception as e:
                results[pkg] = [{'error': str(e)}]
                success = True
                if verbose:
                    elapsed_ex = time.time() - start_time
                    if idx > 1:
                        avg_ex = elapsed_ex / (idx - 1)
                        remaining_ex = avg_ex * (total - idx)
                    else:
                        remaining_ex = (delay * 2) * (total - idx)
                    percent_ex = (idx / total) * 100
                    filled_ex = int(bar_len * idx / total)
                    bar_ex = '█' * filled_ex + '░' * (bar_len - filled_ex)
                    print_progress(idx, elapsed_ex, remaining_ex, found_cves, bar_ex, percent_ex,
                                   f"ошибка: {str(e)[:30]}")
                break

        if not success:
            results[pkg] = [{'error': 'Failed after retries'}]
            if verbose:
                elapsed_fail = time.time() - start_time
                if idx > 1:
                    avg_fail = elapsed_fail / (idx - 1)
                    remaining_fail = avg_fail * (total - idx)
                else:
                    remaining_fail = (delay * 2) * (total - idx)
                percent_fail = (idx / total) * 100
                filled_fail = int(bar_len * idx / total)
                bar_fail = '█' * filled_fail + '░' * (bar_len - filled_fail)
                print_progress(idx, elapsed_fail, remaining_fail, found_cves, bar_fail, percent_fail, "Ошибка")

        if idx < total and delay > 0:
            time.sleep(delay)

    if verbose:
        sys.stdout.write("\n")
        sys.stdout.flush()

    return results, success_count

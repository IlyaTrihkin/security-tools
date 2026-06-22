#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import requests
import time
import json
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from tqdm import tqdm

from package_utils import get_installed_packages_with_versions

# ---------- Кэширование ----------
CACHE_FILE = "cve_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def get_package_fingerprint(packages_with_versions):
    items = sorted(packages_with_versions.items())
    data = json.dumps(items, sort_keys=True)
    return hashlib.md5(data.encode()).hexdigest()

# ---------- Функции сравнения версий ----------
try:
    from packaging import version as pkg_version
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False

def version_compare(v1, v2):
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
    if not version:
        return True
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
    if not has_version_constraints:
        return True
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

# ---------- Основная функция проверки через NVD ----------
def check_cve_for_packages(packages_with_versions, timeout=90, max_workers=2, retries=7):
    if not packages_with_versions:
        return {}, 0

    # Кэш
    cache = load_cache()
    fingerprint = get_package_fingerprint(packages_with_versions)
    if cache.get('fingerprint') == fingerprint:
        result = {k: v for k, v in cache.items() if k not in ('fingerprint', 'timestamp')}
        return result, len(packages_with_versions)

    total = len(packages_with_versions)
    results = {}
    success_count = 0
    failed_packages = []
    lock = threading.Lock()
    base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    # Используем tqdm для прогресса
    pbar = tqdm(total=total, desc="Идет проверка CVE (NVD)", unit="пакет")

    def process_package(pkg, version):
        nonlocal success_count
        for attempt in range(retries):
            try:
                if attempt > 0:
                    wait = 2 ** (attempt - 1)
                    time.sleep(wait)
                params = {'keywordSearch': pkg, 'resultsPerPage': 10}
                response = requests.get(base_url, params=params, timeout=timeout)
                if response.status_code == 200:
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
                            cve_link = f"https://nvd.nist.gov/vuln/detail/{cve_id}"
                            cves.append({
                                'id': cve_id,
                                'description': description[:200] + '...' if len(description) > 200 else description,
                                'cvss_score': cvss_score,
                                'link': cve_link
                            })
                    if cves:
                        with lock:
                            results[pkg] = cves
                    with lock:
                        success_count += 1
                        pbar.update(1)
                    return
                elif response.status_code in (429, 503):
                    wait = 2 ** (attempt + 1)
                    time.sleep(wait)
                    continue
                else:
                    continue
            except requests.exceptions.Timeout:
                continue
            except Exception:
                continue
        with lock:
            failed_packages.append((pkg, version))
            pbar.update(1)

    # Первый проход
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for pkg, version in packages_with_versions.items():
            future = executor.submit(process_package, pkg, version)
            futures[future] = (pkg, version)

        for future in as_completed(futures):
            pass  # прогресс обновляется внутри process_package

    pbar.close()

    # Второй проход для неудачных пакетов
    if failed_packages:
        print(f"\nПовторная проверка {len(failed_packages)} пакетов с увеличенным таймаутом...")
        pbar2 = tqdm(total=len(failed_packages), desc="Повторная проверка (NVD)", unit="пакет")
        timeout2 = 120
        retries2 = 5
        for pkg, version in failed_packages:
            for attempt in range(retries2):
                try:
                    if attempt > 0:
                        wait = 2 ** (attempt - 1)
                        time.sleep(wait)
                    params = {'keywordSearch': pkg, 'resultsPerPage': 10}
                    response = requests.get(base_url, params=params, timeout=timeout2)
                    if response.status_code == 200:
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
                                cve_link = f"https://nvd.nist.gov/vuln/detail/{cve_id}"
                                cves.append({
                                    'id': cve_id,
                                    'description': description[:200] + '...' if len(description) > 200 else description,
                                    'cvss_score': cvss_score,
                                    'link': cve_link
                                })
                        if cves:
                            with lock:
                                results[pkg] = cves
                        with lock:
                            success_count += 1
                        break
                    elif response.status_code in (429, 503):
                        wait = 2 ** (attempt + 1)
                        time.sleep(wait)
                        continue
                    else:
                        continue
                except:
                    continue
            pbar2.update(1)
        pbar2.close()

    # Сохраняем кэш
    cache_data = results.copy()
    cache_data['fingerprint'] = fingerprint
    cache_data['timestamp'] = datetime.now().isoformat()
    save_cache(cache_data)

    return results, success_count

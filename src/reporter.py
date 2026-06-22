#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime

def generate_report(data, output_dir='reports'):
    """
    Генерирует отчёт в форматах TXT и JSON.
    data: словарь с данными аудита.
    output_dir: папка для сохранения отчётов.
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_name = f"audit_report_{timestamp}"

    # ---------- TXT-отчёт ----------
    txt_path = os.path.join(output_dir, base_name + '.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        sysinfo = data.get('system', {})
        f.write("="*60 + "\n")
        f.write("         ОТЧЁТ ПО ИНФОРМАЦИОННОЙ БЕЗОПАСНОСТИ\n")
        f.write("="*60 + "\n\n")
        f.write(f"Дата:          {sysinfo.get('timestamp', 'N/A')}\n")
        f.write(f"Имя хоста:     {sysinfo.get('hostname', 'N/A')}\n")
        f.write(f"Тип ОС:        {sysinfo.get('os_name', 'N/A')}\n")
        f.write(f"Версия ОС:     {sysinfo.get('os_version', 'N/A')}\n")
        f.write(f"Версия ядра:   {sysinfo.get('kernel', 'N/A')}\n")
        f.write(f"Серийный N:    {sysinfo.get('serial', 'N/A')}\n")
        f.write(f"MAC-адрес:     {sysinfo.get('mac', 'N/A')}\n")
        f.write(f"IP-адрес:      {sysinfo.get('ip', 'N/A')}\n")
        f.write(f"Machine ID:    {sysinfo.get('machine_id', 'N/A')}\n")
        f.write("\n")

        # ---------- Обновления ----------
        f.write("--- ОБНОВЛЕНИЯ ---\n")
        available = data.get('updates_available', [])
        installed = data.get('updates_installed', [])
        if available:
            f.write(f"Доступно обновлений: {len(available)}\n")
            for pkg in available:
                f.write(f"  - {pkg}\n")
            if installed:
                f.write(f"\nУстановлено обновлений: {len(installed)}\n")
                for pkg in installed:
                    f.write(f"  + {pkg}\n")
            else:
                f.write("\nОбновления не устанавливались.\n")
        else:
            f.write("Доступных обновлений не найдено.\n")
        f.write("\n")

        # ---------- CVE ----------
        cve_data = data.get('cve', {})
        total_checked = data.get('cve_checked_count', 0)
        success_checked = data.get('cve_success_count', 0)
        source = data.get('cve_source', 'N/A')
        updates_available = set(available)

        if cve_data or total_checked > 0:
            f.write("--- УЯЗВИМОСТИ (CVE) ---\n")
            f.write(f"Всего пакетов в проверке: {total_checked}\n")
            f.write(f"Успешно проверено: {success_checked}\n")
            if total_checked > success_checked:
                f.write(f"Ошибок при проверке: {total_checked - success_checked}\n")
            f.write(f"Источник данных: {source}\n")

            if cve_data:
                total_cves = 0
                critical_cves = []
                other_cves = []
                for pkg, cves in cve_data.items():
                    for cve in cves:
                        total_cves += 1
                        try:
                            cvss = float(cve.get('cvss_score', 'N/A'))
                            if cvss >= 7.0:
                                critical_cves.append((pkg, cve))
                            else:
                                other_cves.append((pkg, cve))
                        except:
                            other_cves.append((pkg, cve))

                f.write(f"Всего найдено уязвимостей (соответствующих версии): {total_cves}\n")
                f.write(f"Из них критических (CVSS >= 7.0): {len(critical_cves)}\n")

                if critical_cves:
                    f.write("\n--- КРИТИЧЕСКИЕ УЯЗВИМОСТИ (CVSS >= 7.0) ---\n")
                    for pkg, cve in critical_cves:
                        f.write(f"Пакет: {pkg}\n")
                        f.write(f"  ID: {cve['id']} (CVSS: {cve['cvss_score']})\n")
                        f.write(f"  Описание: {cve['description']}\n")
                        f.write(f"  Ссылка: {cve['link']}\n")
                        if pkg in updates_available:
                            f.write(f"  Статус: доступно обновление\n")
                        else:
                            f.write(f"  Статус: обновление не найдено\n")
                        f.write("\n")

                if other_cves:
                    f.write("\n--- ОСТАЛЬНЫЕ УЯЗВИМОСТИ (CVSS < 7.0 или N/A) ---\n")
                    other_by_pkg = {}
                    for pkg, cve in other_cves:
                        other_by_pkg.setdefault(pkg, []).append(cve)
                    for pkg, cves in other_by_pkg.items():
                        cve_list = ", ".join([f"{c['id']} (CVSS: {c['cvss_score']})" for c in cves])
                        f.write(f"Пакет: {pkg} (найдено: {len(cves)} уязвимостей)\n")
                        f.write(f"  {cve_list}\n")
                        if pkg in updates_available:
                            f.write(f"  Статус: доступно обновление\n")
                        else:
                            f.write(f"  Статус: обновление не найдено\n")
                        f.write("\n")
            else:
                f.write("Уязвимостей не найдено.\n")
        else:
            f.write("--- УЯЗВИМОСТИ (CVE) ---\n")
            f.write("Проверка CVE не выполнялась.\n")

        f.write("\n")

        # ---------- Неудачные попытки входа ----------
        f.write("--- НЕУДАЧНЫЕ ПОПЫТКИ ВХОДА ---\n")
        logins = data.get('failed_logins', {})
        if logins:
            for ip, count in sorted(logins.items(), key=lambda x: x[1], reverse=True):
                f.write(f"{ip:20} {count} раз(а)\n")
            f.write(f"Всего IP: {len(logins)}\n")
        else:
            f.write("Неудачных попыток не обнаружено.\n")

        # ---------- Подпись ----------
        f.write("\n" + "="*60 + "\n")
        f.write(f"Должность:               Специалист по информационной безопасности\n")
        f.write(f"Подпись:                 \n")
        f.write(f"ФИО:                     Илья Тришкин\n")
        f.write(f"Дата подписания:         {datetime.now().strftime('%d.%m.%Y')}\n")
        f.write("="*60 + "\n")

    # ---------- JSON-отчёт ----------
    json_path = os.path.join(output_dir, base_name + '.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"Отчёт сохранён: {txt_path}")
    print(f"JSON-отчёт сохранён: {json_path}")

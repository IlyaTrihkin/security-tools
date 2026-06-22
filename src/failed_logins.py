#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from collections import Counter

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

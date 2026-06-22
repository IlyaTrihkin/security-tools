#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import re
import socket
import platform
from datetime import datetime

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

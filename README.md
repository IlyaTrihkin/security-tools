# security-tools

Сборник скриптов для автоматизации задач информационной безопасности.

## Содержание

- **`check_os_updates.py`** — проверяет доступные обновления пакетов в системах на базе apt (Debian/Ubuntu/Astra) или yum (CentOS/RedOS). Умеет выводить результат в текстовом или JSON-формате.

## Установка и использование

### Требования
- Python 3.6+
- Менеджер пакетов apt или yum

### Запуск

Склонируйте репозиторий или скачайте файл.

```bash
python3 check_os_updates.py [--format text|json]

Параметры:

--format, -f — формат вывода: text (по умолчанию) или json.

Примеры:

python3 check_os_updates.py
python3 check_os_updates.py --format json

Пример вывода (JSON):

[
  "openssl",
  "bash",
  "systemd"
]

Планы по развитию
Добавить проверку критических уязвимостей (CVE).

Интеграция с системами мониторинга.

Автор
Илья Тришкин — специалист по информационной безопасности.
GitHub: https://github.com/IlyaTrihkin
TenChat: https://tenchat.ru/ilya_trishkin

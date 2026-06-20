FROM ubuntu:22.04

# Устанавливаем Python и менеджер пакетов
RUN apt update && apt install -y python3 python3-pip sudo && rm -rf /var/lib/apt/lists/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем скрипт
COPY check_os_updates.py log_analyzer.py .

# Даём права на выполнение
RUN chmod +x *.py

# Запускаем скрипт
ENTRYPOINT ["python3"]

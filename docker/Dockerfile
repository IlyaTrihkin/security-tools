FROM ubuntu:22.04

# Устанавливаем Python и менеджер пакетов
RUN apt update && apt install -y python3 python3-pip sudo && rm -rf /var/lib/apt/lists/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем все файлы проекта
COPY . .

# Даём права на выполнение
RUN chmod +x audit.py modules/*.py

# Запускаем скрипт
ENTRYPOINT ["python3", "audit.py"]
CMD ["--help"]

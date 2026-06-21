FROM ubuntu:22.04

# Устанавливаем системные зависимости
RUN apt update && apt install -y python3 python3-pip sudo && rm -rf /var/lib/apt/lists/*

# Устанавливаем Python-зависимости
RUN pip3 install requests packaging

# Создаём рабочую директорию
WORKDIR /app

# Копируем все файлы проекта
COPY . .

# Даём права на выполнение
RUN chmod +x audit.py modules/*.py

# Запускаем скрипт
ENTRYPOINT ["python3", "audit.py"]

# По умолчанию показываем справку, если флаги не переданы
CMD ["--help"]

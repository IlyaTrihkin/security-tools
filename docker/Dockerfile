FROM ubuntu:22.04

RUN apt update && apt install -y python3 python3-pip sudo && rm -rf /var/lib/apt/lists/*

RUN pip3 install requests packaging

WORKDIR /app

COPY . .

RUN chmod +x audit.py src/*.py

ENTRYPOINT ["python3", "audit.py"]
CMD ["--help"]

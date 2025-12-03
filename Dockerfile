FROM python:3.11-alpine

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект включая .env
COPY . .

EXPOSE 8080

# Установка supervisor для управления процессами
RUN apk add --no-cache supervisor

# Создаем директории для supervisor
RUN mkdir -p /etc/supervisor.d /var/log/supervisor

# Конфигурация supervisor
COPY supervisord.conf /etc/supervisor.d/supervisord.ini

CMD ["supervisord", "-c", "/etc/supervisor.d/supervisord.ini"]

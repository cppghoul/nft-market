FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Копируем .env файл
COPY .env .env

EXPOSE 8080

CMD ["python", "app.py"]

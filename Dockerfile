FROM python:3.11-alpine

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект включая .env
COPY . .

EXPOSE 8080

CMD ["python", "app.py"]

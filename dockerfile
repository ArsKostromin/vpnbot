# Dockerfile (Django-приложение)
FROM python:3.11-slim

WORKDIR /app

# Копируем только requirements.txt сначала
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Затем копируем остальной проект
COPY . .

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]

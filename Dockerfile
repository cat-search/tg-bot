FROM python:3.12-slim

# Устанавливаем Poetry
RUN pip install poetry==2.1.2

# Отключаем создание виртуального окружения (используем системный Python)
ENV POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock ./

# Устанавливаем зависимости
RUN poetry install --no-root --no-interaction --no-ansi --only main

# Копируем остальные файлы проекта
COPY . .

CMD ["python", "bot.py"]
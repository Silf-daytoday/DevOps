FROM python:3.12.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Создаём непривилегированного пользователя
RUN groupadd --system --gid 10001 app \
    && useradd --system \
       --uid 10001 \
       --gid app \
       --home-dir /nonexistent \
       --shell /usr/sbin/nologin \
       app

# Устанавливаем зависимости
COPY requirements.txt requirements-container.txt .
RUN python -m pip install --no-cache-dir -r requirements-container.txt

# Копируем исходный код
COPY --chown=app:app app.py domain.py ./
COPY --chown=app:app lr3_tools ./lr3_tools
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app alembic.ini ./

# Контейнер работает без root
USER 10001:10001

EXPOSE 5000

# Проверка работоспособности приложения
HEALTHCHECK --interval=30s \
    --timeout=5s \
    --start-period=30s \
    --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3)"

# Запуск Flask через Gunicorn
STOPSIGNAL SIGTERM

CMD ["gunicorn", \
     "--bind=0.0.0.0:5000", \
     "--workers=2", \
     "--graceful-timeout=30", \
     "--timeout=60", \
     "--access-logfile=-", \
     "--error-logfile=-", \
     "app:app"]

FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

ENV PYTHONPATH=/app

CMD ["python", "tg_work_bot/bot/bot.py"]

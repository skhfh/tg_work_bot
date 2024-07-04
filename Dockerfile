FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY tg_work_bot/ .

CMD ["python", "tg_work_bot.py"]

FROM python:3.13.3-alpine3.21
WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "run.py"]

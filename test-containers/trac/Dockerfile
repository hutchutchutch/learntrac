FROM python:2.7-slim

RUN pip install flask

WORKDIR /app
COPY app.py .

EXPOSE 8000

CMD ["python", "app.py"]
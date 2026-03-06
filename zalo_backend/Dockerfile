FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py .
COPY zalo_verifierOOQHBhE56GrFaOuejh4c5LQCW3Qw-bHWCpGn.html .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    SLOTH_HOST=0.0.0.0 SLOTH_DB=/data/sloth_shoebox.db
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY sloth_shoebox ./sloth_shoebox
COPY docs ./docs
VOLUME /data
EXPOSE 8337
CMD ["python", "-m", "sloth_shoebox"]

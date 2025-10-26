FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 7860
ENV PORT=7860
CMD ["uvicorn", "backend.main_openrouter:app", "--host", "0.0.0.0", "--port", "7860"]

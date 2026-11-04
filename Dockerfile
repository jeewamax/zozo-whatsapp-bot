FROM python:3.12-slim
WORKDIR /app
RUN useradd --uid 10001 --create-home botuser && mkdir /app/data && chown botuser:botuser /app/data
COPY --chown=botuser:botuser bot.py product.json ./
USER botuser
ENV PYTHONUNBUFFERED=1 PORT=8080 BOT_DB=/app/data/messages.sqlite3
EXPOSE 8080
CMD ["python", "bot.py"]

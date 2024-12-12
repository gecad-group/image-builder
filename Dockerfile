FROM python:3.11-slim

WORKDIR /app

RUN pip3 install --no-cache-dir streamlit && pip3 uninstall -y pandas numpy

COPY streamlit-app.py .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "streamlit-app.py", "--server.port=8501", "--server.address=0.0.0.0"]


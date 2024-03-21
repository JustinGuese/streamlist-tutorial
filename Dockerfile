FROM python:3.11-slim
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
WORKDIR /app
COPY Main.py /app
COPY pages/ /app/pages
CMD ["streamlit", "run", "Main.py", "--server.address=0.0.0.0", "--server.port=8501"]
FROM python:3.8-slim
WORKDIR /workspace
COPY . /workspace
RUN pip install -r requirements.txt
CMD ["uvicorn", "workspace.scripts.main:app", "--host", "0.0.0.0", "--port", "80"]

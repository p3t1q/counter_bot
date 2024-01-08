FROM python:3.9
ADD requirements.txt .
RUN pip3 install -r requirements.txt
COPY src src/
ADD bot.py .
CMD ["python3", "./bot.py"]
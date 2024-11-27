FROM python:3.10-slim

RUN apt-get update -y 
RUN apt-get install -y python3-pip 

# Clean up apt cache to reduce image size
RUN rm -rf /var/lib/apt/lists/*

#copy in source code
COPY . /app 

WORKDIR /app 

#install requirements
RUN pip install -r requirements.txt 

ENTRYPOINT ["python3"]

CMD ["application.py"] 
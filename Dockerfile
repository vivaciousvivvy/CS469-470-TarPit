FROM python:3

RUN apt-get update -y 
RUN apt-get install -y python3-pip 

#copy in source code
COPY . /app 

WORKDIR /app 

#install requirements
RUN pip install -r requirements.txt 

ENTRYPOINT ["python3"]

CMD ["application.py"] 
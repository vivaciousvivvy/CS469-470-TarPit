FROM python:3.10-slim

RUN apt-get update -y 
RUN apt-get install -y python3-pip 

# Clean up apt cache to reduce image size
RUN rm -rf /var/lib/apt/lists/*

#copy in source code
COPY . /app 

WORKDIR /app 

#install requirements
#--no-cache-dir helps keep the image size smaller by not caching pip downloads
RUN pip install --no-cache-dir -r requirements.txt 

ENTRYPOINT ["python3"]

CMD ["slack_bot.py"] 
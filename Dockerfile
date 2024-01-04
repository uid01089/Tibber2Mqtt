FROM arm64v8/python:3.12-alpine

# Update system
RUN apk update && apk upgrade && apk add build-base --no-cache

# Create workdir
WORKDIR /app

# Setup requirements, no venv needed
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN apk del build-base

# Copy app itself
COPY . .

# Call script
CMD [ "python", "./Tibber2Mqtt.py" ]

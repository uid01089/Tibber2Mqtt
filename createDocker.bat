pip freeze > requirements.txt
docker build -t tibber2mqtt -f Dockerfile .
docker tag tibber2mqtt:latest docker.diskstation/tibber2mqtt
docker push docker.diskstation/tibber2mqtt:latest
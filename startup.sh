#!/bin/bash

# Make sure certbot config directories exist
mkdir -p ./certbot/conf
mkdir -p ./certbot/www

# Create necessary SSL files first
./update-init-letsencrypt.sh

# Start the containers
docker compose up --build --detach;

crontab -r;
echo "0 0 1,20 * * rm postgres_dump.gz; sudo docker exec -t database pg_dumpall -c | gzip > ./postgres_dump.gz" >> mycron;
crontab mycron;
rm mycron;

docker exec -it database /bin/bash -c ".venv/bin/python3 -m pgmigrate -c '' migrate -t latest";

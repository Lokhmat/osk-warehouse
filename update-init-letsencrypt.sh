#!/bin/bash

if ! [ -x "$(command -v docker compose)" ]; then
  echo 'Error: docker compose is not installed.' >&2
  exit 1
fi

domains=(osk-warehouse.ru www.osk-warehouse.ru)
rsa_key_size=4096
data_path="./certbot"
email="qazxcdews207@yandex.ru" # Your email
staging=0 # Set to 1 for testing

# 1. Create the required directories
if [ ! -d "$data_path/conf" ]; then
  mkdir -p "$data_path/conf"
fi

if [ ! -d "$data_path/www" ]; then
  mkdir -p "$data_path/www"
fi

# 2. Copy SSL configuration files to the correct locations
if [ ! -f "$data_path/conf/options-ssl-nginx.conf" ]; then
  echo "Creating options-ssl-nginx.conf..."
  cat > "$data_path/conf/options-ssl-nginx.conf" << EOF
ssl_session_cache shared:le_nginx_SSL:10m;
ssl_session_timeout 1440m;
ssl_session_tickets off;

ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;

ssl_ciphers "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384";
EOF
fi

if [ ! -f "$data_path/conf/ssl-dhparams.pem" ]; then
  echo "Creating ssl-dhparams.pem..."
  cat > "$data_path/conf/ssl-dhparams.pem" << EOF
-----BEGIN DH PARAMETERS-----
MIIBCAKCAQEA//////////+t+FRYortKmq/cViAnPTzx2LnFg84tNpWp4TZBFGQz
+8yTnc4kmz75fS/jY2MMddj2gbICrsRhetPfHtXV/WVhJDP1H18GbtCFY2VVPe0a
87VXE15/V8k1mE8McODmi3fipona8+/och3xWKE2rec1MKzKT0g6eXq8CrGCsyT7
YdEIqUuyyOP7uWrat2DX9GgdT0Kj3jlN9K5W7edjcrsZCwenyO4KbXCeAvzhzffi
7MA0BM0oNC9hkXL+nOmFg/+OTxIy7vKBg8P+OxtMb61zO7X8vC7CIAXFjvGDfRaD
ssbzSibBsu/6iGtCOGEoXJf//////////wIBAg==
-----END DH PARAMETERS-----
EOF
fi

# 3. Stop any running containers first
docker compose down

# 4. Clean up existing certificates if they exist
if [ -d "$data_path/conf/live/${domains[0]}" ]; then
  echo "Cleaning up existing certificate directories..."
  docker compose run --rm --entrypoint "\
    rm -Rf /etc/letsencrypt/live/${domains[0]}* && \
    rm -Rf /etc/letsencrypt/archive/${domains[0]}* && \
    rm -Rf /etc/letsencrypt/renewal/${domains[0]}*.conf" certbot
fi

# 5. Start with nginx only first
echo "### Starting nginx for initial setup..."
docker compose up --force-recreate -d nginx
echo

# 6. Wait for nginx to be ready
echo "Waiting for nginx to start..."
sleep 5

# 7. Create dummy certificate
echo "### Creating dummy certificate for ${domains[0]} ..."
path="/etc/letsencrypt/live/${domains[0]}"
mkdir -p "$data_path/conf/live/${domains[0]}"
docker compose run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 1\
    -keyout '$path/privkey.pem' \
    -out '$path/fullchain.pem' \
    -subj '/CN=localhost'" certbot
echo

# 8. Reload nginx to use the dummy certificate
docker compose exec nginx nginx -s reload
sleep 2

# 9. Request the real certificate
echo "### Requesting Let's Encrypt certificate for $domains ..."
# Join $domains to -d args
domain_args=""
for domain in "${domains[@]}"; do
  domain_args="$domain_args -d $domain"
done

# Select appropriate email arg
case "$email" in
  "") email_arg="--register-unsafely-without-email" ;;
  *) email_arg="--email $email" ;;
esac

# Enable staging mode if needed
if [ $staging != "0" ]; then staging_arg="--staging"; fi

docker compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $staging_arg \
    $email_arg \
    $domain_args \
    --rsa-key-size $rsa_key_size \
    --agree-tos \
    --force-renewal" certbot
echo

# 10. Find the actual certificate path
echo "### Finding the correct certificate path..."
cert_path=""
docker compose run --rm --entrypoint "\
  find /etc/letsencrypt/live -name fullchain.pem -path \"*/osk-warehouse.ru*\" | sort -r | head -n 1" certbot > cert_path.tmp
cert_path=$(cat cert_path.tmp)
cert_path=$(dirname "$cert_path")
cert_path=${cert_path#/etc/letsencrypt/live/}
rm cert_path.tmp

if [ -z "$cert_path" ]; then
  echo "Error: Could not find certificate path!"
  echo "Using the default path: ${domains[0]}"
  cert_path="${domains[0]}"
else
  echo "Found certificate path: $cert_path"
fi

# 11. Now enable HTTPS in nginx conf with the correct certificate path
echo "Updating nginx config to enable HTTPS with path: $cert_path"
cat > ./nginx/conf.d/app.conf << EOF
server {
    listen 80;
    server_name osk-warehouse.ru www.osk-warehouse.ru;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name osk-warehouse.ru www.osk-warehouse.ru;

    ssl_certificate /etc/letsencrypt/live/$cert_path/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$cert_path/privkey.pem;
    
    # Include SSL configuration
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://app:80;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

echo "### Reloading nginx..."
docker compose exec nginx nginx -s reload

# 12. Start the rest of the services
echo "### Starting all services..."
docker compose up -d 

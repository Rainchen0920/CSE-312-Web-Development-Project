openssl req -x509 -newkey rsa:4096 -keyout nginx/private.key -out nginx/cert.pem -days 365 -sha256 -nodes -subj "/C=US"

mkdir -p keys

if [ ! -f keys/private.pem ]; then
  openssl genrsa -out keys/private.pem 2048
fi

if [ ! -f keys/public.pem ]; then
  openssl rsa -in keys/private.pem -pubout -out keys/public.pem
fi
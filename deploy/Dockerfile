# Build image ERPNext có sẵn custom app (chạy từ thư mục deploy hoặc root có file này).
# docker build -f deploy/Dockerfile -t your-registry/erpnext-food:v15 .
# Trong docker-compose.yml: image: your-registry/erpnext-food:v15

FROM frappe/erpnext:v15

USER frappe
WORKDIR /home/frappe/frappe-bench

RUN bench get-app https://github.com/YOUR_ORG/food_order_app.git --branch main

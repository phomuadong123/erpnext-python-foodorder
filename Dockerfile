FROM frappe/erpnext:v16.7.3

# Copy app của bạn vào thư mục apps
USER frappe
COPY --chown=frappe:frappe ./apps/food_order /home/frappe/frappe-bench/apps/food_order

# Cài đặt app vào môi trường python của bench
RUN cd /home/frappe/frappe-bench && \
    ./env/bin/pip install -e ./apps/food_order
# Food Order App

Hệ thống đặt món trên nền **Frappe / ERPNext** chạy bằng Docker.

**Tài liệu này dành cho Ubuntu Server (production), theo đúng flow của bạn:**
1) deploy stack xong, 2) `exec` vào `backend`, 3) `bench get-app`, 4) `install-app`.

**Cổng public mặc định: `4455`**.

---

## 1) Kiến trúc nhanh

- `db`: MariaDB.
- `redis-cache`, `redis-queue`: Redis cho cache/queue.
- `configurator`: chạy một lần để ghi `common_site_config`.
- `create-site`: tạo site ERPNext lần đầu (bỏ qua nếu site đã tồn tại).
- `backend`, `frontend`, `websocket`, `queue-long`, `queue-short`, `scheduler`: runtime chính.

Compose dùng 2 file:
- `docker-compose.yml`
- `docker-compose.prod.yml`

---

## 2) Chuẩn bị Ubuntu Server

- Ubuntu 22.04/24.04.
- Có quyền `sudo`.
- DNS domain trỏ về IP server (nếu dùng domain).

SSH vào server:

```bash
ssh user@YOUR_SERVER_IP
sudo apt update && sudo apt upgrade -y
```

---

## 3) Cài Docker + Compose plugin

```bash
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Đăng xuất SSH và vào lại, rồi kiểm tra:

```bash
docker --version
docker compose version
```

---

## 4) Clone repo và tạo `.env`

```bash
sudo mkdir -p /opt/an-trua
sudo chown "$USER":"$USER" /opt/an-trua
cd /opt/an-trua
git clone URL_REPO_CAU_HINH .
cp env.template .env
nano .env
```

### Biến bắt buộc trong `.env`

- `MYSQL_ROOT_PASSWORD`: đặt mật khẩu mạnh.
- `ADMIN_PASSWORD`: mật khẩu user Administrator.
- `BASE_URL`: ví dụ `https://your-domain.com:4455` (không có `/` cuối).
- `SITE_NAME`: mặc định `frontend` (hoặc tên bạn muốn).
- `FRONTEND_PORT=4455`.
- `FRONTEND_BIND`:
  - `0.0.0.0`: mở trực tiếp cổng Docker ra ngoài.
  - `127.0.0.1`: chỉ local, dùng reverse proxy (Nginx).

---

## 5) Validate và chạy stack

```bash
cd /opt/an-trua
docker compose -f docker-compose.yml -f docker-compose.prod.yml config
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Lần đầu `create-site` có thể mất vài phút.

Kiểm tra:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs create-site
```

---

## 6) Flow cài app sau khi deploy (đúng yêu cầu của bạn)

Sau khi stack đã lên ổn:

### Bước 1 - Lấy app vào backend

```bash
cd /opt/an-trua
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend \
  bench get-app URL_REPO_CUA_BAN --branch main
```

### Bước 2 - Cài app vào site

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend \
  bench --site frontend install-app food_order_app
```

> Nếu `SITE_NAME` không phải `frontend` thì thay lại cho đúng.

### Bước 3 - Migrate (nếu cần)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend \
  bench --site frontend migrate
```

### Bước 4 - Restart service liên quan

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart \
  backend queue-long queue-short scheduler websocket frontend
```

---

## 7) Expose ra ngoài với cổng 4455

Bạn có 2 cách:

### Cách A - Mở trực tiếp Docker

- `.env`: `FRONTEND_BIND=0.0.0.0`, `FRONTEND_PORT=4455`.
- Mở firewall cổng 4455 (mục bên dưới).
- Truy cập: `http://SERVER_IP:4455` hoặc qua domain.

### Cách B - Dùng Nginx trên host Ubuntu (khuyến nghị production)

- `.env`: `FRONTEND_BIND=127.0.0.1`, `FRONTEND_PORT=4455`.
- Dùng file `deploy/nginx-site.conf` để reverse proxy tới `127.0.0.1:4455`.

Cài Nginx:

```bash
sudo apt install -y nginx
sudo cp /opt/an-trua/deploy/nginx-site.conf /etc/nginx/sites-available/food-order
sudo ln -sf /etc/nginx/sites-available/food-order /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Nhớ sửa trong file Nginx:
- `server_name your-domain.com`
- `ssl_certificate`
- `ssl_certificate_key`

---

## 8) UFW (Ubuntu Firewall)

Nếu public cổng 4455:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 4455/tcp
sudo ufw enable
sudo ufw status
```

---

## 9) Cấu hình domain trong Frappe

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend \
  bench --site frontend set-config host_name your-domain.com
```

Sau đó restart:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart \
  backend queue-long queue-short scheduler websocket frontend
```

---

## 10) Backup cơ bản

Kiểm tra volume:

```bash
docker volume ls
```

Backup DB volume (đổi tên volume theo máy thực tế nếu khác):

```bash
cd /opt/an-trua
docker run --rm \
  -v an-trua_db-data:/data \
  -v "$(pwd)":/backup \
  alpine tar czf /backup/db-data-$(date +%Y%m%d).tgz -C /data .
```

Nên backup thêm volume `sites` và file `.env`.

---

## 11) Troubleshooting nhanh

- `create-site` fail: `docker compose ... logs create-site`.
- Port bận: đổi `FRONTEND_PORT` trong `.env`, chạy lại `up -d`.
- `bench get-app` lỗi repo private: dùng HTTPS + token hoặc SSH key phù hợp.
- Không thấy thay đổi app: chạy `migrate` + restart backend/queue/scheduler.

---

## Contributing

```bash
cd apps/food_order_app
pre-commit install
```

---

## License

MIT

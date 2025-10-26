K# Hướng dẫn cài đặt đơn giản

## Bước 1: Tạo môi trường ảo

```bash
python -m venv venv
```

## Bước 2: Kích hoạt môi trường ảo

```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

## Bước 3: Cài đặt thư viện

```bash
pip install -r requirements-minimal.txt
```

Hoặc cài đặt thủ công:

```bash
pip install fastapi uvicorn pydantic pydantic-settings python-multipart requests python-dotenv pandas numpy wntr
```

## Bước 4: Chạy API

```bash
python main.py
```

## Bước 5: Test

```bash
python test_single_station.py
```

## Truy cập API

- API: <http://localhost:8000>
- Docs: <http://localhost:8000/docs>

## EPANET (Tùy chọn)

```bash
pip install wntr
```

Xong! 🎉

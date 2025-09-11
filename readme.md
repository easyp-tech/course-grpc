# Установка бинарей
```bash
make bin-deps
```

# Генерация кода

## Golang
```bash
easyp generate
```

## python
```bash
easyp --config easyp.python.yaml generate
```

# Установка зависимостей

## Golang

```bash
go mod download
```

## python

```bash
cd python
pip  install -r requirements.txt
```

# Запуск

## Golang

### Server
```bash
go run cmd/server/server.go
```

### Client
```bash
go run cmd/client/client.go
```

## Python

### Server
```bash
cd python
python server.py
```

### Client
```bash
cd python
python client.py
```

*****
# Kafka-Based Backtest Pipeline on AWS EC2 with Docker

This project runs a Python-based Kafka producer and consumer (`backtest.py`) on an AWS EC2 instance using Docker. It uses `kafka_producer.py` to send data to a Kafka topic and `backtest.py` to consume, process, and return JSON results.

---

## 📁 Project Structure

```

project/
│
├── docker-compose.yml
├── kafka\_producer/
│   ├── kafka\_producer.py
│   └── Dockerfile
├── backtest/
│   ├── backtest.py
│   └── Dockerfile

````

---

## 🐳 Docker Compose Setup

### `kafka_producer/Dockerfile`

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY kafka_producer.py .

RUN pip install kafka-python

CMD ["python", "kafka_producer.py"]
````

### `backtest/Dockerfile`

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY backtest.py .

RUN pip install kafka-python

CMD ["python", "backtest.py"]
```

### `docker-compose.yml`

```yaml
version: '3.8'

services:
  zookeeper:
    image: bitnami/zookeeper:latest
    container_name: zookeeper
    ports:
      - "2181:2181"
    environment:
      ALLOW_ANONYMOUS_LOGIN: "yes"

  kafka:
    image: bitnami/kafka:latest
    container_name: kafka
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_CFG_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_CFG_LISTENERS: PLAINTEXT://:9092
      KAFKA_CFG_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      ALLOW_PLAINTEXT_LISTENER: "yes"
    depends_on:
      - zookeeper

  backtest:
    build: ./backtest
    depends_on:
      - kafka

  producer:
    build: ./kafka_producer
    depends_on:
      - kafka
```

---

## 🔧 Modify Python Scripts

In both `kafka_producer.py` and `backtest.py`, set the Kafka broker hostname to Docker's service name:

```python
KAFKA_BROKER = 'kafka:9092'
TOPIC = 'backtest-topic'
```

---

## 🚀 Deploy on EC2 (t3.micro)

1. **Launch EC2 Instance**

   * Type: `t3.micro`
   * AMI: Ubuntu 22.04
   * Open ports: `22`, `9092`, and any others as needed (e.g., `5000`)

2. **Install Docker and Docker Compose**

```bash
sudo apt update
sudo apt install docker.io docker-compose -y
sudo usermod -aG docker $USER
newgrp docker
```

3. **Upload the Project**

From local machine:

```bash
scp -i your-key.pem -r project/ ubuntu@<EC2_PUBLIC_IP>:~/
```

4. **Run the Docker Compose Project**

```bash
cd project
docker-compose up --build
```

---

## 📤 Retrieving output from output.json

```bash
docker cp backtest_container_name:/app/output.json .
```

Or mount a volume in `docker-compose.yml` for persistence.

---

## ✅ Local Development

You can run this entire setup locally (Docker must be installed):

```bash
docker-compose up --build
```

This allows full testing before deploying to EC2.

---

## 🔒 Notes

* Ensure your EC2 security group allows necessary inbound traffic (e.g., ports 22, 9092, 5000).
* Use `tmux` or background services if you run parts manually.
* For production, consider:

  * Using AWS MSK (Managed Kafka)
  * Logging and monitoring with Docker logs or volumes
  * Reverse proxies (e.g., Nginx) for exposing Flask apps

---

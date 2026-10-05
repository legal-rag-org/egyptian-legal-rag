# LegalRAG — Docker Setup

Docker configuration for running the **LegalRAG** application and its supporting services.

The project uses **uv** for Python dependency management and PostgreSQL with **pgvector** for persistent application data.

## Services

| Service               | Purpose                                |
| --------------------- | -------------------------------------- |
| FastAPI               | Main LegalRAG API                      |
| PostgreSQL + pgvector | Relational database and vector storage |
| Qdrant                | Vector database                        |
| Prometheus            | Metrics collection                     |
| Grafana               | Metrics visualization                  |
| Node Exporter         | System-level metrics                   |
| PostgreSQL Exporter   | PostgreSQL metrics                     |

All services communicate through the Docker `backend` network.

---

## Project Structure

```text
docker/
├── docker-compose.yml
├── env/
│   ├── .env.example.app
│   ├── .env.example.postgres
│   ├── .env.example.grafana
│   └── .env.example.postgres-exporter
├── legalrag/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── alembic.example.ini
│   └── alembic.ini
├── nginx
│   └── default.conf
└── prometheus
    └── prometheus.yml
```

Python dependencies are managed from the project root:

```text
pyproject.toml
uv.lock
```

---

## Prerequisites

Make sure the following are installed:

* Docker
* Docker Compose
* Git

No local Python environment is required to run the application through Docker.

---

## Environment Configuration

Create the required environment files from the provided examples:

```bash
cd docker/env

cp .env.example.app .env.app
cp .env.example.postgres .env.postgres
cp .env.example.grafana .env.grafana
cp .env.example.postgres-exporter .env.postgres-exporter
```

Update the generated files with the appropriate values for your environment.

### Security

Do **not** commit files containing secrets to the repository.

Keep credentials and API keys inside local `.env` files or a dedicated secrets-management system.

Example:

```env
POSTGRES_USERNAME=<username>
POSTGRES_PASSWORD=<password>
POSTGRES_HOST=pgvector
POSTGRES_PORT=5432
POSTGRES_MAIN_DATABASE=<database>
```

Inside Docker, services communicate using Docker service names rather than `localhost`.

For example:

```text
pgvector:5432
```

---

## Alembic Configuration

Create the Alembic configuration from the example:

```bash
cd docker/legalrag

cp alembic.example.ini alembic.ini
```

The database URL should reference the PostgreSQL service:

```text
postgresql://<username>:<password>@pgvector:5432/<database>
```

Do not commit an `alembic.ini` containing real database credentials.

---

## Build and Start

From the `docker` directory:

```bash
cd docker

docker compose up --build -d
```

Check the service status:

```bash
docker compose ps
```

View application logs:

```bash
docker compose logs -f fastapi
```

---

## Start Individual Services

Start the core LegalRAG services:

```bash
docker compose up -d fastapi pgvector qdrant
```

Start the monitoring services:

```bash
docker compose up -d prometheus grafana node-exporter postgres-exporter
```

---

## Application

FastAPI is available at:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

Metrics endpoint:

```text
http://localhost:8000/metrics
```

---

## PostgreSQL

PostgreSQL runs using the `pgvector` image.

Inside the Docker network, applications connect to:

```text
pgvector:5432
```

From the host machine, PostgreSQL is exposed through the configured host port.

The PostgreSQL data is persisted using the Docker volume:

```text
pgvector_data
```

### Check PostgreSQL

```bash
docker compose exec pgvector pg_isready
```

Connect to PostgreSQL:

```bash
docker compose exec pgvector psql -U <username> -d <database>
```

List databases:

```sql
\l
```

List tables:

```sql
\dt
```

---

## Qdrant

Qdrant is used as a vector database for similarity search.

Inside Docker:

```text
qdrant:6333
```

From the host:

```text
http://localhost:6333
```

Qdrant dashboard:

```text
http://localhost:6333/dashboard
```

Qdrant data is persisted using:

```text
qdrant_data
```

---

## Monitoring

### Prometheus

Prometheus collects metrics from the application and infrastructure services.

```text
http://localhost:9090
```

### Grafana

Grafana provides dashboards for monitoring.

```text
http://localhost:3000
```

Prometheus can be configured as a Grafana data source using:

```text
http://prometheus:9090
```

### Node Exporter

Node Exporter provides system-level metrics.

```text
http://localhost:9100
```

### PostgreSQL Exporter

PostgreSQL Exporter exposes PostgreSQL metrics to Prometheus.

---

## Python Dependencies

LegalRAG uses **uv** for dependency management.

The main dependency files are:

```text
pyproject.toml
uv.lock
```

The Docker image installs dependencies from the lock file:

```bash
uv sync --frozen --no-dev
```

This ensures that the versions specified in `uv.lock` are used during the Docker build.

To add a dependency locally:

```bash
uv add <package>
```

To remove a dependency:

```bash
uv remove <package>
```

After modifying dependencies, commit both:

```text
pyproject.toml
uv.lock
```

---

## Database Persistence

PostgreSQL uses:

```text
pgvector_data
```

and Qdrant uses:

```text
qdrant_data
```

These volumes allow data to persist when containers are recreated.

Stopping the stack normally does not remove these volumes:

```bash
docker compose down
```

Start the stack again with:

```bash
docker compose up -d
```

### Important

Avoid using:

```bash
docker compose down -v
```

unless you intentionally want to remove the Docker volumes and their stored data.

---

## Database Backup

For PostgreSQL, use PostgreSQL's native backup tools such as `pg_dump` and `pg_restore`.

Example:

```bash
docker compose exec pgvector pg_dump \
  -U <username> \
  -d <database> \
  -F c \
  -f /tmp/database-backup.dump
```

Copy the backup to the host:

```bash
docker cp pgvector:/tmp/database-backup.dump ./database-backup.dump
```

Keep database backups outside the Docker volume and store them securely.

---

## Useful Commands

### Start

```bash
docker compose up -d
```

### Build and start

```bash
docker compose up --build -d
```

### Stop

```bash
docker compose down
```

### Restart FastAPI

```bash
docker compose restart fastapi
```

### View FastAPI logs

```bash
docker compose logs -f fastapi
```

### View PostgreSQL logs

```bash
docker compose logs -f pgvector
```

### View Qdrant logs

```bash
docker compose logs -f qdrant
```

### Check service status

```bash
docker compose ps
```

---

## Troubleshooting

### FastAPI cannot connect to PostgreSQL

Verify that PostgreSQL is running:

```bash
docker compose ps pgvector
```

Check its logs:

```bash
docker compose logs --tail=100 pgvector
```

Inside Docker, make sure the database host is:

```text
pgvector
```

not:

```text
localhost
```

---

### PostgreSQL is not ready

Check:

```bash
docker compose exec pgvector pg_isready
```

Then inspect:

```bash
docker compose logs --tail=100 pgvector
```

---

### Database does not exist

List the available databases:

```bash
docker compose exec pgvector \
  psql -U <username> -c "\l"
```

Verify that the database name in your environment configuration matches the actual PostgreSQL database.

---

### FastAPI container keeps restarting

Check:

```bash
docker compose logs --tail=200 fastapi
```

Also verify:

* Environment variables
* PostgreSQL availability
* Qdrant availability
* Alembic configuration
* Application startup errors

---

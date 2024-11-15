podman network create rekuper
podman run \
    --rm \
    --name rekuper_db \
    --network rekuper \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=changeme \
    -e POSTGRES_RO_USER=telemetry \
    -e POSTGRES_RO_PASSWORD=fero \
    -v ./init-user-db.sh:/docker-entrypoint-initdb.d/init-user-db.sh:z \
    -p 25432:5432 \
    postgres:17 postgres -c log_statement=all

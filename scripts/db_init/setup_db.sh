podman network create rekuper
podman run --network rekuper --rm -e POSTGRES_PASSWORD=changeme -v ./init-user-db.sh:/docker-entrypoint-initdb.d/init-user-db.sh:z -p 25432:5432 postgres:17

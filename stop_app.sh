#!/bin/bash

application_container_name="techbuddy_app"  # This should match the container name in docker-compose.yml
application_image_name="techbuddy-app:latest"  # This should match the image name in docker-compose.yml
postgres_container_name="techbuddy_postgres"  # This should match the container name in docker-compose.yml
postgres_image_name="postgres:latest"  # This should match the image name in docker-compose.yml
minio_container_name="techbuddy_minio"  # This should match the container name in docker-compose.yml
minio_image_name="minio/minio:latest"  # This should match the image name in docker-compose.yml

echo "[~] Stopping TechBuddy application container: $application_container_name"
# Stop the application container
docker stop $application_container_name
if [ $? -eq 0 ]; then
    echo "[+] Successfully stopped the application container."
else
    echo "[-] Failed to stop the application container. It may not be running."
fi

echo "[~] Removing TechBuddy application container: $application_container_name"
# Remove the application container
docker rm $application_container_name
if [ $? -eq 0 ]; then
    echo "[+] Successfully removed the application container."
else
    echo "[-] Failed to remove the application container. It may have already been removed."
fi

echo "[~] Removing TechBuddy application image: $application_image_name"
# Remove the associated images
docker rmi $application_image_name
if [ $? -eq 0 ]; then
    echo "[+] Successfully removed the application image."
else
    echo "[-] Failed to remove the application image. It may have already been removed."
fi

echo "[~] Stopping PostgreSQL container: $postgres_container_name"
# Stop the PostgreSQL container
docker stop $postgres_container_name
if [ $? -eq 0 ]; then
    echo "[+] Successfully stopped the PostgreSQL container."
else
    echo "[-] Failed to stop the PostgreSQL container. It may not be running."
fi

echo "[~] Removing TechBuddy PostgreSQL container: $postgres_container_name"
# Remove the PostgreSQL container
docker rm $postgres_container_name
if [ $? -eq 0 ]; then
    echo "[+] Successfully removed the PostgreSQL container."
else
    echo "[-] Failed to remove the PostgreSQL container. It may have already been removed."
fi

echo "[~] Removing TechBuddy PostgreSQL image: $postgres_image_name"
# Remove the associated images
docker rmi $postgres_image_name
if [ $? -eq 0 ]; then
    echo "[+] Successfully removed the PostgreSQL image."
else
    echo "[-] Failed to remove the PostgreSQL image. It may have already been removed."
fi


# Add commands to stop and remove MinIO container and image
echo "[~] Stopping MinIO container: $minio_container_name"
docker stop $minio_container_name
if [ $? -eq 0 ]; then
    echo "[+] Successfully stopped the MinIO container."
else
    echo "[-] Failed to stop the MinIO container. It may not be running."
fi

echo "[~] Removing TechBuddy MinIO container: $minio_container_name"
docker rm $minio_container_name
if [ $? -eq 0 ]; then
    echo "[+] Successfully removed the MinIO container."
else
    echo "[-] Failed to remove the MinIO container. It may have already been removed."
fi

echo "[~] Removing TechBuddy MinIO image: $minio_image_name"
docker rmi $minio_image_name
if [ $? -eq 0 ]; then
    echo "[+] Successfully removed the MinIO image."
else
    echo "[-] Failed to remove the MinIO image. It may have already been removed."
fi
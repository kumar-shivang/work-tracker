#!/bin/bash
set -e

SERVICE_FILE="personal-assistant.service"
SYSTEMD_DIR="/etc/systemd/system"
SERVICE_NAME="personal-assistant"

echo "Copying $SERVICE_FILE to $SYSTEMD_DIR..."
sudo cp "$SERVICE_FILE" "$SYSTEMD_DIR/"

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Restarting $SERVICE_NAME service..."
sudo systemctl restart "$SERVICE_NAME"

echo "Checking service status..."
sudo systemctl status "$SERVICE_NAME" --no-pager

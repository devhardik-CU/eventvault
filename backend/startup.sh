#!/usr/bin/env bash
# Azure App Service (Linux) startup command for the API.
# 1) Install Microsoft's ODBC driver if missing (needed for Azure SQL). UNTESTED here: no Azure/Docker in the dev sandbox.
# 2) Start the API with gunicorn + uvicorn workers.
set -e
if ! odbcinst -q -d 2>/dev/null | grep -q "ODBC Driver 18 for SQL Server"; then
  curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
  . /etc/os-release
  echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/${ID}/${VERSION_ID}/prod ${VERSION_CODENAME} main" > /etc/apt/sources.list.d/mssql-release.list
  apt-get update
  ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc
fi
exec gunicorn -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --timeout 120 app.main:app

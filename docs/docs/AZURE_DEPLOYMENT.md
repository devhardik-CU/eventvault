# Azure Deployment Guide

> **Status: prepared, NOT executed.** No Azure resources were created and no Azure account was used. The commands below follow Azure's documented CLI usage but were never run by me, so check each with `--help` if one errors. Nothing here should be run without you deciding to spend (or not spend) money.

## 0. Cost warning (read first)
| Service | Free option | Catch |
|---|---|---|
| Azure SQL Database | The **free offer**: 100,000 vCore-seconds and 32 GB per month, for the life of the subscription | Choose **"Auto-pause the database until next month"** when the limit is reached; the other option bills you. **The "Azure for Students Starter" offer is documented as incompatible**: use "Azure for Students" or a Free account instead. Apply the offer on the portal's create page (banner "Apply offer"). |
| Static Web Apps (frontend) | **Free plan** (100 GB bandwidth/month, free TLS certificate) | No SLA |
| App Service (backend) | F1 Free plan exists but is heavily limited (shared CPU, daily quota, no custom domains) | B1 and above **cost money** every month |
| Blob Storage (posters) | Not permanently free | Tiny cost for a few images; free-account credits may cover it |

When finished experimenting, delete everything: `az group delete --name eventvault-rg` (**destructive**, removes all resources in the group).

Pick variables once (replace the `<...>` values; names must be globally unique):
```bash
RG=eventvault-rg; LOC=<region e.g. centralindia>; SQLSRV=<unique-sql-server-name>; DB=eventvault
STORE=<uniquestorage24chars>; API=<unique-api-name>; WEB=eventvault-web
```

## 1. Azure SQL Database
1. Portal → **Create a resource → SQL Database**. Create a new logical server with **SQL authentication** (choose an admin user and a strong password; store them in a password manager, never in Git). Use **Apply offer** for the free database and select *Auto-pause*.
2. **Networking** (security): leave **public access with firewall rules**, do *not* allow "any IP". Under the server's Networking page add:
   - your own IP (to run the setup scripts): `az sql server firewall-rule create -g $RG -s $SQLSRV -n my-ip --start-ip-address <YOUR.IP> --end-ip-address <YOUR.IP>`
   - the backend's outbound IPs (step 3). The "Allow Azure services" toggle is simpler but opens the server to *all* Azure customers' services, so avoid it if you can.
   - Set minimal TLS 1.2: `az sql server update -g $RG -n $SQLSRV --minimal-tls-version 1.2`
3. **Create the tables** (as admin, in Azure Data Studio, SSMS or `sqlcmd`), running in order: `database/sqlserver/01_schema.sql`, `02_view.sql`, `03_trigger.sql`, `04_seed_lookups.sql`. *Alternative:* from `backend/`, with `DATABASE_URL` pointing at Azure SQL and `ENVIRONMENT=production`, run `python -m app.db_objects`. This needs the Microsoft ODBC Driver 18 on your computer.
4. **Least-privilege login for the app** (run on the `eventvault` database as admin):
```sql
CREATE USER eventvault_app WITH PASSWORD = '<long-random-password>';
ALTER ROLE db_datareader ADD MEMBER eventvault_app;
ALTER ROLE db_datawriter ADD MEMBER eventvault_app;
```
5. Connection string for the app (`DATABASE_URL`):
`mssql+pyodbc://eventvault_app:<PASSWORD>@<SQLSRV>.database.windows.net:1433/eventvault?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no`
(URL-encode special characters in the password, e.g. `@` → `%40`.)

> **Do not run `python -m app.seed` against production.** It creates demo accounts with a known password.

## 2. Azure Blob Storage
```bash
az storage account create -g $RG -n $STORE -l $LOC --sku Standard_LRS --kind StorageV2 \
   --allow-blob-public-access false --min-tls-version TLS1_2
az storage container create --account-name $STORE -n event-posters --auth-mode login
az storage account show-connection-string -g $RG -n $STORE --query connectionString -o tsv
```
The container stays **private**; the API streams posters to browsers. Keep the connection string secret (it is a full-access key).

## 3. Backend (App Service, Linux, Python 3.12)
```bash
az appservice plan create -g $RG -n eventvault-plan --is-linux --sku B1      # B1 costs money; F1 is free but limited
az webapp create -g $RG -p eventvault-plan -n $API --runtime "PYTHON:3.12"
az webapp update -g $RG -n $API --https-only true                           # HTTPS only
az webapp config set -g $RG -n $API --min-tls-version 1.2 --ftps-state Disabled --startup-file "bash startup.sh"
az webapp config appsettings set -g $RG -n $API --settings \
   ENVIRONMENT=production SCM_DO_BUILD_DURING_DEPLOYMENT=true STORAGE_BACKEND=azure \
   SECRET_KEY="<output of: python -c 'import secrets; print(secrets.token_urlsafe(48))'>" \
   DATABASE_URL="<connection string from step 1>" \
   AZURE_STORAGE_CONNECTION_STRING="<from step 2>" AZURE_STORAGE_CONTAINER=event-posters \
   CORS_ORIGINS="https://<your-static-web-app-hostname>"
az webapp show -g $RG -n $API --query possibleOutboundIpAddresses -o tsv     # add these to the SQL firewall (step 1)
cd backend && zip -r ../backend.zip . -x ".venv/*" "tests/*" "*.db" "__pycache__/*" "uploads/*" ".env"
az webapp deploy -g $RG -n $API --src-path ../backend.zip --type zip
```
Notes:
- **`STORAGE_BACKEND=azure` is required**: files saved to the App Service's disk are not durable.
- In production the app **refuses to start** with the default secret key, a short key, or `*` in CORS, and with `STORAGE_BACKEND=azure` but no connection string.
- `startup.sh` installs Microsoft's ODBC Driver 18 if missing, then starts gunicorn. **I could not confirm which ODBC drivers the App Service image ships today, and this script is untested.** If the app logs "Can't open lib 'ODBC Driver 18'", read the log (`az webapp log tail -g $RG -n $API`); the fallback is deploying the backend as a container image that installs `msodbcsql18`.
- Also set secrets via **Key Vault references** later if you want stricter secret handling.

## 4. Frontend (Static Web Apps, Free plan)
1. Edit `frontend/public/staticwebapp.config.json`: replace both `YOUR-BACKEND.azurewebsites.net` with your API hostname (this sets the Content-Security-Policy).
2. Build and deploy:
```bash
cd frontend && VITE_API_URL=https://$API.azurewebsites.net npm run build
az staticwebapp create -g $RG -n $WEB -l <supported-region e.g. eastasia> --sku Free
TOKEN=$(az staticwebapp secrets list -g $RG -n $WEB --query properties.apiKey -o tsv)
npx @azure/static-web-apps-cli deploy ./dist --deployment-token "$TOKEN" --env production
```
3. Copy the site's hostname into the backend's `CORS_ORIGINS` (exact `https://...` origin, no trailing slash) and restart the web app.

HTTPS is automatic on Static Web Apps; the API is HTTPS-only via the setting above.

## 5. Verify the deployment
1. `curl https://$API.azurewebsites.net/api/health` → `{"status":"ok"}`; open `/docs` for Swagger.
2. `curl -I http://$API.azurewebsites.net/api/health` → redirects/refuses plain HTTP.
3. Open the website, create an organizer account, create an event with a poster → confirm the blob appears in the `event-posters` container.
4. Register as a participant in a second browser; confirm the organizer's analytics change.
5. In SQL: `SELECT TOP 20 * FROM activity_logs ORDER BY id DESC;`
6. Run the real-SQL-Server test suite (see README) against a **separate, empty test database** named with "test" in it.

## 6. Migrations
This project has no migration tool. For schema changes: edit `models.py`, regenerate the scripts (`python database/generate_sqlserver_schema.py`), and write a small `ALTER TABLE` script for the live database. Adopting **Alembic** is the recommended next step.

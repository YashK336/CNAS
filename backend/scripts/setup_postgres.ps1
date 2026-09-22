# Creates the CNAS application database/user in local PostgreSQL 17.
# Usage (PowerShell):
#   $env:PGPASSWORD = "your-postgres-superuser-password"
#   .\backend\scripts\setup_postgres.ps1

$ErrorActionPreference = "Stop"

$psql = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
if (-not (Test-Path $psql)) {
    throw "psql not found at $psql. Install PostgreSQL 17 first."
}

if (-not $env:PGPASSWORD) {
    throw "Set PGPASSWORD to the postgres superuser password before running this script."
}

$sql = @"
DO `$`$`$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'cnas') THEN
        CREATE ROLE cnas LOGIN PASSWORD 'cnas';
    END IF;
END
`$`$`$;

SELECT 'CREATE DATABASE cnas OWNER cnas'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'cnas')\gexec

GRANT ALL PRIVILEGES ON DATABASE cnas TO cnas;
"@

& $psql -U postgres -h localhost -v ON_ERROR_STOP=1 -c $sql
Write-Host "CNAS database ready at postgresql://cnas:cnas@localhost:5432/cnas"
Write-Host "Set CNAS_USE_MEMORY_STORE=0 in backend/.env and restart uvicorn."

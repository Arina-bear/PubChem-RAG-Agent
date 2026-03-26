set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
  CREATE DATABASE ${APP_DB};
EOSQL
echo "✅ База данных ${APP_DB} создана"
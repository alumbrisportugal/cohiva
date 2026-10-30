#!/bin/sh
# Only the named disposable project. Never use this script for production.
# Password expansion is deliberately inside the container; host redirects run as the invoking user.
# shellcheck disable=SC2016,SC2024
set -eu
cd /volume1/docker/alumbris-living-test-20261030
umask 077
project=alumbris-living-test-20261030
docker=/usr/local/bin/docker
compose=/var/packages/ContainerManager/target/usr/bin/docker-compose
dc() { sudo -n "$compose" -p "$project" -f compose.yaml "$@"; }
[ ! -e backup-rehearsal ] || { echo 'Backup rehearsal already exists; preserve evidence'; exit 1; }
mkdir backup-rehearsal
chmod 700 backup-rehearsal
# Seed a harmless file to prove recovery of the data volume as well as SQL.
dc exec -T web sh -c 'printf "synthetic-recovery-sentinel\n" > /data/recovery-sentinel'
dc exec -T db sh -c 'exec mariadb-dump --single-transaction --routines --events -uroot -p"$MARIADB_ROOT_PASSWORD" living_django_test' > backup-rehearsal/database.sql
sudo -n "$docker" run --rm --network none --memory=256m -v "${project}_data:/data:ro" -v "$PWD/backup-rehearsal:/backup" alumbris-living-test:141ae832 tar -C /data -czf /backup/data.tar.gz .
tar -czf backup-rehearsal/configuration.tar.gz .env source/django/cohiva/base_config.py source/django/cohiva/settings.py source/django/cohiva/settings_living.py source/django/cohiva/oauth2/oidc.key source/django/cohiva/saml2/private.key source/django/cohiva/saml2/public.pem
# Restore into another MariaDB container and volume with networking disabled.
# Retain the same schema name: views must resolve against recovered tables, not the original DB.
restore_container=${project}-restore-db
restore_db_volume=${project}_restore_db
[ -z "$(sudo -n "$docker" ps -aq --filter name="^${restore_container}$")" ]
[ -z "$(sudo -n "$docker" volume ls -q --filter name="^${restore_db_volume}$")" ]
python3 -c 'from pathlib import Path; values=dict(line.split("=",1) for line in Path(".env").read_text().splitlines()); Path("backup-rehearsal/restore.env").write_text("MARIADB_ROOT_PASSWORD="+values["DB_ROOT_PASSWORD"]+"\nMARIADB_DATABASE=living_django_test\nMARIADB_USER=living\nMARIADB_PASSWORD="+values["DB_PASSWORD"]+"\n")'
chmod 600 backup-rehearsal/restore.env
sudo -n "$docker" volume create "$restore_db_volume" >/dev/null
sudo -n "$docker" run -d --name "$restore_container" --network none --memory=768m --env-file backup-rehearsal/restore.env -v "$restore_db_volume:/var/lib/mysql" mariadb:11.8 >/dev/null
attempt=0
until sudo -n "$docker" exec "$restore_container" healthcheck.sh --connect --innodb_initialized >/dev/null 2>&1; do
  attempt=$((attempt+1)); [ "$attempt" -lt 60 ] || exit 1; sleep 2
done
sudo -n "$docker" exec -i "$restore_container" sh -c 'exec mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" living_django_test' < backup-rehearsal/database.sql
query='SELECT COUNT(*) FROM geno_building; SELECT COUNT(*) FROM geno_rentalunit; SELECT COUNT(*) FROM geno_address; SELECT COUNT(*) FROM geno_contract; SELECT COUNT(*) FROM geno_contract_contractors; SELECT COUNT(*) FROM geno_contract_rental_units; SELECT COUNT(*) FROM geno_residentmaintenancerequest; SELECT COUNT(*) FROM geno_residentmaintenancecomment; SELECT COUNT(*) FROM auditlog_logentry; SELECT COUNT(*) FROM geno_TenantsView; CHECKSUM TABLE geno_building, geno_rentalunit, geno_address, geno_contract, geno_contract_contractors, geno_contract_rental_units, geno_residentmaintenancerequest, geno_residentmaintenancecomment, auditlog_logentry;'
printf '%s\n' "$query" | dc exec -T db sh -c 'exec mariadb -N -uroot -p"$MARIADB_ROOT_PASSWORD" living_django_test' > backup-rehearsal/original-counts.txt
printf '%s\n' "$query" | sudo -n "$docker" exec -i "$restore_container" sh -c 'exec mariadb -N -uroot -p"$MARIADB_ROOT_PASSWORD" living_django_test' > backup-rehearsal/restored-counts.txt
cmp backup-rehearsal/original-counts.txt backup-rehearsal/restored-counts.txt
# A separate restore volume. No existing project volume is removed or replaced.
[ -z "$(sudo -n "$docker" volume ls -q --filter name="^${project}_restore$")" ]
sudo -n "$docker" volume create "${project}_restore" >/dev/null
sudo -n "$docker" run --rm --network none --memory=256m -v "${project}_restore:/restore" -v "$PWD/backup-rehearsal:/backup:ro" alumbris-living-test:141ae832 sh -c 'tar -xzf /backup/data.tar.gz -C /restore && test "$(cat /restore/recovery-sentinel)" = synthetic-recovery-sentinel && test -s /restore/test-credentials.json'
sudo -n "$docker" run --rm --network "container:$restore_container" --memory=768m -e PYTHONPATH=/cohiva --env-file .env --env-file backup-rehearsal/restore.env -v "$PWD/source/django:/cohiva:ro" -v "$PWD/verify_restored.py:/work/verify_restored.py:ro" -v "${project}_restore:/data" -w /cohiva alumbris-living-test:141ae832 python /work/verify_restored.py
mkdir backup-rehearsal/configuration-restored
tar -xzf backup-rehearsal/configuration.tar.gz -C backup-rehearsal/configuration-restored
cmp .env backup-rehearsal/configuration-restored/.env
cmp source/django/cohiva/oauth2/oidc.key backup-rehearsal/configuration-restored/source/django/cohiva/oauth2/oidc.key
cmp source/django/cohiva/saml2/private.key backup-rehearsal/configuration-restored/source/django/cohiva/saml2/private.key
sha256sum backup-rehearsal/database.sql backup-rehearsal/data.tar.gz backup-rehearsal/configuration.tar.gz > backup-rehearsal/checksums.txt
sudo -n "$docker" rm -f "$restore_container" >/dev/null
sudo -n "$docker" volume rm "$restore_db_volume" >/dev/null
sudo -n "$docker" volume rm "${project}_restore" >/dev/null
echo 'RECOVERY_REHEARSAL_PASS: SQL counts/relations/audit, data sentinel, credentials, settings and private keys restored; temporary restore database and volume removed'

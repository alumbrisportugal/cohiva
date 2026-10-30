#!/bin/sh
# Rehearsal ONLY for this code-only update, inside the isolated test project.
set -eu
# shellcheck disable=SC2016
project=alumbris-living-test-20261030
cd /volume1/docker/alumbris-living-test-20261030
docker=/usr/local/bin/docker
compose=/var/packages/ContainerManager/target/usr/bin/docker-compose
previous=cohiva-141ae832ec10a75ac8ae97dfae8e6b2c3e716574
[ -d "$previous/django/cohiva" ]
for file in base_config.py settings.py settings_living.py oauth2/oidc.key saml2/private.key saml2/public.pem; do
  cp "source/django/cohiva/$file" "$previous/django/cohiva/$file"
done
sudo -n "$docker" run --rm --network none --memory=768m --env-file .env -v "$PWD/$previous/django:/cohiva:rw" -v "${project}_data:/data" -w /cohiva alumbris-living-test:141ae832 python setup.py --use-default-certs
cat > rollback.yaml <<'YAML'
services:
  web:
    volumes:
      - ./cohiva-141ae832ec10a75ac8ae97dfae8e6b2c3e716574/django:/cohiva:ro
YAML
sudo -n "$compose" -p "$project" -f compose.yaml -f rollback.yaml up -d --no-deps --force-recreate web
actual=$(sudo -n "$docker" inspect --format '{{range .Mounts}}{{if eq .Destination "/cohiva"}}{{.Source}}{{end}}{{end}}' "${project}-web-1")
[ "$actual" = "$PWD/$previous/django" ]
# HTTP verification is from the TLS container namespace and validates the exact test CA.
verify() {
  sudo -n "$docker" run --rm --network "container:${project}-tls-1" --memory=256m -e EXPECTED_STATUS="$1" -v "${project}_tls:/tls:ro" alumbris-living-test:141ae832 python -c 'import os,time,requests; s=requests.Session(); s.verify="/tls/caddy/pki/authorities/local/root.crt"; expected=int(os.environ["EXPECTED_STATUS"]); good=False
for attempt in range(30):
 try:
  r=s.get("https://localhost:18443/geno/living/",allow_redirects=False,timeout=10)
  if r.status_code==expected: good=True; break
 except requests.RequestException: pass
 time.sleep(2)
assert good, "Unexpected management route after code switch"
assert s.get("https://localhost:18443/geno/resident/portal/",allow_redirects=False,timeout=10).status_code==302
print("CODE_SWITCH_HTTP_PASS",expected)'
}
# Always return to the candidate even if the previous revision's probe fails.
result=0
verify 404 || result=1
sudo -n "$compose" -p "$project" -f compose.yaml up -d --no-deps --force-recreate web
verify 302 || result=1
[ "$result" = 0 ]
echo 'ROLLBACK_REHEARSAL_PASS: previous code then candidate restored, same DB/volumes, no schema changes'

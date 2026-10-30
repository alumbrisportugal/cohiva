# Ensaio isolado no DS220+

Exclusivo de staging descartável. Não é um instalador comercial nem configuração financeira homologada.

O primeiro ensaio usa `/volume1/docker/alumbris-living-test-20261030`, projeto Container Manager com o mesmo nome, código candidato em `source/` e imagem de dependências `alumbris-living-test:141ae832` construída pelo Dockerfile nativo, target `cohiva-platform-django`. O bind mount de código é só de leitura durante o serviço. A tag refere a base de dependências, **não** a revisão do código montado; o relatório deve identificar ambos. Os novos scripts de teste são sobreposições auditáveis da branch.

## Configuração e arranque

- `.env` contém `DB_PASSWORD`, `DB_ROOT_PASSWORD` e `DJANGO_SECRET_KEY` aleatórios, fora de Git; diretório 0700 e ficheiro 0600. No DSM, verificar também ACLs herdadas: `chmod` só por si pode não retirar direitos de uma ACL. Alterar apenas ACLs do novo diretório de teste.
- `base_config.py` e `settings_living.py` são copiados para `source/django/cohiva/`. O `setup.py` nativo gera settings, ligações a templates e chaves OIDC/SAML numa inicialização com o código temporariamente gravável; o serviço web usa depois código read-only.
- Primeiro arranque de uma base vazia: `migrate --noinput --skip-checks`, seguido obrigatoriamente de `check`. O Unfold faz verificações de permissões antes de existirem as tabelas; não usar `--skip-checks` como aprovação de verificações.
- `collectstatic --noinput` escreve no volume `data`; apenas depois se iniciam web e TLS. Um worker Gunicorn. O ensaio não inicia workers Celery nem envia correio real.
- MariaDB e Redis não publicam portas no host. Caddy publica apenas `127.0.0.1:18443`, com CA própria, sem mudar certificados ou reverse proxies existentes. Acesso remoto de utilizadores não está disponibilizado por esta configuração.
- `cpu_shares` é uma prioridade relativa, não um teto de CPU. O kernel observado recusa `cpus`/NanoCPUs. Limites de RAM definidos por serviço; confirmar aplicação efetiva via inspeção Docker e medir o consumo.
- Ativar EUR apenas nesta base dedicada. O backend financeiro de staging é `DummyBook`; os resultados não comprovam pagamentos, reconciliação ou contabilização persistente.

## Ensaios reproduzíveis

- `seed_synthetic.py`: executado através de `manage.py shell` com settings de staging, cria sete contratos de ensaio, utilizadores e tokens temporários. Credenciais apenas em `/data/test-credentials.json` (0600); recusa reset silencioso.
- `settings_living_tests.py`: testes Django com **migrações reais MariaDB** numa base de teste separada. Desativa redirect HTTPS só para o test client; não altera o serviço web. O utilizador SQL deve ter privilégio somente sobre a base de testes além da base de staging.
- `http_smoke.py`: pedidos HTTPS reais, com validação da CA exata de Caddy, entre dois residentes; contratos, frações, pedidos e comentários, incluindo acessos negativos.
- `browser-smoke.cjs`: Playwright/Chromium em contentor descartável, login, novo arrendamento, consulta desktop/mobile e ausência de acesso anónimo. A exceção de certificado de navegador aplica-se só à CA interna de ensaio; a cadeia TLS é verificada separadamente no ensaio HTTPS.
- `recovery-rehearsal.sh`: backup SQL, volume de dados, configuração/segredos/chaves; restauro numa segunda MariaDB com rede desligada e num volume separado, comparação de contagens/checksums, relações, auditoria e view, ficheiro sentinela e chaves. Remove apenas os recursos de restauro criados por si após sucesso. Conserva backups protegidos para análise. Verifica também consultas autenticadas do Django contra a base recuperada. Não prova recuperação de documentos reais nem o serviço completo após desastre.

Não executar limpeza global Docker. Preservar evidências e manter PR em draft até homologar todos os oito cenários da matriz.

- O restauro deve criar a conta SQL `living` antes de consultar views com esse `DEFINER`; não basta recuperar as tabelas como root. A primeira execução detetou e corrigiu essa dependência.
- `rollback-rehearsal.sh` troca o código do web para a base `141ae832`, verifica HTTP e regressa ao candidato mantendo volumes/DB. Este ensaio cobre apenas a atualização de código sem migrações novas; não generaliza para esquemas incompatíveis.

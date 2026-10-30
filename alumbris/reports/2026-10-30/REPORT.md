# Primeiro marco operacional — Alumbris Living Premium

**Data:** 30/10/2026. **Resultado:** candidato de desenvolvimento instalado e ensaiado no DS220+; **não homologado comercialmente**. PR #1 permanece draft; nenhuma alteração a `develop` ou à produção.

## Versão e âmbito

Base recebida: `141ae832ec10a75ac8ae97dfae8e6b2c3e716574`.
Primeiro commit publicado nesta execução: `b5b214247a9f3ecc2a5d4fbf9d9239db46d0f678`.
Este relatório acompanha a consolidação dos scripts/evidências e a correção de login de residentes, aplicados e testados como sobreposição do candidato antes de publicar o commit que contém este ficheiro.

Imagem de dependências construída no NAS pelo Dockerfile Cohiva, target `cohiva-platform-django`: `alumbris-living-test:141ae832`, ID inicial `36fc1069602c`. Código candidato montado read-only no web. A tag da imagem identifica a base de dependências; não é prova da revisão de código montado. Não foi criada uma stack paralela ao Django/MariaDB/Redis existentes no repositório.

Percurso demonstrado: `/geno/living/` → novo edifício ou edifício existente → nova fração → novo contacto ou contacto existente → contrato em proposta/assinado → consulta na carteira e detalhe. Gravação atómica, validação de datas/valores, auditoria nativa, permissões explícitas e CSRF. Não cria automaticamente contas/convidados nem documentos fiscais. Renda é configuração atual da fração; não equivale a snapshot histórico contratual.

## Hardware e isolamento observados

- DS220+, Intel Celeron J4025, AMD64, 18 GB RAM.
- DSM real: **7.4.1-90080 Update 1**. A referência DSM 7.2.1 não foi ensaiada nem inferida.
- Projeto novo no Container Manager: `alumbris-living-test-20261030`.
- Quatro serviços: web (1 worker Gunicorn), MariaDB 11.8, Redis 7 e Caddy. Volumes e rede prefixados pelo projeto.
- Sem portas de MariaDB/Redis/web no host; única publicação: **127.0.0.1:18443**, HTTPS com CA exclusiva do teste. Não existe acesso remoto público disponibilizado por este ensaio.
- Limites RAM verificados em Docker: web 1536 MiB, DB 768 MiB, Redis/TLS 128 MiB cada. O kernel recusa quotas NanoCPUs; `cpu_shares` configurado é prioridade relativa, não limite garantido.
- Credenciais temporárias fora de Git, diretório 0700 e `.env` 0600 após retirar ACL herdada apenas nesses novos caminhos. Chaves de teste geradas localmente; nenhum segredo de produção reutilizado.

## Evidências funcionais

| Verificação | Resultado e evidência |
|---|---|
| Local, 14 testes do percurso e login | Aprovados; SQLite para retorno rápido, sem migrações SQL específicas |
| Local, 25 testes leves anteriores | Aprovados; integridade pt-PT/políticas/guards |
| Ruff, ShellCheck e sintaxe Node/shell | Aprovados nos ficheiros alterados |
| NAS, primeira suite de 12 testes | Aprovados com migrações reais MariaDB; [registo](mariadb-tests-12.txt) |
| NAS, suite final de 14 testes | Aprovados no NAS com MariaDB/migrações reais, incluindo os dois testes de login: [registo](mariadb-tests-14.txt) |
| Migrações e Django check da instalação | Aplicadas no NAS; sem erros de check. Quatro avisos Wagtailmenus preexistentes sobre painéis de snippets; avisos de dependências registados |
| HTTPS real, CA validada | Aprovado; dois residentes, isolamento de contratos/frações/avarias/comentários e rejeição CSRF: [resultado](http-result.json) |
| Chromium real no NAS | Aprovado; login, criação de contrato, consulta, desktop 1440 px, mobile 390 px sem overflow, anonimato, login do residente e recusa da gestão global: [resultado](browser-result.json) |
| Capturas reais | [Desktop](contract-desktop.png) e [mobile](contract-mobile.png), dados fictícios; mobile inspecionado visualmente |
| Restauro independente | Aprovado: segunda MariaDB sem rede, contagens e checksums de entidades/relações/auditoria, consulta de view, volume de dados/sentinela, credenciais de teste, configuração e chaves; consulta Django autenticada à base recuperada: [registo](recovery.txt) |
| Limpeza da recuperação | Contentor e volumes temporários de restauro removidos; backups protegidos e evidência preservados |
| Rollback específico | Aprovado: código `141ae832` montado e verificado via HTTP; regresso ao candidato, mesmos dados/volumes: [registo](rollback.txt) |

O navegador usa exceção apenas para a CA interna de ensaio; o teste HTTP verifica a cadeia com a raiz exata de Caddy. Isto não valida uma cadeia pública nem disponibilização a residentes reais.

## Amostra de desempenho

Após os ensaios: 20 consultas HTTPS autenticadas sequenciais, 20 respostas válidas; mediana **17,32 ms**, p95 **27,15 ms**, máximo **4169,56 ms** (inclui arranque/aquecimento). [Resultado bruto](performance.json). É uma amostra de um único cliente, não um teste de carga ou promessa de capacidade.

Snapshot posterior: web 215,5 MiB, DB 364,1 MiB, Redis 3,7 MiB, TLS 14,0 MiB; cerca de 598 MiB no total. [Recursos](resources.txt). Os contadores Block I/O apresentados pelo Docker eram 0B; isso não demonstra ausência de atividade física de disco. Sem OOM observado. CPU sem quota dura neste kernel.

## Falhas encontradas e corrigidas

1. `cpus`/NanoCPUs impedia arrancar no kernel deste DSM; substituído por prioridades relativas e medição, mantendo limites de RAM.
2. O bootstrap `setup.py` precisa de escrever ligações/configuração/chaves. Inicialização com mount gravável separado; serviço web normal usa read-only.
3. A primeira migração vazia encontrava verificações Unfold antes de existir `auth_permission`. Sequência usada: `migrate --skip-checks`, imediatamente seguido de `check`; os checks não foram dispensados como critério de aprovação.
4. `/geno/resident/` era desviado para o login administrativo. O middleware agora preserva o login do portal para residentes; testado localmente e no Chromium com uma conta não-staff.
5. O restauro das tabelas não bastava: a view tinha `DEFINER living@%`. A segunda MariaDB agora cria a conta aplicacional temporária antes de importar o dump; verificação da view e consulta da aplicação aprovadas.
6. O primeiro seletor de login do ensaio browser era dependente de rótulos; corrigido para os campos do formulário. O runner termina com erro em vez de deixar um browser órfão; o contentor de teste da tentativa falhada foi identificado pelos mounts do projeto e removido.

## CI e fronteira de aprovação

No commit `b5b2142`, confirmados Quick Django Tests, Quality Assurance e pt-PT integrity aprovados. Django Tests completo ainda estava em execução na recolha. Os resultados da base `141ae832` tinham as quatro suites aprovadas. Os estados posteriores devem ser consultados no [PR #1](https://github.com/alumbrisportugal/cohiva/pull/1) / [Actions](https://github.com/alumbrisportugal/cohiva/actions); aprovação de um SHA não é transferida para outro. A publicação desta consolidação desencadeia novo CI. Nenhuma release aprovada enquanto houver suites obrigatórias pendentes, falhadas ou canceladas.

## Limitações que impedem homologação comercial

- Cenário 1 cobre nova fração e contrato; reutilização de fração/novo ocupante, proprietários e delegação por imóvel, cotitulares na UI e condições completas ainda faltam.
- Cobrança/reconciliação e demonstrações EUR não homologadas. Staging usa `DummyBook`; não prova persistência financeira ou recebimentos reais. Não há integração fiscal AT/recibos legais implementada.
- Renovação, atualização anual, snapshot histórico da renda, cauções e inspeções/inventário pendentes.
- Manutenção ensaiada cobre abertura e comentários; atribuição, anexos, agenda, notificações e ciclo completo ainda incompletos.
- Isolamento ensaiado nos recursos indicados; não constitui auditoria total de todos os endpoints Cohiva. Downloads residentes continuam desativados.
- Parte da interface nativa, incluindo login, ainda tem texto alemão; design/navegação/PWA e acessibilidade completa não homologados.
- Restauro testado com dados fictícios e ficheiro sentinela; não simula um desastre completo de DSM nem documentos reais. Rollback cobre esta alteração de código sem novas migrações, não um downgrade de esquema incompatível.
- Imagem final imutável, utilizador não-root, readiness/healthchecks completos, backups agendados, teste de carga prolongado, certificado público e compatibilidade DSM 7.2.1 pendentes.

A matriz única [FUNCTIONAL_MATRIX.md](../../FUNCTIONAL_MATRIX.md) define o trabalho restante. Preservados serviços/volumes/certificados/credenciais preexistentes, MCP SSH/Synology, gateway e branches principais. Não houve promoção para produção.

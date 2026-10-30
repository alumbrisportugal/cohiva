# Matriz única de implementação e homologação

Referência auditada: `141ae832`, 30/10/2026. Alterações deste lote: percurso de novo arrendamento e infraestrutura de ensaio. Esta matriz substitui o uso do ROADMAP como prova de execução. **Nenhuma fase comercial homologada.**

Estado: **existente** = código nativo inspecionado; **adaptado** = código nesta branch; **validado** exige resultados identificados no relatório; **pendente** = falta implementação ou ensaio. Uma existência no modelo não prova o processo completo.

| Processo / cenário | Reutilização confirmada | Adaptação / lacuna | Aceitação / estado |
|---|---|---|---|
| Edifícios e frações / 1 | `geno.Building`, `RentalUnit`; admin nativo | Formulário pt-PT, renda mensal; não recria modelos | Adaptado; testes `test_living`; navegador pendente |
| Contactos / 1 | `Address`; ligação opcional a utilizador | Contacto novo ou existente; conta de residente não criada automaticamente | Adaptado; atribuição de conta e convite pendentes |
| Contratos / 1 | `Contract`, M2M titulares/frações, datas, estados | Novo percurso usa proposta/assinado, data e renda da fração | Adaptado; condições detalhadas, cotitulares no formulário e edição pendentes |
| Proprietários e permissões por imóvel | Staff e permissões de modelo existentes | Novo gestor é global, exige 4 permissões de leitura e, para criar, 4 de adição | Proprietários e delegação limitada por imóvel pendentes |
| Rendas recorrentes / 2 | `billing.create_invoices`, categorias, transações | Auditar configuração EUR, planos contabilísticos e repetição | Existente; integração portuguesa pendente |
| Pagamentos parciais / 2 | `pay_invoice` → `add_payment` → `add_invoice_obj`, entidade `Payment` | Não criar segundo ledger; validar reconciliação, concorrência e referências | Existente; homologação pendente |
| Renovação, atualização anual / 5 | Datas e relações contratuais | Snapshot de condições/renda histórica e aprovação de índice em falta | Pendente |
| Cessação e histórico / 5 | Datas, estados; APIs residentes filtradas | `is_active()` nativo continua inadequado para autorização; não usado no novo controlo de acesso | Adaptação parcial; testes de fronteira existentes, ciclo operacional pendente |
| Cauções | `RentalUnit.depot` | Valor não equivale a movimentos de receção/devolução | Pendente |
| Inspeções e inventário | Documentação genérica existente | Não existe processo completo inspecionado | Pendente |
| Despesas e demonstrativos | `finance` com backends GnuCash/CashCtrl | Configuração portuguesa e painel por imóvel pendentes | Existente/adaptável |
| Fiscalidade / 3 | Documentos e faturas internas | Fatura Cohiva não é recibo AT; revisão oficial portuguesa antes de implementar | Pendente; nenhuma emissão fiscal disponível |
| Manutenção / 4 | Modelos 0034/0035, API, admin, portal | Atribuição, anexos, agendamento, notificações, histórico de estado em falta | Adaptado parcialmente; cenário completo pendente |
| Documentos e privacidade / 6 | `resident_visible`, allowlist, querysets de titularidade | Descarregamento protegido ainda indisponível | Testes CI da base aprovados; navegador e revisão documental pendentes |
| Interface premium | Vue/Quasar/PWA, portal HTML Django | Gestão Django pt-PT reutiliza servidor e dados; unificação de navegação e design pendentes | Adaptado parcialmente; sem nova stack |
| Backup/restauro/rollback / 7 | MariaDB e ficheiros persistentes | Ensaiar dados, ficheiros, segredos/chaves e imagem anterior | Pendente |
| Instalação NAS / 8 | Dockerfile nativo Python 3.13, MariaDB e Redis | Compose de teste sem portas DB/Redis, TLS próprio, recursos limitados | Ensaio iniciado; não homologado |
| Baseline DSM 7.2.1 | Docker AMD64 | NAS disponível reporta DSM **7.4.1-90080 Update 1**, DS220+, J4025, 18 GB | Compatibilidade 7.2.1 não demonstrável neste hardware atual |

## Fronteiras do lote

- `/geno/living/`, `/geno/living/new/`, `/geno/living/contracts/<id>/` são páginas do Django existente, não uma aplicação paralela.
- Ativação explícita por `ALUMBRIS_CURRENCY = "EUR"` apenas em base dedicada. O modelo upstream não armazena moeda; não mudar este setting numa base histórica CHF.
- `RentalUnit.rent_netto` é a configuração atual da fração, não renda contratual histórica. A interface declara essa limitação; futura alteração de renda necessita desenho próprio antes de editar valores de contratos antigos.
- O percurso cria uma **nova** fração. Reutilizar uma fração existente com novo contrato, sobreposições, renovação e mudança de ocupante é trabalho seguinte.
- Não usa `Tenant` como titular: é uma associação comunitária ao edifício; `Contract.contractors` é a fonte de titularidade contratual.
- Sem novas migrações neste lote: são reutilizadas tabelas nativas, incluindo `auditlog`, configurado no upstream para todos os modelos e ator no middleware.
- A base passou as quatro suites obrigatórias no commit auditado. Consultar `reports/` para resultados deste lote; nunca transferir aprovação de um SHA para outro.

# NVIDEA

## Objetivo

Pasta dedicada à pesquisa, análise fundamentalista, acompanhamento estratégico e avaliação de investimento da NVIDIA Corporation (NASDAQ: NVDA).

## Documentos principais

- [MASTER_RESEARCH_SCRIPT.md](./MASTER_RESEARCH_SCRIPT.md) — protocolo mestre de pesquisa e respostas sobre negócio, tecnologia, concorrência, finanças, valuation, governança, regulação, mercado e riscos.
- [FASE_2_INTELIGENCIA_FINANCEIRA.md](./FASE_2_INTELIGENCIA_FINANCEIRA.md) — base financeira parcial, métricas reconciliadas, fórmulas, alertas, arquitetura de dados e critérios de QA.\n- [02_DADOS_FINANCEIROS/README.md](./02_DADOS_FINANCEIROS/README.md) — procedimento de extração XBRL da SEC, outputs, limitações e execução no GitHub Actions.\n- [scripts/extract_sec_companyfacts.py](./scripts/extract_sec_companyfacts.py) — coletor de fatos financeiros reportados via SEC Companyfacts.\n- [tests/test_extract_sec_companyfacts.py](./tests/test_extract_sec_companyfacts.py) — teste de regressão para normalização e reconciliação.

## Padrão de pesquisa

- Priorizar SEC/EDGAR, Investor Relations e documentos oficiais.
- Registrar data de corte, período fiscal, moeda, unidade e timestamp dos dados de mercado.
- Separar fatos reportados, declarações da administração, estimativas, cálculos, hipóteses e notícias não confirmadas.
- Citar fontes e reconciliar GAAP versus non-GAAP.
- Não inventar dados, não ocultar lacunas e não prometer retornos.
- Atualizar o snapshot após cada divulgação de resultados ou evento material.

## Estado do projeto — 17/11/2026

- FASE 1 — Pesquisa fundamental: script mestre V1.0 criado e leitura no GitHub confirmada.
- FASE 2 — Inteligência financeira: coletor SEC XBRL e workflow manual adicionados; primeira execução passou no teste automatizado, mas recebeu HTTP 403 da SEC. User-Agent corrigido para exigir e-mail de contato; reexecução depende da variável `SEC_CONTACT_EMAIL` no GitHub Actions.
- Q3 FY2027: resultados programados para 17/11/2026 às 13h20 PT; incorporar somente após publicação oficial.
- Governança: transição de CEO documentada em comunicado oficial e Form 8-K; manter investigação independente e fatos subsequentes em acompanhamento separado.
- Valuation: bloqueado como conclusão de investimento até a coleta SEC retornar HTTP 200, série histórica ser reconciliada e ações diluídas, caixa/dívida, guidance e dados de mercado serem sincronizados.

## Roadmap

1. FASE 1 — Pesquisa fundamental: concluída na versão inicial.
2. FASE 2 — Inteligência financeira: em andamento.
3. FASE 3 — Valuation institucional: depende da certificação da base financeira.
4. FASE 4 — Inteligência competitiva.
5. FASE 5 — Monitoramento de resultados, governança e catalisadores.
6. FASE 6 — Dashboard de investimentos.

## Governança

- Manter arquivos fora do escopo inalterados.
- Preservar histórico e versionamento.
- Toda atualização deve incluir fonte, data e justificativa.
- Revisar inconsistências antes de publicar conclusões.
- Distinguir dados parciais de dados certificados.

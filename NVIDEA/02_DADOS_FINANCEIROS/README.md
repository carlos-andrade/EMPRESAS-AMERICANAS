# SEC Companyfacts — extração e normalização

## Objetivo

Extrair fatos financeiros reportados pela NVIDIA a partir do endpoint XBRL Companyfacts da SEC, com rastreabilidade por conceito, período, unidade, formulário e accession number.

## Execução

O fluxo foi desenhado para rodar no GitHub Actions, sem servidor próprio:

1. Acesse **Actions** no repositório.
2. Selecione **NVIDEA — SEC financial data refresh**.
3. Clique em **Run workflow**.
4. O job consulta a SEC, gera os CSVs, valida proveniência e períodos e publica somente se houver dados válidos.

Também pode ser executado localmente:

```bash
python NVIDEA/scripts/extract_sec_companyfacts.py --output-dir NVIDEA/02_DADOS_FINANCEIROS
```

Para testes determinísticos com fixture:

```bash
python NVIDEA/scripts/extract_sec_companyfacts.py --input-json tests/fixtures/companyfacts_sample.json --output-dir /tmp/nvidea-financials
```

## Arquivos gerados

- `Source_Index.csv`: endpoint Companyfacts e filings 10-K/10-Q identificados.
- `Normalized_Financials_Long.csv`: fatos XBRL em formato longo; USD e ações convertidos para milhões, EPS preservado em USD/ação.
- `Normalization_Issues.csv`: conceitos esperados ausentes no payload.
- `QA_Flags.csv`: exceções materiais encontradas.
- `Validation_Checks.csv`: verificações executadas e seus resultados.

## Regras de integridade

- Não inventar valores ausentes.
- Não converter períodos YTD em trimestres por inferência.
- Não inferir data final fiscal pelo rótulo do trimestre.
- Não misturar GAAP com non-GAAP.
- Não tratar métricas de segmentos não disponíveis no US-GAAP como zero.
- Preservar accession, tag XBRL, início/fim do período e formulário.
- O resultado do extrator é staging auditável, não um modelo de valuation certificado.

## Limitações conhecidas

- O endpoint Companyfacts não substitui a leitura dos 10-K/10-Q e dos comunicados de resultados.
- A seleção inicial cobre conceitos US-GAAP explícitos; taxonomias proprietárias, receita por segmento, guidance, backlog, concentração de clientes e métricas operacionais exigem extração separada.
- O script preserva observações por accession e não escolhe silenciosamente entre valores conflitantes.
- Os testes de balanço são diagnósticos; períodos com dados provenientes de filings distintos exigem revisão antes da certificação.
- A execução é manual por enquanto. O workflow não roda automaticamente nem presume que os resultados trimestrais já foram divulgados.

## Fonte

SEC Companyfacts — CIK 1045810: https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json
NVIDIA filings: https://www.sec.gov/edgar/browse/?CIK=1045810&owner=exclude

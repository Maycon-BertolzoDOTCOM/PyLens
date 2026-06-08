# PyScope

PyScope é um observatório arquitetural para código Python. Ele foca em observação estática do grafo de imports, métricas de arquitetura, artefatos auditáveis e visualizações claras.

## O que é PyScope

- uma ferramenta de observação, não de governança
- voltada para análise do estado atual do código
- produz resultados reproduzíveis e artefatos JSON
- integra visualização Graphviz para inspeção do grafo

## Pipeline: observe → visualize → store

PyScope includes a minimal pipeline runner that reads a C1 JSON artifact, generates Graphviz artifacts, and stores results.

Basic usage (local storage):

```bash
# install editable package
pip install -e .

# run pipeline using local storage
pyscope run-pipeline \
	--input-json tests/fixtures/c1_example.json \
	--output-dir out \
	--storage-dir storage
```

Using S3 as storage backend (requires `boto3` and AWS credentials):

```bash
pip install boto3

pyscope run-pipeline \
	--input-json tests/fixtures/c1_example.json \
	--output-dir out \
	--storage-dir storage \
	--storage-backend s3 \
	--s3-bucket my-bucket \
	--s3-prefix pyscope
```

Artifacts produced:

- `graph.dot` — Graphviz DOT source
- `graph.svg` / `graph.png` — rendered images (when Graphviz is available)
- `index.html` — simple HTML report referencing the images

The CI workflow `./github/workflows/c1_pipeline.yml` runs the pipeline on `main` and uploads `out/` artifacts.

## Visualizador

O módulo `pyscope.visualizer` converte um resultado C1 em um grafo Graphviz e gera um relatório HTML.

### Exemplo de uso

```bash
python -m pyscope.visualizer --input-json tests/fixtures/c1_example.json --output-dir out/visual
```

### Saída esperada

- `out/graph.dot`
- `out/graph.svg` (se Graphviz estiver instalado)
- `out/graph.png` (se Graphviz estiver instalado)
- `out/index.html`

## CI

A workflow `.github/workflows/visualizer-ci.yml` roda o visualizador em branches `scope/**` e publica artefatos.

## Estrutura do visualizador

- `pyscope/visualizer/schema.py`
- `pyscope/visualizer/graphviz_builder.py`
- `pyscope/visualizer/renderer.py`
- `pyscope/visualizer/html_report.py`
- `pyscope/visualizer/cli.py`

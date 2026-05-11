# Research Paper Chunking Pipeline

This repository contains a research-paper chunking pipeline for structured OCR JSON files. It is designed for RAG preprocessing where each chunk should keep enough context, metadata, and source relationships to be useful during retrieval and answer generation.

**Status:** this repository is under active update.

## What the pipeline does

The pipeline converts structured paper JSON files into relationship-aware chunks. It keeps the paper hierarchy, section path, page span, source block IDs, neighboring chunk links, and special metadata for equations, tables, and figures.

It runs in three stages:

1. **Prepare papers:** normalize section and block metadata, remove noisy blocks, and drop irrelevant sections such as references, acknowledgements, and checklist text.
2. **Create chunks:** convert cleaned text, equations, tables, and figures into embeddable chunks with metadata and relations.
3. **Evaluate chunks:** check whether chunks have usable text, section paths, source block metadata, relationship metadata, equation context, table captions, and figure captions.


## Input format

Each input file should be a JSON object with paper-level metadata and a list of sections:


## Installation

Use Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`chonkie` is used for recursive text splitting when available. If the import fails at runtime, the code falls back to a deterministic local paragraph/character splitter.

## How to run

First, create local working folders , create three folders for each normalized files, chunk folder, log folder (you can create before running scripts cmd or give in the output directory, folder will be made automatically.):


### 1. Prepare papers

```bash
python 01_prepare_papers.py \
  --input data/raw \
  --output data/normalized \
  --log-dir logs
```

This step:

- infers section IDs, section numbers, section depth, and section paths
- marks section roles such as content, title/authors, references, acknowledgements, and checklist sections
- removes references, acknowledgements, checklist sections, empty blocks, and obvious noise
- assigns stable block IDs to every retained source block
- writes cleaned paper JSON files to `data/normalized/`
- writes `_prepare_report.json` with section/block drop statistics

### 2. Create chunks

```bash
python 02_chunk_papers.py \
  --input data/normalized \
  --output data/chunks \
  --log-dir logs \
  --chunk-size 640 \
  --overlap 64 \
  --table-chunk-size 768 \
  --min-prose-tokens 80 \
  --max-context-blocks 2
```

This step creates four chunk types: `prose`, `equation`, `table`, and `figure`.

#### Prose chunks

Text blocks are accumulated inside the same section and split with the recursive splitter. The default `chunk-size` is 640 estimated tokens and the default overlap is 64 estimated tokens. Short prose chunks below `min-prose-tokens` are merged with nearby prose chunks from the same section when possible. If they cannot be merged, they are kept with a quality flag.

#### Equation chunks

Each equation becomes its own chunk. The raw LaTeX is preserved in `metadata.equation_latex` and is also included in the chunk text. The chunk also includes:

- section path
- previous nearby text blocks
- following nearby text blocks
- equation image path, when available
- context cue flags such as whether the previous text introduces the equation or the following text explains it

This avoids storing equations as raw LaTeX only, which is usually weak for retrieval.

#### Table chunks

Tables are converted from HTML into row-wise plain text. The raw table HTML is preserved in `metadata.table_html`. The chunk includes:

- section path
- explicit caption when available
- recovered caption from nearby `Table X` reference text when no explicit caption exists
- inferred section-based caption as a fallback
- nearby table reference text
- row range metadata

Long tables are split by rows using `table-chunk-size`. The header row and caption are repeated in every table part so each table chunk can be retrieved independently.

#### Figure chunks

Consecutive image blocks in the same section are grouped into one figure chunk. The chunk includes:

- section path
- explicit figure caption when available
- recovered caption from nearby `Figure X` or `Fig. X` reference text when needed
- LLM-generated image summaries from `caption_llm`, when available
- image paths
- figure group size

This makes visual content searchable even when the actual image is not embedded directly.

### 3. Evaluate chunks

```bash
python 03_evaluate_chunks.py \
  --input data/chunks \
  --output data/evaluation \
  --log-dir logs \
  --chunk-size 640 \
  --table-chunk-size 768 \
  --min-prose-tokens 80
```

This step writes `data/evaluation/_evaluation_report.json` and checks:

- empty chunks
- missing section paths
- missing source block metadata
- missing relationship metadata
- reference/checklist leakage
- duplicate chunks
- short or oversized prose chunks
- equations without LaTeX or text context
- tables without reliable captions or oversized table chunks
- figures without captions or LLM summaries
- missing previous/next chunk links

## Main hyperparameters

| Parameter | Default | Used in | Meaning |
|---|---:|---|---|
| `--chunk-size` | `640` | chunking, evaluation | Target size for prose chunks in estimated tokens. |
| `--overlap` | `64` | chunking | Context overlap between prose chunks. |
| `--table-chunk-size` | `768` | chunking, evaluation | Target size for table chunks before row-wise splitting. |
| `--min-prose-tokens` | `80` | chunking, evaluation | Minimum preferred prose size. Short chunks are merged or flagged. |
| `--max-context-blocks` | `2` | chunking | Number of nearby text blocks to attach before and after equations. |
| `--no-table-splitting` | disabled | chunking | If set, long tables are kept as one chunk. |
| `--verbose` | disabled | all scripts | Enables more detailed logging. |

Token counts are approximate. The code uses a simple estimate of one token per four characters.

## Output chunk schema

Each output file in your chunk folder is a JSON list. Each chunk follows this structure:

```json
{
  "chunk_id": "paper_key_00001_prose",
  "type": "prose",
  "text": "embeddable chunk text",
  "metadata": {
    "paper_key": "...",
    "source_pdf": "...",
    "paper_title": "...",
    "chunk_type": "prose",
    "section_id": "...",
    "section_index": 2,
    "section_title": "3 Methodology",
    "section_number": "3",
    "section_depth": 1,
    "section_path": ["3 Methodology", "3.1 Model"],
    "section_path_ids": ["..."],
    "page_span": {"start": 3, "end": 4},
    "source_block_ids": ["..."],
    "source_block_indices": [0, 1],
    "source_block_types": ["text"],
    "relations": {
      "parent_section_id": "...",
      "ancestor_section_ids": ["..."],
      "previous_chunk_id": null,
      "next_chunk_id": "...",
      "previous_same_section_chunk_id": null,
      "next_same_section_chunk_id": "...",
      "previous_source_block_id": null,
      "next_source_block_id": null,
      "related_text_block_ids": [],
      "related_equation_block_ids": [],
      "related_table_block_ids": [],
      "related_figure_block_ids": []
    },
    "quality_flags": [],
    "estimated_tokens": 390
  }
}
```

Additional metadata is added depending on the chunk type:

- `equation`: `equation_latex`, `equation_text_format`, `equation_img_path`, `equation_context`
- `table`: `table_caption`, `table_caption_source`, `table_html`, `table_part_index`, `table_part_count`, `table_row_start`, `table_row_end`, `table_reference_text_block_ids`
- `figure`: `figure_caption`, `figure_caption_source`, `figure_group_size`, `image_paths`, `llm_caption_count`, `figure_reference_text_block_ids`
- `prose`: `prose_part_index`, `prose_part_count`, `splitter_backend`

## Advatanges of using this pipeline for RAG

The output is not just plain text chunks. Each chunk keeps enough source information to support grounded retrieval:

- section paths help the retriever understand where the chunk belongs in the paper
- source block IDs allow tracing a chunk back to the original OCR block
- previous/next chunk IDs preserve document flow
- same-section links preserve local context
- equations keep LaTeX plus nearby explanation text
- tables keep captions, headers, rows, and raw HTML
- figures keep captions, nearby references, and image summaries
- quality flags make it easier to inspect weak chunks before embedding


"""Ingest data/sample_docs and write the chunks to data/processed/chunks.jsonl."""

import json

from enterprise_rag.config import get_settings, project_root
from enterprise_rag.ingestion.registry import Registry
from enterprise_rag.ingestion.service import ingest_file


def main() -> None:
    root = project_root()
    settings = get_settings()
    out_dir = root / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    registry = Registry(out_dir / "registry.json")
    rows = []
    for path in sorted((root / "data" / "sample_docs").glob("*")):
        if not path.is_file():
            continue
        result = ingest_file(path, settings, registry)
        rows.extend(chunk.to_dict() for chunk in result.chunks)
        print(f"{path.name}: {len(result.chunks)} chunks, new={result.is_new}")
    lines = (json.dumps(row, ensure_ascii=False) for row in rows)
    (out_dir / "chunks.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} chunks to {out_dir / 'chunks.jsonl'}")


if __name__ == "__main__":
    main()
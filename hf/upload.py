# -*- coding: utf-8 -*-
"""Публикует датасет переписывания карточек на Hugging Face.

    export HF_TOKEN=hf_...     # Windows: set HF_TOKEN=hf_...
    python hf/upload.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HF = REPO / "hf"
DATASET_NAME = "product-card-rewrites"
DATA = HF / "data" / "rewrites.jsonl"
CARD = HF / "dataset" / "README.md"


def main() -> int:
    try:
        from huggingface_hub import HfApi, create_repo, upload_file
    except ImportError:
        print("Нужен huggingface_hub: pip install huggingface_hub")
        return 2

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        print("Задайте HF_TOKEN (write-токен Hugging Face).")
        return 2
    api = HfApi(token=token)
    namespace = api.whoami()["name"]

    if not DATA.exists():
        print("Сначала соберите датасет: python hf/build_dataset.py")
        return 2

    repo_id = "%s/%s" % (namespace, DATASET_NAME)
    create_repo(repo_id, repo_type="dataset", exist_ok=True, token=token)
    upload_file(str(DATA), path_in_repo="rewrites.jsonl", repo_id=repo_id,
                repo_type="dataset", token=token)
    upload_file(str(CARD), path_in_repo="README.md", repo_id=repo_id,
                repo_type="dataset", token=token)
    print("готово: https://huggingface.co/datasets/%s" % repo_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())

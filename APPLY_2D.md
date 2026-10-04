# NusantaraEdu Games 2D — Direct Overlay

Direkomendasikan memakai script dari **NusantaraEdu-Traditional-Games-2D-kit.zip** karena script otomatis membackup UI lama dan mengompilasi konten NER.

Perintah utama:

```bash
python tools/apply_2d_overlay.py \
  --project-root /DISK/nurchim/NusantaraEdu-NER \
  --remote-base-url https://nusantara-edu-ner.vercel.app
```

Setelah itu:

```bash
cd /DISK/nurchim/NusantaraEdu-NER
pytest -q
python -m uvicorn api.index:app --reload
```

Target test: `9 passed`.

# NusantaraEdu Traditional Games

Aplikasi game edukasi permainan tradisional Indonesia yang dibangun di atas **model produksi NusantaraEdu-NER**.

## Fitur

- `/` dan `/game` — game hub untuk publik.
- `/ner` — interface analisis NER sebelumnya.
- **Tebak Kategori** — klasifikasi entitas budaya hasil model.
- **Lengkapi Cerita** — mengisi entitas yang disembunyikan dari teks budaya.
- **Tebak Permainan** — mengenali permainan dari deskripsi cara bermain.
- **Tantangan Campuran** — gabungan beberapa tipe soal.
- **Teks Sendiri** — pengguna memasukkan teks dan model membuat pertanyaan otomatis.
- Skor dan streak disimpan di `localStorage`, tidak membutuhkan akun/database.

## Jalankan lokal

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pytest -q
python -m uvicorn api.index:app --reload
```

Buka `http://127.0.0.1:8000`.

## Endpoint

- `GET /api/health`
- `GET /api/model-info`
- `POST /api/predict`
- `POST /api/quiz`
- `GET /api/game/catalog`
- `GET /api/game/catalog/{game_id}`
- `POST /api/game/session`
- `POST /api/game/custom`
- `GET /api/docs`

## Deployment

Repository ini disiapkan untuk GitHub + Vercel. Model produksi berada di `models/production/model-best` dan konten game yang sudah dikompilasi berada di `game/compiled_game_content.json`.

Metrik model pada UI dibaca dari `models/production/manifest.json`; jangan hard-code skor model ke frontend.

"""Skema akumulator state turn PIC 7 Level 2 (Milestone 7.6+).

`KeadaanTurn` tumbuh field-demi-field tiap milestone Sambungan (M7.8-7.16
menambah field sendiri sesuai kebutuhan cabangnya) - BUKAN tuple yang terus
membesar/bersarang across 11 langkah berurutan. Field M7.6 (`payload`,
`ketergantungan`) non-Optional: baik `ValidationError` (Input Layer) maupun
`APIError` (Pemetaan Ketergantungan Turn) adalah exception keras yang
menjalar keluar `proses_turn()`, bukan nilai terdegradasi yang disimpan di
sini. Lihat
milestones/7.6-sambungan-input-layer-pemetaan-ketergantungan/decisions.md
Keputusan 2.

Field M7.7 (`rewrite`, `session_memory`): `rewrite` selalu terisi
(`rewrite_to_standalone()` py fallback penuh, tidak pernah raise).
`session_memory` membedakan `None` (Tarik Memory tidak pernah dipanggil -
tidak ada referensi terdeteksi) dari `[]` (dipanggil, genuinely tidak
menemukan data) - forced KK M7.7 eksplisit. Lihat
milestones/7.7-sambungan-percabangan-paralel-rewrite-tarik-memory/
decisions.md Keputusan 3.

Field M7.8 (`decomposition`): selalu terisi, mirror `rewrite` -
`decompose_question()` (ketiga sub-langkahnya: klasifikasi_kebutuhan,
pecah_atomik, verifikasi_pemecahan) py fallback APIError penuh di tiap
tahap, tidak pernah raise ke pemanggilnya. Dipanggil dengan
`rewrite.rewritten_question` (hasil Rewrite), BUKAN `payload.question`
asli - forced KK M7.8 eksplisit ("bukan makna kalimat asli sebelum
di-rewrite"). Lihat
milestones/7.8-sambungan-rewrite-decomposition/decisions.md Keputusan 2+4.

Field M7.9 (`matches`): selalu terisi KALAU `proses_turn()` selesai tanpa
exception - BEDA dari `rewrite`/`decomposition`, `match_and_archive()`
SENDIRI bisa raise (arsip ulang lewat `store_session_memory()` genuinely
raise pada kegagalan DB, tidak full-fallback). Dipanggil dengan
`session_memory or []` (konversi wajib - `match_and_archive()` menerima
`list`, bukan `Optional`). Lihat
milestones/7.9-sambungan-pencocokan/decisions.md Keputusan 1+3.

Field M7.10 (`domain_gate`): selalu terisi, mirror `rewrite`/`decomposition`
- `identifikasi_domain_semua()` (M2.1) tidak pernah raise (sub-langkahnya
py fallback APIError penuh). Panjang list BISA lebih kecil dari `matches`
- filter ke `status=PERLU_EKSEKUSI` adalah tanggung jawab INTERNAL
`identifikasi_domain_semua()` sendiri (sudah ada sejak M2.1), `matches`
diteruskan APA ADANYA tanpa filter oleh orkestrator. Lihat
milestones/7.10-sambungan-domain-gate/decisions.md Keputusan 1+3.

Field M7.11 (`otorisasi`, `cakupan_individu`, `retriever` - ditambah
bertahap per checkpoint): M7.11 menutup DUA gap wiring di luar Lingkup
tertulis aslinya (M2.2 Pemeriksaan Otorisasi dan M2.3 Deteksi Cakupan
Individu, keduanya belum pernah tersambung sejak milestone asalnya)
SEBELUM menyambungkan Retriever sesungguhnya - lihat
milestones/7.11-sambungan-retriever/decisions.md Keputusan 1-2. Ketiga
field selalu terisi, mirror `domain_gate`: `periksa_otorisasi_semua()`
(M2.2) dan `deteksi_constraint_semua()` (M2.3) murni deterministik tanpa
panggilan LLM (lookup role_permissions/pre-filter role-domain), tidak
pernah raise; `proses_retrieval_atomic_intent()` per item (M3.1-3.3) juga
tidak pernah gagal teknis di level kebutuhan-atomik. Rantai pemanggilan
sekuensial `identifikasi_domain_semua()` -> `periksa_otorisasi_semua()`
-> `deteksi_constraint_semua()` -> `proses_retrieval_semua()` (baru,
`src/layers/retriever/kecukupan_struktural.py`), tiap fungsi menerima
persis output fungsi sebelumnya. Lihat
milestones/7.11-sambungan-retriever/decisions.md Keputusan 4+6.
"""

from pydantic import BaseModel

from src.schemas.authorization import AtomicIntentAuthorization
from src.schemas.cakupan_individu import AtomicIntentConstraint
from src.schemas.decomposition import DecompositionResult
from src.schemas.domain_gate import AtomicIntentDomains
from src.schemas.matching import AtomicIntentMatch
from src.schemas.retriever import HasilKecukupanStruktural
from src.schemas.rewrite import RewriteResult
from src.schemas.session_memory import SessionMemoryPackage
from src.schemas.turn_dependency import TurnDependencyResult
from src.schemas.turn_payload import TurnPayload


class KeadaanTurn(BaseModel):
    payload: TurnPayload
    ketergantungan: TurnDependencyResult
    rewrite: RewriteResult
    session_memory: list[SessionMemoryPackage] | None
    decomposition: DecompositionResult
    matches: list[AtomicIntentMatch]
    domain_gate: list[AtomicIntentDomains]
    otorisasi: list[AtomicIntentAuthorization]
    cakupan_individu: list[AtomicIntentConstraint]
    retriever: list[HasilKecukupanStruktural]

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

Field M7.12 (`query_engine`): `susun_dan_verifikasi_request_semua()`
(baru, `src/layers/query_engine/query_engine.py`) - layer Query Engine
(M3.4-3.5) sudah tersambung internal penuh sejak M7.4, TAPI belum py
fungsi batch level-list gabungan Langkah 1+2. Bentuk `list[tuple[...]]`
dipertahankan apa adanya dari kontrak M7.4 (tanpa skema baru). Panjang
BISA lebih pendek dari `retriever` - item `view_name_final=None` di-skip
(forced by signature `view_name: str` non-Optional, bukan pilihan gaya).
Lihat milestones/7.12-sambungan-query-engine/decisions.md Keputusan 1+4+7.

Field M7.13 (`verification_gate`): `verifikasi_gate_semua()` (baru,
`src/layers/verification_gate/verifikasi_gate.py`) - layer Verification
Gate (M2.4) sudah matang penuh (real DB fixture) tapi belum py fungsi
batch. Fan-in TIGA sumber (`query_engine`, `retriever`, `cakupan_
individu`) dicocokkan via `atomic_intent_id`. `HasilVerifikasiGate`
sendiri TIDAK membawa field `atomic_intent` - bentuk
`list[tuple[AtomicIntent, HasilVerifikasiGate]]` mengembalikan asosiasi
itu (tanpa skema baru, konsisten preferensi M7.12). Panjang BISA lebih
pendek dari `query_engine` - item `hasil_verifikasi=None` ATAU
`lolos=False` (M3.5) di-skip (Keputusan 2+4, beda dari M7.11: `lolos=
False` bukan forced by signature, murni keputusan desain mencegah
request tidak cukup lolos diam-diam ke Execution). Lihat
milestones/7.13-sambungan-verification-gate/decisions.md.
"""

from pydantic import BaseModel

from src.schemas.authorization import AtomicIntentAuthorization
from src.schemas.cakupan_individu import AtomicIntentConstraint
from src.schemas.decomposition import AtomicIntent, DecompositionResult
from src.schemas.domain_gate import AtomicIntentDomains
from src.schemas.matching import AtomicIntentMatch
from src.schemas.query_engine import HasilPenyusunanRequest, HasilVerifikasiBentukRequest
from src.schemas.retriever import HasilKecukupanStruktural
from src.schemas.rewrite import RewriteResult
from src.schemas.session_memory import SessionMemoryPackage
from src.schemas.turn_dependency import TurnDependencyResult
from src.schemas.turn_payload import TurnPayload
from src.schemas.verification_gate import HasilVerifikasiGate


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
    query_engine: list[tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]]
    verification_gate: list[tuple[AtomicIntent, HasilVerifikasiGate]]

"""Orkestrator Turn PIC 7 Level 2: Input Layer (M1.2) -> Pemetaan
Ketergantungan Turn (M1.3) -> Percabangan Paralel (Rewrite M1.4 + Tarik
Session Memory M1.5) -> Decomposition (M1.6).

Fungsi ini membuka span `invoke_agent` PERTAMA KALI di `src/` produksi
(Milestone 7.6) - pembungkus "operasi orkestrasi keseluruhan" per turn
sesuai kontrak Bagian 2 rancangan-observability-ai-chatbot.md. Tumbuh
bertahap tiap milestone Sambungan berikutnya (M7.9-7.16) hingga mencakup
seluruh sembilan layer. `src/main.py` SENGAJA belum memanggil fungsi ini -
penyambungan endpoint ditunda ke Milestone 7.17.

Short-circuit murni alami: `validate_turn_payload()` melempar
`pydantic.ValidationError` yang menjalar keluar tanpa langkah berikutnya
pernah terpanggil - tidak ada `try`/`if` eksplisit yang menyembunyikan
kegagalan. `openai.APIError` dari `detect_turn_dependency()` juga
dibiarkan menjalar apa adanya (celah M1.3, sudah diperbaiki - lihat
docs/keterbatasan-diterima.md #14).

Milestone 7.7: Rewrite (selalu jalan) dan Tarik Session Memory (HANYA
jalan kalau ada referensi terdeteksi) dijalankan BENAR-BENAR paralel
lewat `ThreadPoolExecutor` - context span OTel dipropagasi manual ke
thread worker (`opentelemetry.context.attach()`/`detach()`), diverifikasi
nyata terhadap Jaeger live sebelum dikunci sebagai pendekatan. Kegagalan
ganda (kedua cabang gagal bersamaan) TIDAK ditangani secara khusus -
`.result()` dipanggil berurutan, exception pertama yang menjalar. Lihat
milestones/7.7-sambungan-percabangan-paralel-rewrite-tarik-memory/
decisions.md.

Milestone 7.8: setelah blok `ThreadPoolExecutor` selesai (`rewrite_result`
final), `decompose_question()` dipanggil SEKUENSIAL di thread utama
dengan `rewrite_result.rewritten_question` (bukan `payload.question`
asli) - Decomposition murni bergantung data pada hasil Rewrite, bukan
Tarik Memory, sehingga tidak butuh paralelisme baru maupun propagasi
context manual (span `chat` dari ketiga sub-langkah Decomposition
otomatis jadi anak `invoke_agent` karena tetap di thread yang sama). Lihat
milestones/7.8-sambungan-rewrite-decomposition/decisions.md.

Milestone 7.9: `match_and_archive()` dipanggil SEKUENSIAL setelah
`decomposition_result` final - titik pertemuan pertama, Pencocokan
genuinely butuh KEDUA jalur (Decomposition M7.8 + Tarik Memory M7.7)
sebagai argumen. `session_memory_result or []` mengonversi `None`->`[]`
(forced signature `match_and_archive()`, bukan `Optional`). BEDA dari
`rewrite`/`decomposition`: panggilan ini SENDIRI bisa raise (arsip ulang
lewat `store_session_memory()` genuinely raise pada kegagalan DB) -
TIDAK dibungkus try/except baru, mirror preseden kegagalan cabang M7.7.
Lihat milestones/7.9-sambungan-pencocokan/decisions.md.

Milestone 7.10: `identifikasi_domain_semua(matches)` dipanggil SEKUENSIAL
setelah `matches` final, `matches` diteruskan APA ADANYA (filter ke
status=PERLU_EKSEKUSI adalah tanggung jawab INTERNAL fungsi itu sendiri,
sudah ada sejak M2.1 - orkestrator TIDAK ikut memfilter, mencegah
duplikasi logic). Lihat milestones/7.10-sambungan-domain-gate/decisions.md.

Milestone 7.11 (Checkpoint 2): `periksa_otorisasi_semua(domain_gate_result,
payload.role_title)` dipanggil SEKUENSIAL setelah `domain_gate_result`
final - menutup gap wiring M2.2 (Pemeriksaan Otorisasi) yang belum pernah
tersambung sejak milestone asalnya, di luar Lingkup tertulis asli M7.11
tapi dibutuhkan KK-nya sendiri. Lihat
milestones/7.11-sambungan-retriever/decisions.md Keputusan 1+4-5.

Milestone 7.11 (Checkpoint 4): `deteksi_constraint_semua(otorisasi_result,
payload.role_title)` dipanggil SEKUENSIAL setelah `otorisasi_result`
final - menutup gap wiring M2.3 (Deteksi Cakupan Individu), juga belum
pernah tersambung sejak milestone asalnya. Disambungkan sekarang (bukan
ditunda ke M7.13) atas keputusan sadar user, mencegah M7.13 nanti
menemukan gap serupa. Lihat
milestones/7.11-sambungan-retriever/decisions.md Keputusan 2+4.

Milestone 7.11 (Checkpoint 7): `proses_retrieval_semua(cakupan_individu_
result)` dipanggil SEKUENSIAL setelah `cakupan_individu_result` final -
Sambungan 6 resmi (Domain Gate -> Retriever): daftar domain yang lolos
otorisasi (hasil rantai M2.1->M2.2->M2.3) jadi input pembatas pencarian
Retriever (M3.1-3.3). Lihat
milestones/7.11-sambungan-retriever/decisions.md Keputusan 3-4.

Milestone 7.12 (Sambungan 7 resmi): `susun_dan_verifikasi_request_semua(
retriever_result)` dipanggil SEKUENSIAL setelah `retriever_result` final -
view yang divalidasi Retriever jadi input Query Engine (M3.4-3.5, sudah
tersambung internal sejak M7.4). Item dengan `view_name_final=None`
di-skip secara INTERNAL oleh fungsi ini sendiri (bukan tanggung jawab
orkestrator). Lihat
milestones/7.12-sambungan-query-engine/decisions.md.

Milestone 7.13 (Sambungan 8 resmi): `verifikasi_gate_semua(query_engine_
result, retriever_result, cakupan_individu_result, payload.employee_id)`
dipanggil SEKUENSIAL setelah `query_engine_result` final - request final
Query Engine JADI input Verification Gate (M2.4, sudah matang penuh sejak
awal proyek), termasuk constraint cakupan-individu (M7.11) dicek konsisten
di titik ini. Fan-in TIGA sumber (`query_engine_result`, `retriever_
result`, `cakupan_individu_result`), dicocokkan via `atomic_intent_id`
SECARA INTERNAL oleh fungsi ini sendiri. Lihat
milestones/7.13-sambungan-verification-gate/decisions.md.

Milestone 7.14 (Sambungan 9 resmi, termasuk uji wave berulang): SETELAH
`query_engine_result` final, `kelompokkan_wave(query_engine_result)`
(`src/orchestration/wave.py`, baru) mempartisi atomic intent jadi
gelombang eksekusi berurutan berdasar `relasi`/`bergantung_pada` - MURNI
soal urutan, TANPA data hasil wave 1 di-inject ke wave 2 (`susun_request_
atomic_intent()` M3.4 TIDAK disentuh, dikonfirmasi user). Panggilan
`verifikasi_gate_semua()` (M7.13) yang SEBELUMNYA sekali borongan untuk
seluruh atomic intent, SEKARANG dipanggil PER WAVE di dalam loop - ini
PERTAMA KALINYA Sambungan Level 2 menata ulang CARA memanggil fungsi
milestone sebelumnya (bukan murni menambah langkah baru di akhir).
Tiap iterasi wave dibungkus span `orchestration.wave` (`wave.index`,
`wave.intent_count`) - pembuktian utama KK M7.14 (wave 2 baru terlihat
di Jaeger setelah wave 1 selesai) lewat urutan span nyata. Hasil
`verifikasi_gate_semua()`+`eksekusi_atomic_intent_semua()` (baru,
`src/layers/execution/klasifikasi_respons.py`) tiap wave di-`extend()`
ke akumulator lintas-wave - `KeadaanTurn.verification_gate`/`execution`
tetap FLAT, bentuk/kontrak tidak berubah dari M7.13. Lihat
milestones/7.14-sambungan-execution/decisions.md.
"""

from concurrent.futures import ThreadPoolExecutor

from opentelemetry import context as otel_context

from src.layers.context_resolution.matching import match_and_archive
from src.layers.context_resolution.rewrite import rewrite_to_standalone
from src.layers.context_resolution.session_memory import retrieve_session_memory
from src.layers.context_resolution.turn_dependency import detect_turn_dependency
from src.layers.decomposition.decompose import decompose_question
from src.layers.domain_gate.cakupan_individu import deteksi_constraint_semua
from src.layers.domain_gate.domain_gate import identifikasi_domain_semua
from src.layers.domain_gate.otorisasi import periksa_otorisasi_semua
from src.layers.execution.klasifikasi_respons import eksekusi_atomic_intent_semua
from src.layers.input_layer import validate_turn_payload
from src.layers.query_engine.query_engine import susun_dan_verifikasi_request_semua
from src.layers.retriever.kecukupan_struktural import proses_retrieval_semua
from src.layers.verification_gate.verifikasi_gate import verifikasi_gate_semua
from src.observability.tracing import get_tracer
from src.orchestration.wave import kelompokkan_wave
from src.schemas.orchestration import KeadaanTurn
from src.schemas.rewrite import RewriteResult
from src.schemas.session_memory import SessionMemoryPackage
from src.schemas.turn_payload import TurnPayload

_TRACER_NAME = "orchestration"


def _jalankan_rewrite(ctx: otel_context.Context, payload: TurnPayload) -> RewriteResult:
    token = otel_context.attach(ctx)
    try:
        return rewrite_to_standalone(payload)
    finally:
        otel_context.detach(token)


def _jalankan_tarik_memory(
    ctx: otel_context.Context, session_id: str, turn_index: int
) -> list[SessionMemoryPackage]:
    token = otel_context.attach(ctx)
    try:
        return retrieve_session_memory(session_id, turn_index)
    finally:
        otel_context.detach(token)


def proses_turn(raw: dict) -> KeadaanTurn:
    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("invoke_agent") as span:
        if "session_id" in raw:
            span.set_attribute("session.id", str(raw["session_id"]))
        if "turn_index" in raw:
            try:
                span.set_attribute("turn.index", int(raw["turn_index"]))
            except (TypeError, ValueError):
                pass

        payload = validate_turn_payload(raw)
        ketergantungan = detect_turn_dependency(payload)

        harus_tarik_memory = (
            ketergantungan.is_dependent and ketergantungan.referenced_turn_index is not None
        )

        ctx = otel_context.get_current()
        with ThreadPoolExecutor(max_workers=2) as executor:
            rewrite_future = executor.submit(_jalankan_rewrite, ctx, payload)
            memory_future = (
                executor.submit(
                    _jalankan_tarik_memory,
                    ctx,
                    payload.session_id,
                    ketergantungan.referenced_turn_index,
                )
                if harus_tarik_memory
                else None
            )

            rewrite_result = rewrite_future.result()
            session_memory_result = memory_future.result() if memory_future else None

        decomposition_result = decompose_question(rewrite_result.rewritten_question)

        matches = match_and_archive(
            decomposition_result.atomic_intents,
            session_memory_result or [],
            payload.session_id,
            payload.turn_index,
        )

        domain_gate_result = identifikasi_domain_semua(matches)

        otorisasi_result = periksa_otorisasi_semua(domain_gate_result, payload.role_title)

        cakupan_individu_result = deteksi_constraint_semua(otorisasi_result, payload.role_title)

        retriever_result = proses_retrieval_semua(cakupan_individu_result)

        query_engine_result = susun_dan_verifikasi_request_semua(retriever_result)

        waves = kelompokkan_wave(query_engine_result)
        verification_gate_result: list = []
        execution_result: list = []
        for wave_index, wave in enumerate(waves, start=1):
            with tracer.start_as_current_span("orchestration.wave") as wave_span:
                wave_span.set_attribute("wave.index", wave_index)
                wave_span.set_attribute("wave.intent_count", len(wave))

                hasil_vg_wave = verifikasi_gate_semua(
                    wave, retriever_result, cakupan_individu_result, payload.employee_id
                )
                verification_gate_result.extend(hasil_vg_wave)

                hasil_eksekusi_wave = eksekusi_atomic_intent_semua(
                    hasil_vg_wave, cakupan_individu_result, payload.role_title, payload.employee_id
                )
                execution_result.extend(hasil_eksekusi_wave)

        return KeadaanTurn(
            payload=payload,
            ketergantungan=ketergantungan,
            rewrite=rewrite_result,
            session_memory=session_memory_result,
            decomposition=decomposition_result,
            matches=matches,
            domain_gate=domain_gate_result,
            otorisasi=otorisasi_result,
            cakupan_individu=cakupan_individu_result,
            retriever=retriever_result,
            query_engine=query_engine_result,
            verification_gate=verification_gate_result,
            execution=execution_result,
        )

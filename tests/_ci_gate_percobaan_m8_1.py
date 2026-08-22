"""File sementara Checkpoint 18 Milestone 8.1 - percobaan sengaja membuktikan
gate CI menolak pelanggaran lint dan pola menyerupai credential. Dihapus
setelah bukti didapat, TIDAK PERNAH masuk main."""

import os  # sengaja tidak dipakai - harus terdeteksi ruff F401

AWS_EXAMPLE_KEY = "AKIATESTFAKEDUMMY227"  # pola dummy cocok regex aws-access-token, BUKAN kredensial asli

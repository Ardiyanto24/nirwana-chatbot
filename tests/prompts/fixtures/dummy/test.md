---
id: dummy.test
version: 3
milestone: "0.0"
model_compat: ["dummy-model"]
description: "Fixture uji loader, bukan prompt produksi"
---
Ini prompt dummy untuk {{ subjek }}.
{% if feedback %}
Catatan revisi: {{ feedback }}
{% endif %}
Daftar item:
{% for item in daftar %}
- {{ item }}
{% endfor %}

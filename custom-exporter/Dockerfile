# Multi-stage build - Milestone 6.1 Checkpoint 9. Stage build pakai image
# golang resmi menjalankan `ocb` (OpenTelemetry Collector Builder) persis
# proses yang sudah diverifikasi manual Checkpoint 3+8 (fast-fail gate +
# build penuh dengan seluruh komponen existing + supabaseexporter).
# Runtime image minimal (alpine, BUKAN distroless) - butuh ca-certificates
# untuk TLS koneksi Supabase (sslmode=require).

FROM golang:1.26-bookworm AS build

WORKDIR /build

RUN go install go.opentelemetry.io/collector/cmd/builder@v0.159.0

COPY builder-config.yaml ./builder-config.yaml
COPY supabaseexporter ./supabaseexporter

RUN $(go env GOPATH)/bin/builder --config=builder-config.yaml

FROM alpine:latest

RUN apk add --no-cache ca-certificates

COPY --from=build /build/dist/nirwana-otelcol /usr/local/bin/nirwana-otelcol

ENTRYPOINT ["/usr/local/bin/nirwana-otelcol"]

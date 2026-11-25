"""
Precarga de datos de demostración (Seed Data) para PulseGuard Cloud.
Puebla Amazon DynamoDB y Amazon S3 con microservicios empresariales,
métricas históricas y logs auditables para que el dashboard esté listo
incluso si el laboratorio escolar se reinició desde cero.
"""
import json
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from infra.config import (
    DDB_INCIDENTS_TABLE,
    DDB_METRICS_TABLE,
    DDB_SERVICES_TABLE,
    STATE_FILE,
    get_boto3_session,
)


def seed_initial_data():
    print("\n[SEED] Cargando catálogo de microservicios, logs en S3 e incidentes en DynamoDB...")
    session = get_boto3_session()
    ddb = session.resource("dynamodb")
    s3 = session.client("s3")
    sts = session.client("sts")
    account_id = sts.get_caller_identity()["Account"]

    s3_bucket = f"pulseguard-logs-{account_id}"
    if STATE_FILE.exists():
        try:
            st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            s3_bucket = st.get("s3_bucket", s3_bucket)
        except Exception:
            pass

    services_tbl = ddb.Table(DDB_SERVICES_TABLE)
    incidents_tbl = ddb.Table(DDB_INCIDENTS_TABLE)
    metrics_tbl = ddb.Table(DDB_METRICS_TABLE)

    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y-%m-%d")

    initial_services = [
        {
            "service_id": "srv-core-payments",
            "service_name": "Core Payments Engine",
            "endpoint": "https://payments.pulseguard.internal/v2/charge",
            "environment": "production",
            "status": "HEALTHY",
            "last_latency_ms": Decimal("112.4"),
            "last_status_code": Decimal(200),
            "cpu_usage": Decimal("34.2"),
            "memory_usage": Decimal("51.8"),
            "uptime_pct": Decimal("99.98"),
            "last_check": now.isoformat(),
            "last_message": "Transacciones SPEI/Tarjeta operando en rango nominal (<150ms).",
        },
        {
            "service_id": "srv-auth-gateway",
            "service_name": "Auth & OAuth2 Gateway",
            "endpoint": "https://auth.pulseguard.internal/oauth/token",
            "environment": "production",
            "status": "HEALTHY",
            "last_latency_ms": Decimal("68.5"),
            "last_status_code": Decimal(200),
            "cpu_usage": Decimal("29.0"),
            "memory_usage": Decimal("43.5"),
            "uptime_pct": Decimal("99.99"),
            "last_check": now.isoformat(),
            "last_message": "Emisión de tokens JWT y validación MFA sin errores.",
        },
        {
            "service_id": "srv-order-stream",
            "service_name": "Order Stream Processor",
            "endpoint": "https://orders.pulseguard.internal/api/events",
            "environment": "production",
            "status": "DEGRADED",
            "last_latency_ms": Decimal("940.0"),
            "last_status_code": Decimal(200),
            "cpu_usage": Decimal("78.5"),
            "memory_usage": Decimal("74.0"),
            "uptime_pct": Decimal("98.75"),
            "last_check": now.isoformat(),
            "last_message": "Latencia elevada detectada en réplica de lectura secundaria.",
        },
        {
            "service_id": "srv-ml-scoring",
            "service_name": "Fraud ML Scoring API",
            "endpoint": "https://ml.pulseguard.internal/v1/score",
            "environment": "production",
            "status": "HEALTHY",
            "last_latency_ms": Decimal("145.0"),
            "last_status_code": Decimal(200),
            "cpu_usage": Decimal("46.0"),
            "memory_usage": Decimal("64.0"),
            "uptime_pct": Decimal("99.95"),
            "last_check": now.isoformat(),
            "last_message": "Inferencia de modelo antifraude v4.2 respondiendo en SLA.",
        },
        {
            "service_id": "srv-notif-hub",
            "service_name": "Notification & Webhook Hub",
            "endpoint": "https://notify.pulseguard.internal/v1/dispatch",
            "environment": "staging",
            "status": "HEALTHY",
            "last_latency_ms": Decimal("89.0"),
            "last_status_code": Decimal(200),
            "cpu_usage": Decimal("22.0"),
            "memory_usage": Decimal("38.0"),
            "uptime_pct": Decimal("99.97"),
            "last_check": now.isoformat(),
            "last_message": "Cola de despacho de webhooks y correos al día.",
        },
    ]

    for srv in initial_services:
        services_tbl.put_item(Item=srv)

    # Crear logs históricos en S3 y métricas en DynamoDB
    sample_events = [
        ("srv-core-payments", "Core Payments Engine", 112.4, 200, 34.2, "INFO", "Health check OK - Pool de conexiones estable", "HEALTHY"),
        ("srv-auth-gateway", "Auth & OAuth2 Gateway", 68.5, 200, 29.0, "INFO", "Validación OAuth2 completada en 68ms", "HEALTHY"),
        ("srv-order-stream", "Order Stream Processor", 940.0, 200, 78.5, "WARN", "Advertencia: Latencia > 800ms en consulta de catálogo", "DEGRADED"),
        ("srv-ml-scoring", "Fraud ML Scoring API", 145.0, 200, 46.0, "INFO", "Batch de scoring procesado sin anomalías", "HEALTHY"),
        ("srv-notif-hub", "Notification & Webhook Hub", 89.0, 200, 22.0, "INFO", "Heartbeat nominal en nodo de despacho", "HEALTHY"),
    ]

    for idx, (sid, sname, lat, code, cpu, lvl, msg, eval_st) in enumerate(sample_events):
        ts = (now - timedelta(minutes=idx * 3)).isoformat()
        mid = f"seed-met-0{idx+1}"
        s3_key = f"logs/{date_prefix}/{sid}/{mid}.json"

        log_doc = {
            "metric_id": mid,
            "service_id": sid,
            "service_name": sname,
            "timestamp": ts,
            "latency_ms": lat,
            "status_code": code,
            "cpu_usage": cpu,
            "memory_usage": 52.0,
            "log_level": lvl,
            "message": msg,
            "evaluated_status": eval_st,
        }
        try:
            s3.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=json.dumps(log_doc, indent=2).encode("utf-8"),
                ContentType="application/json",
            )
        except Exception as e:
            print(f"[WARN] No se pudo subir seed log a S3: {e}")

        metrics_tbl.put_item(
            Item={
                "metric_id": mid,
                "service_id": sid,
                "service_name": sname,
                "timestamp": ts,
                "epoch_ms": Decimal(int(time.time() * 1000) - idx * 180000),
                "latency_ms": Decimal(str(lat)),
                "status_code": Decimal(code),
                "cpu_usage": Decimal(str(cpu)),
                "memory_usage": Decimal("52.0"),
                "log_level": lvl,
                "message": msg,
                "evaluated_status": eval_st,
                "s3_archive_key": s3_key,
            }
        )

    # Crear 1 incidente abierto de demostración y 1 resuelto
    incidents_tbl.put_item(
        Item={
            "incident_id": "inc-demo-01",
            "service_id": "srv-order-stream",
            "service_name": "Order Stream Processor",
            "severity": "WARNING",
            "status": "OPEN",
            "title": "[WARNING] Anomalía de Latencia en Order Stream Processor",
            "description": "Degradación detectada (HTTP 200, Latencia=940.0ms, CPU=78.5%)",
            "latency_ms": Decimal("940.0"),
            "status_code": Decimal(200),
            "created_at": (now - timedelta(minutes=6)).isoformat(),
            "s3_evidence_key": f"logs/{date_prefix}/srv-order-stream/seed-met-03.json",
        }
    )
    incidents_tbl.put_item(
        Item={
            "incident_id": "inc-demo-00",
            "service_id": "srv-core-payments",
            "service_name": "Core Payments Engine",
            "severity": "CRITICAL",
            "status": "RESOLVED",
            "title": "[CRITICAL] Pico de Timeout en Pasarela Bancaria",
            "description": "HTTP 503 / Latencia=2450ms — Mitigado automáticamente por Auto-Retry y Failover Multi-AZ.",
            "latency_ms": Decimal("2450.0"),
            "status_code": Decimal(503),
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "resolved_at": (now - timedelta(hours=1, minutes=52)).isoformat(),
            "resolution_note": "Failover automático completado sin pérdida de transacciones.",
        }
    )

    print("[SEED] Datos iniciales cargados correctamente en DynamoDB y S3.")


if __name__ == "__main__":
    seed_initial_data()

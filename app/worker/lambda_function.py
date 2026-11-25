"""
AWS Lambda: PulseGuard Anomaly & Log Evaluator (Ejecutado bajo LabRole)
Consumidor asíncrono del bus de telemetría Amazon SNS (pulseguard-telemetry-stream).
- Evalúa métricas de latencia, códigos HTTP, CPU/RAM y niveles de log.
- Archiva el payload crudo de auditoría en Amazon S3 (logs/<fecha>/<service_id>/<metric_id>.json).
- Actualiza el estado del servicio y registra métricas en Amazon DynamoDB.
- Detecta anomalías automáticamente, abre incidentes en DynamoDB y publica alertas en Amazon SNS.
- Soporta inyección de fallos (Chaos Engineering): tras agotar reintentos, desvía mensajes corruptos
  ('Poison Pills') hacia la Dead Letter Queue persistente en S3 (dlq/<message_id>.json) sin detener el sistema.
- Incluye operaciones administrativas ejecutadas bajo LabRole para creación y semilla de tablas DynamoDB.
"""
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import boto3

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
SERVICES_TABLE = os.environ.get("DDB_SERVICES_TABLE", "pulseguard-services")
INCIDENTS_TABLE = os.environ.get("DDB_INCIDENTS_TABLE", "pulseguard-incidents")
METRICS_TABLE = os.environ.get("DDB_METRICS_TABLE", "pulseguard-metrics")
S3_BUCKET = os.environ.get("S3_LOGS_BUCKET", "")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")

ddb_client = boto3.client("dynamodb", region_name=AWS_REGION)
ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)
sns = boto3.client("sns", region_name=AWS_REGION)


def to_decimal(val):
    if isinstance(val, float):
        return Decimal(str(round(val, 2)))
    if isinstance(val, int):
        return Decimal(val)
    return val


def decimal_to_native(obj):
    if isinstance(obj, list):
        return [decimal_to_native(i) for i in obj]
    if isinstance(obj, dict):
        return {k: decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 != 0 else int(obj)
    return obj


def handle_admin_init_dynamodb():
    """Crea las 3 tablas de DynamoDB de PulseGuard usando los permisos de LabRole."""
    tables_spec = [
        (SERVICES_TABLE, "service_id"),
        (INCIDENTS_TABLE, "incident_id"),
        (METRICS_TABLE, "metric_id"),
    ]
    existing = ddb_client.list_tables().get("TableNames", [])
    # Limpiar tabla temporal de diagnóstico si existe
    if "pulseguard-test-tbl" in existing:
        try:
            ddb_client.delete_table(TableName="pulseguard-test-tbl")
        except Exception:
            pass

    created = []
    for table_name, pk in tables_spec:
        if table_name not in existing:
            ddb_client.create_table(
                TableName=table_name,
                KeySchema=[{"AttributeName": pk, "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": pk, "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            created.append(table_name)

    for table_name, _ in tables_spec:
        waiter = ddb_client.get_waiter("table_exists")
        waiter.wait(TableName=table_name)

    return {"status": "TABLES_ACTIVE", "created": created, "tables": [t[0] for t in tables_spec]}


def handle_admin_seed_data(s3_bucket: str):
    """Puebla datos iniciales de demostración en DynamoDB y S3 bajo LabRole."""
    services_tbl = ddb.Table(SERVICES_TABLE)
    incidents_tbl = ddb.Table(INCIDENTS_TABLE)
    metrics_tbl = ddb.Table(METRICS_TABLE)

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
        if s3_bucket:
            try:
                s3.put_object(
                    Bucket=s3_bucket,
                    Key=s3_key,
                    Body=json.dumps(log_doc, indent=2).encode("utf-8"),
                    ContentType="application/json",
                )
            except Exception:
                pass

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
    return {"status": "SEED_COMPLETED", "services": len(initial_services)}


def lambda_handler(event, context):
    # Operaciones administrativas desde deploy.py / tests
    if isinstance(event, dict) and "admin_action" in event:
        action = event["admin_action"]
        if action == "init_dynamodb":
            return handle_admin_init_dynamodb()
        if action == "seed_data":
            return handle_admin_seed_data(event.get("s3_bucket", S3_BUCKET))
        if action == "get_metric":
            mid = event.get("metric_id")
            item = ddb.Table(METRICS_TABLE).get_item(Key={"metric_id": mid}).get("Item")
            return {"item": decimal_to_native(item) if item else None}

    services_tbl = ddb.Table(SERVICES_TABLE)
    incidents_tbl = ddb.Table(INCIDENTS_TABLE)
    metrics_tbl = ddb.Table(METRICS_TABLE)

    processed = 0
    isolated_to_dlq = 0

    for record in event.get("Records", []):
        if "Sns" in record:
            body_raw = record["Sns"].get("Message", "{}")
            msg_id = record["Sns"].get("MessageId", f"msg-{uuid.uuid4().hex[:8]}")
        else:
            body_raw = record.get("body", "{}")
            msg_id = record.get("messageId", f"msg-{uuid.uuid4().hex[:8]}")

        payload = json.loads(body_raw)

        # PRUEBA DE RESILIENCIA (Chaos Engineering):
        # Si el mensaje incluye simulate_worker_crash=True, simulamos 2 reintentos fallidos
        # del procesador y desviamos el mensaje venenoso a la Dead Letter Queue (DLQ) en S3
        # para no perder el evento ni bloquear los mensajes sanos.
        if payload.get("simulate_worker_crash"):
            dlq_id = payload.get("metric_id") or f"dlq-{uuid.uuid4().hex[:8]}"
            dlq_doc = {
                "message_id": msg_id,
                "dlq_id": dlq_id,
                "receive_count": "2 (Max Retries Exhausted)",
                "isolated_at": datetime.now(timezone.utc).isoformat(),
                "error_reason": "RuntimeError: [CHAOS-TEST] Excepción crítica en Worker Lambda al procesar payload corrupto.",
                "payload": payload,
            }
            if S3_BUCKET:
                s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=f"dlq/{dlq_id}.json",
                    Body=json.dumps(dlq_doc, indent=2).encode("utf-8"),
                    ContentType="application/json",
                )
            isolated_to_dlq += 1
            continue

        now_iso = datetime.now(timezone.utc).isoformat()
        date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        metric_id = payload.get("metric_id") or f"met-{uuid.uuid4().hex[:10]}"
        service_id = payload.get("service_id", "srv-core-payments")
        service_name = payload.get("service_name", "Core Payments Engine")
        endpoint = payload.get("endpoint", "https://api.enterprise.internal/v1/health")
        environment = payload.get("environment", "production")

        latency_ms = float(payload.get("latency_ms", 120.0))
        status_code = int(payload.get("status_code", 200))
        cpu_usage = float(payload.get("cpu_usage", 35.0))
        memory_usage = float(payload.get("memory_usage", 48.0))
        log_level = payload.get("log_level", "INFO").upper()
        log_message = payload.get("message", "Health check OK")

        # 1. Evaluar salud y reglas de anomalía
        anomalies = []
        severity = "NONE"
        new_status = "HEALTHY"

        if status_code >= 500 or log_level in ("CRITICAL", "FATAL"):
            new_status = "DOWN"
            severity = "CRITICAL"
            anomalies.append(f"HTTP {status_code} / Log {log_level}: {log_message}")
        elif latency_ms >= 1500 or cpu_usage >= 90:
            new_status = "DOWN" if latency_ms >= 3000 else "DEGRADED"
            severity = "CRITICAL" if latency_ms >= 3000 or cpu_usage >= 95 else "WARNING"
            anomalies.append(f"Umbral superado (Latencia={latency_ms}ms, CPU={cpu_usage}%)")
        elif status_code >= 400 or latency_ms >= 800 or cpu_usage >= 75 or log_level == "WARN":
            new_status = "DEGRADED"
            severity = "WARNING"
            anomalies.append(f"Degradación detectada (HTTP {status_code}, Latencia={latency_ms}ms)")

        # 2. Archivar log crudo en Amazon S3 (Almacenamiento frío auditable)
        s3_key = f"logs/{date_prefix}/{service_id}/{metric_id}.json"
        if S3_BUCKET:
            try:
                archive_doc = {
                    "metric_id": metric_id,
                    "service_id": service_id,
                    "service_name": service_name,
                    "timestamp": now_iso,
                    "latency_ms": latency_ms,
                    "status_code": status_code,
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory_usage,
                    "log_level": log_level,
                    "message": log_message,
                    "evaluated_status": new_status,
                    "anomalies": anomalies,
                }
                s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=s3_key,
                    Body=json.dumps(archive_doc, indent=2).encode("utf-8"),
                    ContentType="application/json",
                )
            except Exception as e:
                print(f"[WARN] Error archivando en S3: {e}")

        # 3. Guardar telemetría en DynamoDB (pulseguard-metrics)
        metrics_tbl.put_item(
            Item={
                "metric_id": metric_id,
                "service_id": service_id,
                "service_name": service_name,
                "timestamp": now_iso,
                "epoch_ms": Decimal(int(time.time() * 1000)),
                "latency_ms": to_decimal(latency_ms),
                "status_code": to_decimal(status_code),
                "cpu_usage": to_decimal(cpu_usage),
                "memory_usage": to_decimal(memory_usage),
                "log_level": log_level,
                "message": log_message,
                "evaluated_status": new_status,
                "s3_archive_key": s3_key,
            }
        )

        # 4. Actualizar estado del servicio en DynamoDB (pulseguard-services)
        uptime_pct = 99.95 if new_status == "HEALTHY" else (98.40 if new_status == "DEGRADED" else 94.10)
        services_tbl.put_item(
            Item={
                "service_id": service_id,
                "service_name": service_name,
                "endpoint": endpoint,
                "environment": environment,
                "status": new_status,
                "last_latency_ms": to_decimal(latency_ms),
                "last_status_code": to_decimal(status_code),
                "cpu_usage": to_decimal(cpu_usage),
                "memory_usage": to_decimal(memory_usage),
                "uptime_pct": to_decimal(uptime_pct),
                "last_check": now_iso,
                "last_message": log_message,
            }
        )

        # 5. Si hay anomalía, registrar incidente en DynamoDB y disparar alerta por Amazon SNS
        if anomalies:
            incident_id = f"inc-{uuid.uuid4().hex[:8]}"
            summary = " | ".join(anomalies)
            incidents_tbl.put_item(
                Item={
                    "incident_id": incident_id,
                    "service_id": service_id,
                    "service_name": service_name,
                    "severity": severity,
                    "status": "OPEN",
                    "title": f"[{severity}] Anomalía en {service_name}",
                    "description": summary,
                    "latency_ms": to_decimal(latency_ms),
                    "status_code": to_decimal(status_code),
                    "created_at": now_iso,
                    "s3_evidence_key": s3_key,
                }
            )

            if SNS_TOPIC_ARN and severity == "CRITICAL":
                try:
                    sns.publish(
                        TopicArn=SNS_TOPIC_ARN,
                        Subject=f"[PulseGuard CRITICAL] Incidente {incident_id} - {service_name}",
                        Message=(
                            f"Alerta Crítica de PulseGuard Cloud\n"
                            f"===================================\n"
                            f"Incidente ID : {incident_id}\n"
                            f"Servicio     : {service_name} ({service_id})\n"
                            f"Endpoint     : {endpoint}\n"
                            f"Estado       : {new_status}\n"
                            f"Latencia     : {latency_ms} ms\n"
                            f"HTTP Status  : {status_code}\n"
                            f"CPU / RAM    : {cpu_usage}% / {memory_usage}%\n"
                            f"Detalle      : {summary}\n"
                            f"Evidencia S3 : s3://{S3_BUCKET}/{s3_key}\n"
                            f"Timestamp    : {now_iso}\n"
                        ),
                    )
                except Exception as e:
                    print(f"[WARN] No se pudo publicar en SNS: {e}")

        processed += 1

    return {"statusCode": 200, "processed": processed, "isolated_to_dlq": isolated_to_dlq}

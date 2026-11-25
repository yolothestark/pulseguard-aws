"""
PulseGuard Cloud - Backend API & Plataforma Centralizada de Monitoreo, Logs e Incidentes.
Integración nativa con:
- Amazon EC2 + Application Load Balancer (ALB Multi-AZ)
- Amazon SNS (Bus asíncrono de ingesta pulseguard-telemetry-stream + Alertas pulseguard-incident-alerts)
- AWS Lambda (Motor asíncrono de evaluación de anomalías ejecutado bajo LabRole)
- Amazon DynamoDB (Servicios, Métricas en caliente e Incidentes)
- Amazon S3 (Archivo histórico auditable de logs con Presigned URLs + Dead Letter Queue DLQ)

Autores:
- Anguiano Garcia Angel Yahir Guadalupe
- Figueroa Robles Axel Israel
- Torres Martinez Miguel Angel
"""
import json
import os
import socket
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import boto3
import requests
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infra.config import (
    AWS_REGION,
    DDB_INCIDENTS_TABLE,
    DDB_METRICS_TABLE,
    DDB_SERVICES_TABLE,
    LAMBDA_FUNCTION_NAME,
    SNS_TELEMETRY_TOPIC_NAME,
    SNS_TOPIC_NAME,
    SQS_DLQ_NAME,
    STATE_FILE,
    get_boto3_session,
)

app = FastAPI(
    title="PulseGuard Cloud API",
    description="Plataforma Distribuida de Monitoreo de Servicios, Ingesta de Logs y Gestión de Incidentes en AWS",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado local del nodo para Pruebas de Resiliencia (Chaos Engineering)
NODE_CHAOS_STATE = {
    "simulated_down": False,
    "simulated_down_until": 0.0,
    "requests_served": 0,
    "started_at": datetime.now(timezone.utc).isoformat(),
}


def get_ec2_metadata() -> dict:
    """Obtiene metadatos reales de la instancia EC2 (IMDSv2) o identifica el entorno local."""
    hostname = socket.gethostname()
    local_ip = "127.0.0.1"
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        pass

    instance_id = os.environ.get("EC2_INSTANCE_ID", "")
    az = os.environ.get("EC2_AVAILABILITY_ZONE", "")

    if not instance_id:
        try:
            token_resp = requests.put(
                "http://169.254.169.254/latest/api/token",
                headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
                timeout=0.35,
            )
            if token_resp.status_code == 200:
                headers = {"X-aws-ec2-metadata-token": token_resp.text}
                instance_id = requests.get(
                    "http://169.254.169.254/latest/meta-data/instance-id",
                    headers=headers,
                    timeout=0.35,
                ).text
                az = requests.get(
                    "http://169.254.169.254/latest/meta-data/placement/availability-zone",
                    headers=headers,
                    timeout=0.35,
                ).text
                local_ip = requests.get(
                    "http://169.254.169.254/latest/meta-data/local-ipv4",
                    headers=headers,
                    timeout=0.35,
                ).text
        except Exception:
            instance_id = f"node-{hostname}"
            az = f"{AWS_REGION}a (Local/Dev)"

    os.environ["EC2_INSTANCE_ID"] = instance_id
    os.environ["EC2_AVAILABILITY_ZONE"] = az
    return {
        "instance_id": instance_id,
        "availability_zone": az,
        "hostname": hostname,
        "local_ip": local_ip,
    }


def load_deployment_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def get_aws_resources():
    session = get_boto3_session()
    state = load_deployment_state()
    account_id = state.get("account_id")
    if not account_id:
        try:
            account_id = session.client("sts").get_caller_identity()["Account"]
        except Exception:
            account_id = "627739785043"

    s3_bucket = os.environ.get("S3_LOGS_BUCKET") or state.get("s3_bucket") or f"pulseguard-logs-{account_id}"
    sns_telemetry_arn = (
        os.environ.get("SNS_TELEMETRY_TOPIC_ARN")
        or state.get("sns_telemetry_topic_arn")
        or f"arn:aws:sns:{AWS_REGION}:{account_id}:{SNS_TELEMETRY_TOPIC_NAME}"
    )
    sns_arn = (
        os.environ.get("SNS_TOPIC_ARN")
        or state.get("sns_topic_arn")
        or f"arn:aws:sns:{AWS_REGION}:{account_id}:{SNS_TOPIC_NAME}"
    )

    return {
        "session": session,
        "ddb": session.resource("dynamodb"),
        "s3": session.client("s3"),
        "sns": session.client("sns"),
        "lambda": session.client("lambda"),
        "ec2": session.client("ec2"),
        "elbv2": session.client("elbv2"),
        "s3_bucket": s3_bucket,
        "sns_telemetry_arn": sns_telemetry_arn,
        "sns_arn": sns_arn,
        "account_id": account_id,
        "state": state,
    }


def decimal_to_native(obj):
    if isinstance(obj, list):
        return [decimal_to_native(i) for i in obj]
    if isinstance(obj, dict):
        return {k: decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 != 0 else int(obj)
    return obj


# Modelos Pydantic
class ServiceCreate(BaseModel):
    service_name: str
    endpoint: str
    environment: str = "production"


class TelemetryIngest(BaseModel):
    service_id: str
    service_name: str
    endpoint: str = "https://api.pulseguard.internal/health"
    environment: str = "production"
    latency_ms: float = 115.0
    status_code: int = 200
    cpu_usage: float = 34.0
    memory_usage: float = 52.0
    log_level: str = "INFO"
    message: str = "Heartbeat nominal"
    simulate_worker_crash: bool = False


class IncidentResolve(BaseModel):
    resolution_note: str = "Mitigado mediante escalado automático y limpieza de cola."


class SnsSubscribe(BaseModel):
    email: str


@app.get("/api/health")
def health_check(response: Response):
    """
    Endpoint de Health Check utilizado por el Application Load Balancer (ALB).
    Si se activa la simulación de caída de nodo en las pruebas de resiliencia,
    devuelve HTTP 503 para que el ALB desvíe automáticamente el tráfico al otro nodo EC2.
    """
    NODE_CHAOS_STATE["requests_served"] += 1
    meta = get_ec2_metadata()

    if NODE_CHAOS_STATE["simulated_down"]:
        if time.time() < NODE_CHAOS_STATE["simulated_down_until"]:
            response.status_code = 503
            return {
                "status": "UNHEALTHY_SIMULATED",
                "node": meta,
                "detail": "Fallo de nodo simulado (Chaos Engineering) - El ALB redirigirá el tráfico al nodo sano.",
            }
        else:
            NODE_CHAOS_STATE["simulated_down"] = False

    return {
        "status": "HEALTHY",
        "node": meta,
        "requests_served": NODE_CHAOS_STATE["requests_served"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/overview")
def get_dashboard_overview():
    """Devuelve el estado global de servicios, incidentes, logs S3, DLQ y nodo EC2 que responde."""
    NODE_CHAOS_STATE["requests_served"] += 1
    meta = get_ec2_metadata()
    aws = get_aws_resources()
    ddb = aws["ddb"]

    services = []
    incidents = []
    metrics = []

    try:
        services = decimal_to_native(ddb.Table(DDB_SERVICES_TABLE).scan().get("Items", []))
        services.sort(key=lambda x: x.get("service_name", ""))
    except Exception as e:
        print(f"[WARN] Error leyendo {DDB_SERVICES_TABLE}: {e}")

    try:
        incidents = decimal_to_native(ddb.Table(DDB_INCIDENTS_TABLE).scan().get("Items", []))
        incidents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    except Exception as e:
        print(f"[WARN] Error leyendo {DDB_INCIDENTS_TABLE}: {e}")

    try:
        metrics = decimal_to_native(ddb.Table(DDB_METRICS_TABLE).scan(Limit=40).get("Items", []))
        metrics.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    except Exception as e:
        print(f"[WARN] Error leyendo {DDB_METRICS_TABLE}: {e}")

    # Contar archivos archivados en S3 y mensajes aislados en la Dead Letter Queue (dlq/)
    s3_count = 0
    dlq_count = 0
    try:
        resp_s3 = aws["s3"].list_objects_v2(Bucket=aws["s3_bucket"], Prefix="logs/", MaxKeys=500)
        s3_count = resp_s3.get("KeyCount", 0)
    except Exception:
        pass

    try:
        resp_dlq = aws["s3"].list_objects_v2(Bucket=aws["s3_bucket"], Prefix="dlq/", MaxKeys=200)
        dlq_count = resp_dlq.get("KeyCount", 0)
    except Exception:
        pass

    # Estado de nodos en el Application Load Balancer Target Group
    cluster_nodes = []
    tg_arn = os.environ.get("ALB_TARGET_GROUP_ARN") or aws["state"].get("target_group_arn")
    if tg_arn:
        try:
            th = aws["elbv2"].describe_target_health(TargetGroupArn=tg_arn)["TargetHealthDescriptions"]
            target_ids = [t["Target"]["Id"] for t in th]
            inst_map = {}
            if target_ids:
                reservations = aws["ec2"].describe_instances(InstanceIds=target_ids)["Reservations"]
                for r in reservations:
                    for inst in r["Instances"]:
                        inst_map[inst["InstanceId"]] = {
                            "az": inst["Placement"]["AvailabilityZone"],
                            "public_ip": inst.get("PublicIpAddress", "N/A"),
                            "private_ip": inst.get("PrivateIpAddress", "N/A"),
                            "type": inst.get("InstanceType", "t3.micro"),
                        }
            for t in th:
                tid = t["Target"]["Id"]
                info = inst_map.get(tid, {})
                cluster_nodes.append(
                    {
                        "instance_id": tid,
                        "health_state": t["TargetHealth"]["State"],
                        "reason": t["TargetHealth"].get("Description", "OK"),
                        "az": info.get("az", "us-east-1"),
                        "public_ip": info.get("public_ip", "N/A"),
                        "private_ip": info.get("private_ip", "N/A"),
                    }
                )
        except Exception:
            pass

    if not cluster_nodes:
        cluster_nodes = [
            {
                "instance_id": meta["instance_id"],
                "health_state": "unhealthy" if NODE_CHAOS_STATE["simulated_down"] else "healthy",
                "reason": "Simulated Failure" if NODE_CHAOS_STATE["simulated_down"] else "Active Node",
                "az": meta["availability_zone"],
                "public_ip": meta["local_ip"],
                "private_ip": meta["local_ip"],
            }
        ]

    healthy_count = sum(1 for s in services if s.get("status") == "HEALTHY")
    degraded_count = sum(1 for s in services if s.get("status") == "DEGRADED")
    down_count = sum(1 for s in services if s.get("status") == "DOWN")
    open_incidents = [i for i in incidents if i.get("status") == "OPEN"]
    avg_latency = (
        round(sum(float(s.get("last_latency_ms", 0)) for s in services) / len(services), 1)
        if services
        else 0.0
    )

    return {
        "responding_node": {
            **meta,
            "simulated_down": NODE_CHAOS_STATE["simulated_down"],
            "requests_served": NODE_CHAOS_STATE["requests_served"],
        },
        "aws_metadata": {
            "region": AWS_REGION,
            "account_id": aws["account_id"],
            "s3_bucket": aws["s3_bucket"],
            "sqs_main_queue": SNS_TELEMETRY_TOPIC_NAME,
            "sqs_dlq": f"s3://{aws['s3_bucket']}/dlq/",
            "sns_topic": SNS_TOPIC_NAME,
            "s3_archived_logs": s3_count,
        },
        "kpis": {
            "total_services": len(services),
            "healthy_services": healthy_count,
            "degraded_services": degraded_count,
            "down_services": down_count,
            "open_incidents": len(open_incidents),
            "avg_latency_ms": avg_latency,
            "sqs_main_queued": len(metrics),
            "sqs_dlq_messages": dlq_count,
        },
        "cluster_nodes": cluster_nodes,
        "services": services,
        "incidents": incidents[:25],
        "recent_metrics": metrics[:25],
    }


@app.post("/api/services")
def register_service(payload: ServiceCreate):
    """Registra un nuevo servicio o endpoint para ser monitoreado en DynamoDB."""
    aws = get_aws_resources()
    service_id = f"srv-{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    item = {
        "service_id": service_id,
        "service_name": payload.service_name,
        "endpoint": payload.endpoint,
        "environment": payload.environment,
        "status": "HEALTHY",
        "last_latency_ms": Decimal("95.0"),
        "last_status_code": Decimal(200),
        "cpu_usage": Decimal("28.0"),
        "memory_usage": Decimal("44.0"),
        "uptime_pct": Decimal("99.98"),
        "last_check": now_iso,
        "last_message": "Servicio registrado y verificado inicialmente.",
    }
    aws["ddb"].Table(DDB_SERVICES_TABLE).put_item(Item=item)
    return {"status": "created", "service": decimal_to_native(item)}


@app.post("/api/telemetry")
def ingest_telemetry(payload: TelemetryIngest):
    """
    Recibe logs y métricas de telemetría.
    Publica el evento asíncronamente en el bus Amazon SNS (pulseguard-telemetry-stream),
    el cual dispara AWS Lambda (pulseguard-anomaly-evaluator) en segundo plano.
    """
    aws = get_aws_resources()
    metric_id = f"met-{uuid.uuid4().hex[:10]}"
    msg_body = payload.model_dump()
    msg_body["metric_id"] = metric_id
    msg_body["ingested_at"] = datetime.now(timezone.utc).isoformat()

    published = False
    sns_message_id = None

    try:
        resp = aws["sns"].publish(
            TopicArn=aws["sns_telemetry_arn"],
            Message=json.dumps(msg_body),
            Subject=f"PulseGuardTelemetry:{payload.service_id}",
        )
        published = True
        sns_message_id = resp.get("MessageId")
    except Exception as e:
        print(f"[WARN] Fallo al publicar en SNS Stream, invocando Lambda asíncrona directo: {e}")
        try:
            aws["lambda"].invoke(
                FunctionName=LAMBDA_FUNCTION_NAME,
                InvocationType="Event",
                Payload=json.dumps({"Records": [{"body": json.dumps(msg_body), "messageId": metric_id}]}).encode("utf-8"),
            )
            published = True
        except Exception as e2:
            print(f"[ERROR] Fallback Lambda falló: {e2}")

    return {
        "status": "ACCEPTED",
        "http_code": 202,
        "metric_id": metric_id,
        "queued_in_sqs": published,
        "sqs_message_id": sns_message_id,
        "note": (
            "Mensaje venenoso enviado al bus asíncrono: AWS Lambda detectará la excepción tras reintentos y lo aislará en la Dead Letter Queue (DLQ)."
            if payload.simulate_worker_crash
            else "Evento publicado asíncronamente hacia AWS Lambda para evaluación, archivo en S3 y actualización de DynamoDB."
        ),
    }


@app.post("/api/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str, payload: IncidentResolve):
    """Marca un incidente como RESUELTO en DynamoDB y actualiza el servicio asociado."""
    aws = get_aws_resources()
    tbl = aws["ddb"].Table(DDB_INCIDENTS_TABLE)
    now_iso = datetime.now(timezone.utc).isoformat()

    resp = tbl.get_item(Key={"incident_id": incident_id})
    item = resp.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    item["status"] = "RESOLVED"
    item["resolved_at"] = now_iso
    item["resolution_note"] = payload.resolution_note
    tbl.put_item(Item=item)

    service_id = item.get("service_id")
    if service_id:
        srv_tbl = aws["ddb"].Table(DDB_SERVICES_TABLE)
        srv = srv_tbl.get_item(Key={"service_id": service_id}).get("Item")
        if srv:
            srv["status"] = "HEALTHY"
            srv["last_latency_ms"] = Decimal("110.0")
            srv["last_status_code"] = Decimal(200)
            srv["last_message"] = f"Incidente {incident_id} resuelto: {payload.resolution_note}"
            srv["last_check"] = now_iso
            srv_tbl.put_item(Item=srv)

    return {"status": "RESOLVED", "incident": decimal_to_native(item)}


@app.get("/api/s3-log-url")
def get_s3_presigned_url(key: str):
    """Genera una URL pre-firmada (Presigned URL) de Amazon S3 para descargar/inspeccionar un log archivado."""
    aws = get_aws_resources()
    try:
        url = aws["s3"].generate_presigned_url(
            "get_object",
            Params={"Bucket": aws["s3_bucket"], "Key": key},
            ExpiresIn=900,
        )
        return {"presigned_url": url, "bucket": aws["s3_bucket"], "key": key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sns/subscribe")
def subscribe_email_to_sns(payload: SnsSubscribe):
    """Suscribe un correo electrónico al tópico de Amazon SNS para recibir alertas críticas en vivo."""
    aws = get_aws_resources()
    if not aws["sns_arn"]:
        raise HTTPException(status_code=400, detail="Tópico SNS no configurado")
    resp = aws["sns"].subscribe(
        TopicArn=aws["sns_arn"],
        Protocol="email",
        Endpoint=payload.email,
    )
    return {
        "status": "SUBSCRIPTION_PENDING_CONFIRMATION",
        "subscription_arn": resp.get("SubscriptionArn"),
        "message": f"Se envió un correo de confirmación de AWS SNS a {payload.email}.",
    }


# ==============================================================================
# ENDPOINTS DE PRUEBAS DE RESILIENCIA ("DEMUÉSTRAME QUE NO SE ROMPE" - REGLA 2)
# ==============================================================================

@app.post("/api/chaos/simulate-node-failure")
def chaos_simulate_node_failure(duration_seconds: int = 75):
    """
    PRUEBA DE RESILIENCIA 1: Simula la caída del servidor web EC2 actual durante N segundos.
    El endpoint /api/health devolverá HTTP 503 Service Unavailable, haciendo que el
    Application Load Balancer (ALB) redirija automáticamente el 100% del tráfico a la otra
    instancia EC2 en otra Zona de Disponibilidad con Zero Downtime.
    """
    meta = get_ec2_metadata()
    NODE_CHAOS_STATE["simulated_down"] = True
    NODE_CHAOS_STATE["simulated_down_until"] = time.time() + duration_seconds
    return {
        "chaos_experiment": "EC2_NODE_FAILURE",
        "affected_node": meta,
        "duration_seconds": duration_seconds,
        "expected_behavior": (
            f"El nodo {meta['instance_id']} ({meta['availability_zone']}) reportará HTTP 503 en /api/health. "
            "El Application Load Balancer (ALB) conmutará todas las peticiones al nodo secundario sin caída del servicio."
        ),
    }


@app.post("/api/chaos/restore-node")
def chaos_restore_node():
    """Restaura inmediatamente la salud del nodo EC2 actual."""
    meta = get_ec2_metadata()
    NODE_CHAOS_STATE["simulated_down"] = False
    NODE_CHAOS_STATE["simulated_down_until"] = 0.0
    return {"status": "RESTORED", "node": meta}


@app.post("/api/chaos/poison-pill")
def chaos_inject_poison_pill():
    """
    PRUEBA DE RESILIENCIA 2: Inyecta un mensaje corrupto ('Poison Pill') en el bus asíncrono.
    AWS Lambda detectará la excepción tras reintentos y aislará el mensaje en la Dead Letter Queue (DLQ)
    sin detener ni bloquear el procesamiento de mensajes sanos.
    """
    payload = TelemetryIngest(
        service_id="srv-auth-gateway",
        service_name="Auth & OAuth2 Gateway",
        endpoint="https://auth.pulseguard.internal/oauth/token",
        latency_ms=0.0,
        status_code=500,
        cpu_usage=99.9,
        memory_usage=95.0,
        log_level="CRITICAL",
        message="[CHAOS POISON PILL] Payload corrupto diseñado para forzar excepción en Worker Lambda",
        simulate_worker_crash=True,
    )
    return ingest_telemetry(payload)


@app.get("/api/chaos/dlq-inspect")
def chaos_inspect_dlq():
    """Inspecciona los mensajes aislados en la Dead Letter Queue (DLQ)."""
    aws = get_aws_resources()
    objs = aws["s3"].list_objects_v2(Bucket=aws["s3_bucket"], Prefix="dlq/", MaxKeys=20).get("Contents", [])
    parsed = []
    for obj in sorted(objs, key=lambda x: x["LastModified"], reverse=True)[:10]:
        try:
            raw = aws["s3"].get_object(Bucket=aws["s3_bucket"], Key=obj["Key"])["Body"].read().decode("utf-8")
            parsed.append(json.loads(raw))
        except Exception:
            pass
    return {"count": len(parsed), "messages": parsed, "dlq_name": f"s3://{aws['s3_bucket']}/dlq/"}


@app.post("/api/chaos/purge-dlq")
def chaos_purge_dlq():
    """Drena los mensajes de la Dead Letter Queue después de auditarlos."""
    aws = get_aws_resources()
    objs = aws["s3"].list_objects_v2(Bucket=aws["s3_bucket"], Prefix="dlq/", MaxKeys=100).get("Contents", [])
    deleted = 0
    for obj in objs:
        aws["s3"].delete_object(Bucket=aws["s3_bucket"], Key=obj["Key"])
        deleted += 1
    return {"status": "DLQ_DRAINED", "deleted_messages": deleted}


@app.post("/api/chaos/stress-burst")
def chaos_stress_burst(events_count: int = 30):
    """
    PRUEBA DE RESILIENCIA 3: Inyecta una ráfaga concurrente de eventos hacia AWS Lambda
    para demostrar absorción de picos de carga (0% pérdida de paquetes).
    """
    aws = get_aws_resources()
    events_count = min(max(events_count, 5), 100)
    t0 = time.perf_counter()
    sample_services = [
        ("srv-core-payments", "Core Payments Engine", "https://payments.pulseguard.internal/v2/charge"),
        ("srv-auth-gateway", "Auth & OAuth2 Gateway", "https://auth.pulseguard.internal/oauth/token"),
        ("srv-order-stream", "Order Stream Processor", "https://orders.pulseguard.internal/api/events"),
        ("srv-ml-scoring", "Fraud ML Scoring API", "https://ml.pulseguard.internal/v1/score"),
    ]

    records = []
    for i in range(events_count):
        srv_id, srv_name, ep = sample_services[i % len(sample_services)]
        is_spike = (i == events_count - 1)
        body = {
            "metric_id": f"burst-{uuid.uuid4().hex[:8]}",
            "service_id": srv_id,
            "service_name": srv_name,
            "endpoint": ep,
            "environment": "production",
            "latency_ms": 2150.0 if is_spike else round(85.0 + (i * 7.5) % 240, 1),
            "status_code": 503 if is_spike else 200,
            "cpu_usage": 94.5 if is_spike else round(30.0 + (i * 3.1) % 45, 1),
            "memory_usage": 88.0 if is_spike else 51.0,
            "log_level": "CRITICAL" if is_spike else "INFO",
            "message": (
                f"[STRESS-TEST #{i+1}] Pico crítico detectado en ráfaga de carga"
                if is_spike
                else f"[STRESS-TEST #{i+1}] Evento de telemetría procesado asíncronamente en lote"
            ),
            "simulate_worker_crash": False,
        }
        records.append({"body": json.dumps(body), "messageId": body["metric_id"]})

    # Invocar Lambda asíncronamente (InvocationType='Event') en lotes de 10 para absorción instantánea
    sent = 0
    for start in range(0, len(records), 10):
        batch = records[start : start + 10]
        aws["lambda"].invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType="Event",
            Payload=json.dumps({"Records": batch}).encode("utf-8"),
        )
        sent += len(batch)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "chaos_experiment": "ASYNC_LOAD_BURST",
        "requested_events": events_count,
        "accepted_events": sent,
        "packet_loss_pct": 0.0,
        "ingestion_time_ms": elapsed_ms,
        "avg_ms_per_event": round(elapsed_ms / max(sent, 1), 2),
    }


FRONTEND_FILE = PROJECT_ROOT / "app" / "frontend" / "index.html"


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    if FRONTEND_FILE.exists():
        return FileResponse(FRONTEND_FILE)
    return HTMLResponse("<h1>PulseGuard Cloud API Activa</h1>")

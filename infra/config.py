"""
Configuración central y cargador de sesión AWS para PulseGuard Cloud.
Lee automáticamente aws_credentials.txt del laboratorio escolar (AWS Academy Learner Lab)
o variables de entorno / ~/.aws/credentials.
"""
import configparser
import os
from pathlib import Path
import boto3

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / "aws_credentials.txt"
STATE_FILE = Path(__file__).resolve().parent / ".deployment_state.json"

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
PROJECT_PREFIX = "pulseguard"

# Nombres de recursos AWS
DDB_SERVICES_TABLE = f"{PROJECT_PREFIX}-services"
DDB_INCIDENTS_TABLE = f"{PROJECT_PREFIX}-incidents"
DDB_METRICS_TABLE = f"{PROJECT_PREFIX}-metrics"

SNS_TELEMETRY_TOPIC_NAME = f"{PROJECT_PREFIX}-telemetry-stream"
SNS_TOPIC_NAME = f"{PROJECT_PREFIX}-incident-alerts"
S3_DLQ_PREFIX = "dlq/"
LAMBDA_FUNCTION_NAME = f"{PROJECT_PREFIX}-anomaly-evaluator"

# Alias de compatibilidad para reportes
SQS_MAIN_QUEUE_NAME = SNS_TELEMETRY_TOPIC_NAME
SQS_DLQ_NAME = f"{PROJECT_PREFIX}-s3-dlq"

ALB_NAME = f"{PROJECT_PREFIX}-alb"
TG_NAME = f"{PROJECT_PREFIX}-tg"
SG_ALB_NAME = f"{PROJECT_PREFIX}-alb-sg"
SG_EC2_NAME = f"{PROJECT_PREFIX}-ec2-sg"
ASG_NAME = f"{PROJECT_PREFIX}-asg"
LAUNCH_TEMPLATE_NAME = f"{PROJECT_PREFIX}-lt"


def load_aws_credentials() -> dict:
    """Extrae aws_access_key_id, aws_secret_access_key y aws_session_token de aws_credentials.txt."""
    if CREDENTIALS_FILE.exists():
        parser = configparser.ConfigParser()
        raw_text = CREDENTIALS_FILE.read_text(encoding="utf-8").strip()
        if raw_text and not raw_text.startswith("#"):
            if "[default]" not in raw_text:
                raw_text = "[default]\n" + raw_text
            parser.read_string(raw_text)
            if "default" in parser:
                sec = parser["default"]
                key_id = sec.get("aws_access_key_id", "").strip()
                secret = sec.get("aws_secret_access_key", "").strip()
                token = sec.get("aws_session_token", "").strip()
                if key_id and secret:
                    creds = {
                        "aws_access_key_id": key_id,
                        "aws_secret_access_key": secret,
                        "region_name": AWS_REGION,
                    }
                    if token:
                        creds["aws_session_token"] = token
                    return creds
    return {"region_name": AWS_REGION}


def get_boto3_session() -> boto3.Session:
    """Devuelve una sesión de Boto3 autenticada contra el laboratorio escolar."""
    creds = load_aws_credentials()
    return boto3.Session(**creds)

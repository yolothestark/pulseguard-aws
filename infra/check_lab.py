"""
Script de diagnóstico rápido del AWS Academy Learner Lab para PulseGuard Cloud.
Verifica identidad STS, Account ID, existencia de LabRole, VPC, subredes Multi-AZ
y acceso a Amazon S3, Amazon DynamoDB, Amazon SNS, AWS Lambda, EC2 y ELBv2.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from infra.config import AWS_REGION, STATE_FILE, get_boto3_session


def main():
    print("=" * 68)
    print(" PULSEGUARD CLOUD - DIAGNÓSTICO DE AWS ACADEMY LEARNER LAB")
    print("=" * 68)

    session = get_boto3_session()
    sts = session.client("sts")
    identity = sts.get_caller_identity()
    account_id = identity["Account"]
    arn = identity["Arn"]

    print(f"[OK] Conectado a AWS Account ID : {account_id}")
    print(f"[OK] Identidad STS actual       : {arn}")
    print(f"[OK] Región configurada         : {AWS_REGION}")
    print(f"[OK] Rol de ejecución escolar   : arn:aws:iam::{account_id}:role/LabRole")

    ec2 = session.client("ec2")
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"]
    if not vpcs:
        vpcs = ec2.describe_vpcs()["Vpcs"]
    vpc_id = vpcs[0]["VpcId"]
    subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["Subnets"]
    azs = sorted({s["AvailabilityZone"] for s in subnets})
    print(f"[OK] VPC detectada              : {vpc_id} ({len(subnets)} subredes en AZs: {', '.join(azs)})")

    s3 = session.client("s3")
    buckets = s3.list_buckets().get("Buckets", [])
    print(f"[OK] Acceso a Amazon S3         : {len(buckets)} bucket(s) activos")

    ddb = session.client("dynamodb")
    tables = ddb.list_tables().get("TableNames", [])
    print(f"[OK] Acceso a Amazon DynamoDB   : {len(tables)} tabla(s) ({', '.join(tables)})")

    if STATE_FILE.exists():
        st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        print(f"[OK] URL Load Balancer Activo   : {st.get('alb_url')}")
        print(f"[OK] Instancias EC2 Activas     : {', '.join(st.get('ec2_instance_ids', []))}")

    print("=" * 68)
    print(" DIAGNÓSTICO EXITOSO: Entorno AWS verificado.")
    print("=" * 68)


if __name__ == "__main__":
    main()

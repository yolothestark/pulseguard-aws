"""
REGLA 1: Script de Aprovisionamiento Automatizado de Infraestructura AWS (Cero Clics en Consola)
Proyecto: PulseGuard Cloud
Autores:
- Anguiano Garcia Angel Yahir Guadalupe
- Figueroa Robles Axel Israel
- Torres Martinez Miguel Angel

Construye de forma 100% automatizada e idempotente toda la arquitectura en AWS (compatible con AWS Academy Cloud Foundations):
1. Amazon S3 Bucket (Almacenamiento de logs auditables, Dead Letter Queue DLQ y artefacto de despliegue EC2)
2. Amazon SNS (Bus asíncrono de telemetría pulseguard-telemetry-stream + Tópico de alertas pulseguard-incident-alerts)
3. AWS Lambda (Motor asíncrono evaluador de anomalías bajo LabRole suscrito a SNS)
4. Amazon DynamoDB (3 tablas Serverless creadas e inicializadas vía LabRole: services, incidents, metrics)
5. VPC Security Groups + Application Load Balancer (ALB) + Target Group Multi-AZ con Health Check (/api/health)
6. Clúster de 2 Instancias Amazon EC2 (t3.micro, EBS gp2, LabInstanceProfile) en 2 Zonas de Disponibilidad (us-east-1a y us-east-1b)
"""
import io
import json
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from infra.config import (
    ALB_NAME,
    AWS_REGION,
    DDB_INCIDENTS_TABLE,
    DDB_METRICS_TABLE,
    DDB_SERVICES_TABLE,
    LAMBDA_FUNCTION_NAME,
    PROJECT_PREFIX,
    PROJECT_ROOT,
    SG_ALB_NAME,
    SG_EC2_NAME,
    SNS_TELEMETRY_TOPIC_NAME,
    SNS_TOPIC_NAME,
    STATE_FILE,
    TG_NAME,
    get_boto3_session,
)


def ensure_s3_bucket(s3, bucket_name: str):
    print(f"\n[1/7] Configurando Bucket de Amazon S3: {bucket_name} ...")
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"  -> Bucket S3 ya existe: {bucket_name}")
    except Exception:
        if AWS_REGION == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
            )
        print(f"  -> Bucket S3 creado: {bucket_name}")

    s3.put_bucket_cors(
        Bucket=bucket_name,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedHeaders": ["*"],
                    "AllowedMethods": ["GET", "HEAD"],
                    "AllowedOrigins": ["*"],
                    "MaxAgeSeconds": 3000,
                }
            ]
        },
    )


def ensure_sns_topics(sns):
    print("\n[2/7] Configurando Tópicos en Amazon SNS (Bus de Telemetría + Alertas de Incidentes) ...")
    t_stream = sns.create_topic(Name=SNS_TELEMETRY_TOPIC_NAME)["TopicArn"]
    t_alerts = sns.create_topic(Name=SNS_TOPIC_NAME)["TopicArn"]
    print(f"  -> Bus Asíncrono SNS : {t_stream}")
    print(f"  -> Tópico Alertas SNS: {t_alerts}")
    return t_stream, t_alerts


def build_lambda_zip() -> bytes:
    buf = io.BytesIO()
    lambda_file = PROJECT_ROOT / "app" / "worker" / "lambda_function.py"
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(lambda_file, arcname="lambda_function.py")
    return buf.getvalue()


def ensure_lambda_and_dynamodb(lambda_client, sns_client, role_arn: str, s3_bucket: str, sns_telemetry_arn: str, sns_alerts_arn: str):
    print(f"\n[3/7] Desplegando Función AWS Lambda ({LAMBDA_FUNCTION_NAME}) con LabRole ...")
    zip_bytes = build_lambda_zip()
    env_vars = {
        "Variables": {
            "DDB_SERVICES_TABLE": DDB_SERVICES_TABLE,
            "DDB_INCIDENTS_TABLE": DDB_INCIDENTS_TABLE,
            "DDB_METRICS_TABLE": DDB_METRICS_TABLE,
            "S3_LOGS_BUCKET": s3_bucket,
            "SNS_TOPIC_ARN": sns_alerts_arn,
        }
    }

    try:
        fn_info = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        lambda_arn = fn_info["Configuration"]["FunctionArn"]
        print("  -> Actualizando código y configuración de función Lambda existente ...")
        lambda_client.update_function_code(FunctionName=LAMBDA_FUNCTION_NAME, ZipFile=zip_bytes)
        waiter = lambda_client.get_waiter("function_updated_v2")
        waiter.wait(FunctionName=LAMBDA_FUNCTION_NAME)
        lambda_client.update_function_configuration(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Environment=env_vars,
            Timeout=25,
            MemorySize=256,
        )
        waiter.wait(FunctionName=LAMBDA_FUNCTION_NAME)
    except lambda_client.exceptions.ResourceNotFoundException:
        print("  -> Creando nueva función AWS Lambda ...")
        create_resp = lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime="python3.12",
            Role=role_arn,
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": zip_bytes},
            Timeout=25,
            MemorySize=256,
            Environment=env_vars,
            Description="PulseGuard Cloud - Evaluador asíncrono de telemetría y anomalías",
        )
        lambda_arn = create_resp["FunctionArn"]
        waiter = lambda_client.get_waiter("function_active_v2")
        waiter.wait(FunctionName=LAMBDA_FUNCTION_NAME)

    # Suscribir Lambda al bus de telemetría SNS
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId="PulseGuardSNSInvokePermission",
            Action="lambda:InvokeFunction",
            Principal="sns.amazonaws.com",
            SourceArn=sns_telemetry_arn,
        )
    except Exception:
        pass

    sns_client.subscribe(
        TopicArn=sns_telemetry_arn,
        Protocol="lambda",
        Endpoint=lambda_arn,
    )
    print(f"  -> Trigger asíncrono SNS -> Lambda activo ({lambda_arn})")

    # 4. Aprovisionar y poblar Tablas DynamoDB invocando Lambda bajo LabRole
    print("\n[4/7] Aprovisionando Tablas Serverless en Amazon DynamoDB vía LabRole ...")
    inv_init = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps({"admin_action": "init_dynamodb"}).encode("utf-8"),
    )
    init_res = json.loads(inv_init["Payload"].read().decode("utf-8"))
    print(f"  -> Tablas DynamoDB listas: {init_res}")

    inv_seed = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps({"admin_action": "seed_data", "s3_bucket": s3_bucket}).encode("utf-8"),
    )
    seed_res = json.loads(inv_seed["Payload"].read().decode("utf-8"))
    print(f"  -> Semilla de datos inicial en DynamoDB y S3 completada: {seed_res}")
    return lambda_arn


def ensure_security_groups(ec2, vpc_id: str):
    print("\n[5/7] Configurando Security Groups en VPC ...")

    def get_or_create_sg(name: str, desc: str):
        existing = ec2.describe_security_groups(
            Filters=[{"Name": "group-name", "Values": [name]}, {"Name": "vpc-id", "Values": [vpc_id]}]
        )["SecurityGroups"]
        if existing:
            return existing[0]["GroupId"]
        resp = ec2.create_security_group(GroupName=name, Description=desc, VpcId=vpc_id)
        return resp["GroupId"]

    alb_sg_id = get_or_create_sg(SG_ALB_NAME, "Security Group para Application Load Balancer de PulseGuard")
    ec2_sg_id = get_or_create_sg(SG_EC2_NAME, "Security Group para Nodos Web EC2 de PulseGuard")

    for sg_id, ports in [(alb_sg_id, [80]), (ec2_sg_id, [80, 22])]:
        for port in ports:
            try:
                ec2.authorize_security_group_ingress(
                    GroupId=sg_id,
                    IpPermissions=[
                        {
                            "IpProtocol": "tcp",
                            "FromPort": port,
                            "ToPort": port,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                )
            except Exception:
                pass

    print(f"  -> Security Group ALB : {alb_sg_id}")
    print(f"  -> Security Group EC2 : {ec2_sg_id}")
    return alb_sg_id, ec2_sg_id


def ensure_alb_and_target_group(elbv2, vpc_id: str, subnet_ids: list, alb_sg_id: str):
    print("\n[6/7] Configurando Application Load Balancer (ALB) y Target Group Multi-AZ ...")
    tgs = elbv2.describe_target_groups()["TargetGroups"]
    tg_arn = next((t["TargetGroupArn"] for t in tgs if t["TargetGroupName"] == TG_NAME), None)

    if not tg_arn:
        tg_resp = elbv2.create_target_group(
            Name=TG_NAME,
            Protocol="HTTP",
            Port=80,
            VpcId=vpc_id,
            TargetType="instance",
            HealthCheckProtocol="HTTP",
            HealthCheckPort="80",
            HealthCheckPath="/api/health",
            HealthCheckIntervalSeconds=10,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=2,
            UnhealthyThresholdCount=2,
        )
        tg_arn = tg_resp["TargetGroups"][0]["TargetGroupArn"]
    else:
        elbv2.modify_target_group(
            TargetGroupArn=tg_arn,
            HealthCheckPath="/api/health",
            HealthCheckIntervalSeconds=10,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=2,
            UnhealthyThresholdCount=2,
        )

    elbv2.modify_target_group_attributes(
        TargetGroupArn=tg_arn,
        Attributes=[{"Key": "deregistration_delay.timeout_seconds", "Value": "15"}],
    )

    lbs = elbv2.describe_load_balancers()["LoadBalancers"]
    alb = next((l for l in lbs if l["LoadBalancerName"] == ALB_NAME), None)

    if not alb:
        alb_resp = elbv2.create_load_balancer(
            Name=ALB_NAME,
            Subnets=subnet_ids[:2],
            SecurityGroups=[alb_sg_id],
            Scheme="internet-facing",
            Type="application",
            IpAddressType="ipv4",
        )
        alb = alb_resp["LoadBalancers"][0]
    alb_arn = alb["LoadBalancerArn"]
    alb_dns = alb["DNSName"]

    listeners = elbv2.describe_listeners(LoadBalancerArn=alb_arn)["Listeners"]
    if not listeners:
        elbv2.create_listener(
            LoadBalancerArn=alb_arn,
            Protocol="HTTP",
            Port=80,
            DefaultActions=[{"Type": "forward", "TargetGroupArn": tg_arn}],
        )

    print(f"  -> Target Group ARN : {tg_arn}")
    print(f"  -> ALB DNS Público  : http://{alb_dns}")
    return alb_arn, alb_dns, tg_arn


def upload_app_bundle_to_s3(s3, bucket_name: str, state_dict: dict):
    """Empaqueta el código de la aplicación y el estado de despliegue y lo sube a S3 para las instancias EC2."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path in [
            "requirements.txt",
            "infra/config.py",
            "app/backend/main.py",
            "app/worker/lambda_function.py",
            "app/frontend/index.html",
        ]:
            full_path = PROJECT_ROOT / rel_path
            if full_path.exists():
                zf.write(full_path, arcname=rel_path)
        zf.writestr("infra/.deployment_state.json", json.dumps(state_dict, indent=2))

    s3.put_object(
        Bucket=bucket_name,
        Key="artifacts/app_bundle.zip",
        Body=buf.getvalue(),
        ContentType="application/zip",
    )


def ensure_ec2_cluster(ec2, ssm, elbv2, s3_bucket: str, subnet_ids: list, ec2_sg_id: str, tg_arn: str):
    print("\n[7/7] Desplegando Clúster de 2 Instancias Amazon EC2 (Multi-AZ) con Bootstrap Automatizado ...")

    ami_id = ssm.get_parameter(
        Name="/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
    )["Parameter"]["Value"]
    print(f"  -> AMI Amazon Linux 2023 detectada: {ami_id}")

    user_data_script = f"""#!/bin/bash
set -e
dnf install -y python3-pip unzip
mkdir -p /opt/pulseguard
aws s3 cp s3://{s3_bucket}/artifacts/app_bundle.zip /opt/pulseguard/app_bundle.zip --region {AWS_REGION}
cd /opt/pulseguard
unzip -o app_bundle.zip
pip3 install --ignore-installed -r requirements.txt

cat << 'EOF' > /etc/systemd/system/pulseguard.service
[Unit]
Description=PulseGuard Cloud FastAPI Web Application
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/pulseguard
Environment="AWS_REGION={AWS_REGION}"
Environment="S3_LOGS_BUCKET={s3_bucket}"
Environment="ALB_TARGET_GROUP_ARN={tg_arn}"
ExecStart=/usr/bin/python3 -m uvicorn app.backend.main:app --host 0.0.0.0 --port 80
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pulseguard
systemctl restart pulseguard
"""

    reservations = ec2.describe_instances(
        Filters=[
            {"Name": "tag:Project", "Values": [PROJECT_PREFIX]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
        ]
    )["Reservations"]

    existing_instances = [inst for r in reservations for inst in r["Instances"]]

    stopped_ids = [i["InstanceId"] for i in existing_instances if i["State"]["Name"] == "stopped"]
    if stopped_ids:
        print(f"  -> Reactivando instancias EC2 detenidas por el laboratorio: {stopped_ids}")
        ec2.start_instances(InstanceIds=stopped_ids)

    active_ids = [i["InstanceId"] for i in existing_instances]
    needed = max(0, 2 - len(active_ids))

    if needed > 0:
        for idx in range(needed):
            subnet_id = subnet_ids[idx % len(subnet_ids)]
            node_label = f"{PROJECT_PREFIX}-node-{len(active_ids) + 1}"
            print(f"  -> Lanzando instancia EC2 ({node_label}) en subred {subnet_id} (EBS gp2) ...")
            run_resp = ec2.run_instances(
                ImageId=ami_id,
                InstanceType="t3.micro",
                MinCount=1,
                MaxCount=1,
                SubnetId=subnet_id,
                SecurityGroupIds=[ec2_sg_id],
                IamInstanceProfile={"Name": "LabInstanceProfile"},
                BlockDeviceMappings=[
                    {
                        "DeviceName": "/dev/xvda",
                        "Ebs": {
                            "VolumeSize": 8,
                            "VolumeType": "gp2",
                            "DeleteOnTermination": True,
                        },
                    }
                ],
                UserData=user_data_script,
                TagSpecifications=[
                    {
                        "ResourceType": "instance",
                        "Tags": [
                            {"Key": "Name", "Value": node_label},
                            {"Key": "Project", "Value": PROJECT_PREFIX},
                        ],
                    }
                ],
            )
            new_id = run_resp["Instances"][0]["InstanceId"]
            active_ids.append(new_id)

    print(f"  -> Esperando a que las instancias EC2 estén en estado 'running': {active_ids} ...")
    waiter = ec2.get_waiter("instance_running")
    waiter.wait(InstanceIds=active_ids)

    # Sincronizar y levantar el servicio pulseguard vía AWS Systems Manager (SSM) en ambos nodos
    try:
        print("  -> Sincronizando código y servicio systemd en instancias EC2 vía AWS SSM ...")
        ssm_cmd = ssm.send_command(
            InstanceIds=active_ids,
            DocumentName="AWS-RunShellScript",
            Parameters={"commands": [user_data_script]},
        )
        cmd_id = ssm_cmd["Command"]["CommandId"]
        for _ in range(15):
            time.sleep(3)
            statuses = [
                ssm.get_command_invocation(CommandId=cmd_id, InstanceId=iid)["Status"]
                for iid in active_ids
            ]
            if all(st in ("Success", "Failed", "Cancelled") for st in statuses):
                print(f"  -> Estado de sincronización SSM en nodos EC2: {statuses}")
                break
    except Exception as e:
        print(f"  -> Nota SSM (el bootstrap continúa vía UserData): {e}")

    elbv2.register_targets(
        TargetGroupArn=tg_arn,
        Targets=[{"Id": iid, "Port": 80} for iid in active_ids],
    )
    print(f"  -> Instancias registradas en el Load Balancer Target Group: {active_ids}")
    return active_ids


def main():
    print("=" * 75)
    print(" PULSEGUARD CLOUD - DESPLIEGUE AUTOMATIZADO DE INFRAESTRUCTURA AWS (BOTO3)")
    print("=" * 75)

    session = get_boto3_session()
    sts = session.client("sts")
    account_id = sts.get_caller_identity()["Account"]
    lab_role_arn = f"arn:aws:iam::{account_id}:role/LabRole"

    s3 = session.client("s3")
    sns = session.client("sns")
    lambda_client = session.client("lambda")
    ec2 = session.client("ec2")
    elbv2 = session.client("elbv2")
    ssm = session.client("ssm")

    s3_bucket = f"{PROJECT_PREFIX}-logs-{account_id}"

    # 1. S3
    ensure_s3_bucket(s3, s3_bucket)

    # 2. SNS (Bus de telemetría + Alertas)
    sns_telemetry_arn, sns_alerts_arn = ensure_sns_topics(sns)

    # 3 y 4. Lambda + Tablas DynamoDB + Seed Inicial
    lambda_arn = ensure_lambda_and_dynamodb(
        lambda_client, sns, lab_role_arn, s3_bucket, sns_telemetry_arn, sns_alerts_arn
    )

    # 5. VPC y Security Groups
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"]
    if not vpcs:
        vpcs = ec2.describe_vpcs()["Vpcs"]
    vpc_id = vpcs[0]["VpcId"]

    subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["Subnets"]
    subnets_by_az = {}
    for s in subnets:
        az = s["AvailabilityZone"]
        if az in ("us-east-1a", "us-east-1b", "us-east-1c", "us-east-1d") and az not in subnets_by_az:
            subnets_by_az[az] = s["SubnetId"]
    selected_subnets = [subnets_by_az[k] for k in sorted(subnets_by_az.keys())][:2]

    alb_sg_id, ec2_sg_id = ensure_security_groups(ec2, vpc_id)

    # 6. ALB y Target Group
    alb_arn, alb_dns, tg_arn = ensure_alb_and_target_group(elbv2, vpc_id, selected_subnets, alb_sg_id)

    state_data = {
        "account_id": account_id,
        "region": AWS_REGION,
        "s3_bucket": s3_bucket,
        "sns_telemetry_topic_arn": sns_telemetry_arn,
        "sns_topic_arn": sns_alerts_arn,
        "s3_dlq_prefix": f"s3://{s3_bucket}/dlq/",
        "lambda_function_name": LAMBDA_FUNCTION_NAME,
        "lambda_arn": lambda_arn,
        "alb_arn": alb_arn,
        "alb_dns": alb_dns,
        "alb_url": f"http://{alb_dns}",
        "target_group_arn": tg_arn,
        "alb_sg_id": alb_sg_id,
        "ec2_sg_id": ec2_sg_id,
    }
    STATE_FILE.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
    upload_app_bundle_to_s3(s3, s3_bucket, state_data)

    # 7. Clúster EC2
    instance_ids = ensure_ec2_cluster(ec2, ssm, elbv2, s3_bucket, selected_subnets, ec2_sg_id, tg_arn)
    state_data["ec2_instance_ids"] = instance_ids
    STATE_FILE.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
    upload_app_bundle_to_s3(s3, s3_bucket, state_data)

    print("\n" + "=" * 75)
    print(" DESPLIEGUE COMPLETADO CON ÉXITO")
    print("=" * 75)
    print(f" URL Pública del Application Load Balancer : http://{alb_dns}")
    print(f" Instancias EC2 en Clúster Multi-AZ        : {', '.join(instance_ids)}")
    print(f" Bucket Amazon S3 (Logs + DLQ)             : {s3_bucket}")
    print(f" Tablas Amazon DynamoDB                    : {DDB_SERVICES_TABLE}, {DDB_INCIDENTS_TABLE}, {DDB_METRICS_TABLE}")
    print(f" Bus Asíncrono Amazon SNS -> AWS Lambda    : {sns_telemetry_arn}")
    print(f" Tópico de Alertas Amazon SNS              : {sns_alerts_arn}")
    print("=" * 75)


if __name__ == "__main__":
    main()

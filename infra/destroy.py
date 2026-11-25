"""
Script de Limpieza y Destrucción de Infraestructura AWS (Teardown).
Permite apagar/eliminar todos los recursos creados por PulseGuard Cloud
cuando termina la sesión de trabajo para ahorrar créditos del AWS Academy Learner Lab.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from infra.config import (
    ALB_NAME,
    DDB_INCIDENTS_TABLE,
    DDB_METRICS_TABLE,
    DDB_SERVICES_TABLE,
    LAMBDA_FUNCTION_NAME,
    PROJECT_PREFIX,
    SG_ALB_NAME,
    SG_EC2_NAME,
    SNS_TOPIC_NAME,
    SQS_DLQ_NAME,
    SQS_MAIN_QUEUE_NAME,
    STATE_FILE,
    TG_NAME,
    get_boto3_session,
)


def main():
    print("=" * 70)
    print(" PULSEGUARD CLOUD - DESTRUCCIÓN DE RECURSOS AWS (TEARDOWN)")
    print("=" * 70)

    session = get_boto3_session()
    ec2 = session.client("ec2")
    elbv2 = session.client("elbv2")
    lambda_client = session.client("lambda")
    sqs = session.client("sqs")
    sns = session.client("sns")
    ddb = session.client("dynamodb")

    # 1. Eliminar ALB y Target Group
    print("[1/5] Eliminando Application Load Balancer y Target Group ...")
    for lb in elbv2.describe_load_balancers()["LoadBalancers"]:
        if lb["LoadBalancerName"] == ALB_NAME:
            for lst in elbv2.describe_listeners(LoadBalancerArn=lb["LoadBalancerArn"])["Listeners"]:
                elbv2.delete_listener(ListenerArn=lst["ListenerArn"])
            elbv2.delete_load_balancer(LoadBalancerArn=lb["LoadBalancerArn"])
            print(f"  -> ALB eliminado: {ALB_NAME}")
            time.sleep(5)

    for tg in elbv2.describe_target_groups()["TargetGroups"]:
        if tg["TargetGroupName"] == TG_NAME:
            try:
                elbv2.delete_target_group(TargetGroupArn=tg["TargetGroupArn"])
                print(f"  -> Target Group eliminado: {TG_NAME}")
            except Exception as e:
                print(f"  -> Aviso al borrar Target Group: {e}")

    # 2. Terminar instancias EC2 del proyecto
    print("[2/5] Terminando instancias Amazon EC2 del proyecto ...")
    reservations = ec2.describe_instances(
        Filters=[
            {"Name": "tag:Project", "Values": [PROJECT_PREFIX]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
        ]
    )["Reservations"]
    inst_ids = [i["InstanceId"] for r in reservations for i in r["Instances"]]
    if inst_ids:
        ec2.terminate_instances(InstanceIds=inst_ids)
        print(f"  -> Instancias terminadas: {inst_ids}")

    # 3. Eliminar Lambda y Event Source Mappings
    print("[3/5] Eliminando función AWS Lambda y triggers ...")
    try:
        mappings = lambda_client.list_event_source_mappings(FunctionName=LAMBDA_FUNCTION_NAME).get(
            "EventSourceMappings", []
        )
        for m in mappings:
            lambda_client.delete_event_source_mapping(UUID=m["UUID"])
        lambda_client.delete_function(FunctionName=LAMBDA_FUNCTION_NAME)
        print(f"  -> Lambda eliminada: {LAMBDA_FUNCTION_NAME}")
    except Exception:
        pass

    # 4. Eliminar Colas SQS
    print("[4/5] Eliminando colas Amazon SQS ...")
    for q_name in (SQS_MAIN_QUEUE_NAME, SQS_DLQ_NAME):
        try:
            q_url = sqs.get_queue_url(QueueName=q_name)["QueueUrl"]
            sqs.delete_queue(QueueUrl=q_url)
            print(f"  -> Cola SQS eliminada: {q_name}")
        except Exception:
            pass

    # 5. Eliminar Tópico SNS
    print("[5/5] Eliminando tópico Amazon SNS ...")
    try:
        for t in sns.list_topics().get("Topics", []):
            if t["TopicArn"].endswith(f":{SNS_TOPIC_NAME}"):
                sns.delete_topic(TopicArn=t["TopicArn"])
                print(f"  -> Tópico SNS eliminado: {t['TopicArn']}")
    except Exception:
        pass

    if STATE_FILE.exists():
        STATE_FILE.unlink()

    print("=" * 70)
    print(" LIMPIEZA COMPLETADA (S3 y DynamoDB conservan datos sin costo por hora).")
    print("=" * 70)


if __name__ == "__main__":
    main()

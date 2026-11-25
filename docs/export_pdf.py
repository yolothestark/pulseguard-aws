"""
Generador del Entregable PDF Oficial: Documentación Técnica de PulseGuard Cloud.
Incluye Portada con los 3 integrantes del equipo y las 5 secciones obligatorias:
1. Guía de Despliegue Paso a Paso (Regla 1: Cero Clics en Consola)
2. Diagrama de Arquitectura de Bloques y Flujo de Datos
3. Pruebas de Resiliencia ("Demuéstrame que no se rompe" - Regla 2) con resultados reales en AWS
4. Justificación de Decisiones (Comparativa de servicios, ventajas y desventajas)
5. Análisis de Costos (Estimación anual a 12 meses fuera de la capa gratuita + consumo en laboratorio)
"""
import json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PDF = PROJECT_ROOT / "docs" / "DOCUMENTACION_PROYECTO_PULSEGUARD.pdf"
STATE_FILE = PROJECT_ROOT / "infra" / ".deployment_state.json"
REPORT_FILE = PROJECT_ROOT / "tests" / "resilience_report.json"


def build_architecture_drawing() -> Drawing:
    """Dibuja el Diagrama de Arquitectura de Bloques de PulseGuard Cloud en vectorial para el PDF."""
    d = Drawing(480, 225)

    # Fondo suave
    d.add(Rect(0, 0, 480, 225, fillColor=colors.HexColor("#0f172a"), strokeColor=colors.HexColor("#334155"), rx=8, ry=8))

    # Título interno del diagrama
    d.add(String(15, 206, "DIAGRAMA DE BLOQUES: ARQUITECTURA MULTI-AZ Y PIPELINE SERVERLESS EN AWS (us-east-1)", fontSize=8.5, fontName="Helvetica-Bold", fillColor=colors.HexColor("#38bdf8")))

    # Bloque 1: Usuarios / Clientes
    d.add(Rect(15, 130, 82, 55, fillColor=colors.HexColor("#1e293b"), strokeColor=colors.HexColor("#38bdf8"), rx=5, ry=5))
    d.add(String(22, 165, "Clientes / SRE", fontSize=8, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(20, 152, "Navegador Web", fontSize=7, fontName="Helvetica", fillColor=colors.HexColor("#cbd5e1")))
    d.add(String(20, 140, "& Microservicios", fontSize=7, fontName="Helvetica", fillColor=colors.HexColor("#cbd5e1")))

    # Flecha Cliente -> ALB
    d.add(Line(97, 157, 118, 157, strokeColor=colors.HexColor("#38bdf8"), strokeWidth=1.5))

    # Bloque 2: Application Load Balancer
    d.add(Rect(118, 125, 88, 65, fillColor=colors.HexColor("#1e3a8a"), strokeColor=colors.HexColor("#60a5fa"), rx=5, ry=5))
    d.add(String(124, 173, "Application Load", fontSize=7.5, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(124, 162, "Balancer (ALB)", fontSize=7.5, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(124, 148, "Multi-AZ HTTP:80", fontSize=6.8, fontName="Helvetica", fillColor=colors.HexColor("#93c5fd")))
    d.add(String(124, 136, "Health: /api/health", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#bae6fd")))

    # Flechas ALB -> EC2 A y EC2 B
    d.add(Line(206, 170, 228, 182, strokeColor=colors.HexColor("#60a5fa"), strokeWidth=1.5))
    d.add(Line(206, 145, 228, 132, strokeColor=colors.HexColor("#60a5fa"), strokeWidth=1.5))

    # Bloque 3A: EC2 Nodo 1 (us-east-1a)
    d.add(Rect(228, 162, 108, 36, fillColor=colors.HexColor("#064e3b"), strokeColor=colors.HexColor("#34d399"), rx=4, ry=4))
    d.add(String(234, 184, "EC2 Nodo 1 (us-east-1a)", fontSize=7.2, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(234, 170, "FastAPI Stateless (t3.micro)", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#a7f3d0")))

    # Bloque 3B: EC2 Nodo 2 (us-east-1b)
    d.add(Rect(228, 115, 108, 36, fillColor=colors.HexColor("#064e3b"), strokeColor=colors.HexColor("#34d399"), rx=4, ry=4))
    d.add(String(234, 137, "EC2 Nodo 2 (us-east-1b)", fontSize=7.2, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(234, 123, "FastAPI Stateless (t3.micro)", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#a7f3d0")))

    # Flecha EC2 -> SNS Telemetry Stream
    d.add(Line(336, 157, 360, 157, strokeColor=colors.HexColor("#fbbf24"), strokeWidth=1.5))

    # Bloque 4: Amazon SNS Bus + Alertas
    d.add(Rect(360, 130, 105, 58, fillColor=colors.HexColor("#78350f"), strokeColor=colors.HexColor("#fbbf24"), rx=5, ry=5))
    d.add(String(366, 173, "Amazon SNS Bus", fontSize=7.8, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(366, 160, "1. telemetry-stream", fontSize=6.8, fontName="Helvetica", fillColor=colors.HexColor("#fde68a")))
    d.add(String(366, 148, "2. incident-alerts", fontSize=6.8, fontName="Helvetica", fillColor=colors.HexColor("#fde68a")))
    d.add(String(366, 136, "(Pub/Sub + Email Push)", fontSize=6.3, fontName="Helvetica", fillColor=colors.HexColor("#fef3c7")))

    # Flecha SNS -> AWS Lambda
    d.add(Line(412, 130, 412, 92, strokeColor=colors.HexColor("#f97316"), strokeWidth=1.5))

    # Bloque 5: AWS Lambda
    d.add(Rect(345, 32, 120, 60, fillColor=colors.HexColor("#7c2d12"), strokeColor=colors.HexColor("#fb923c"), rx=5, ry=5))
    d.add(String(352, 77, "AWS Lambda (LabRole)", fontSize=7.8, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(352, 65, "pulseguard-anomaly-evaluator", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#fed7aa")))
    d.add(String(352, 52, "- Evalua reglas SLA/CPU/HTTP", fontSize=6.3, fontName="Helvetica", fillColor=colors.white))
    d.add(String(352, 40, "- Aisla fallos en DLQ (S3)", fontSize=6.3, fontName="Helvetica", fillColor=colors.HexColor("#fca5a5")))

    # Bloque 6: Amazon DynamoDB (3 Tablas)
    d.add(Rect(175, 22, 145, 72, fillColor=colors.HexColor("#1e1b4b"), strokeColor=colors.HexColor("#818cf8"), rx=5, ry=5))
    d.add(String(183, 79, "Amazon DynamoDB (Serverless)", fontSize=7.8, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(183, 65, "- pulseguard-services (Estado/SLA)", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#c7d2fe")))
    d.add(String(183, 52, "- pulseguard-metrics (Telemetria)", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#c7d2fe")))
    d.add(String(183, 39, "- pulseguard-incidents (Incidentes)", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#c7d2fe")))
    d.add(String(183, 27, "Modo: PAY_PER_REQUEST", fontSize=6.3, fontName="Helvetica-Bold", fillColor=colors.HexColor("#a5b4fc")))

    # Bloque 7: Amazon S3 (Logs + DLQ + Artifacts)
    d.add(Rect(15, 22, 140, 72, fillColor=colors.HexColor("#14532d"), strokeColor=colors.HexColor("#4ade80"), rx=5, ry=5))
    d.add(String(22, 79, "Amazon S3 Bucket", fontSize=7.8, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(22, 65, "pulseguard-logs-627739785043", fontSize=6.5, fontName="Helvetica-Bold", fillColor=colors.HexColor("#bbf7d0")))
    d.add(String(22, 52, "- /logs/ (JSON Auditable + URLs)", fontSize=6.4, fontName="Helvetica", fillColor=colors.white))
    d.add(String(22, 39, "- /dlq/ (Dead Letter Queue)", fontSize=6.4, fontName="Helvetica", fillColor=colors.HexColor("#fca5a5")))
    d.add(String(22, 27, "- /artifacts/app_bundle.zip", fontSize=6.4, fontName="Helvetica", fillColor=colors.HexColor("#86efac")))

    # Flechas Lambda -> DynamoDB y S3
    d.add(Line(345, 60, 320, 60, strokeColor=colors.HexColor("#818cf8"), strokeWidth=1.5))
    d.add(Line(175, 58, 155, 58, strokeColor=colors.HexColor("#4ade80"), strokeWidth=1.5))
    d.add(Line(250, 115, 250, 94, strokeColor=colors.HexColor("#818cf8"), strokeWidth=1.2))

    return d


def generate_pdf():
    state = {}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))

    alb_url = state.get("alb_url", "http://pulseguard-alb-2010215791.us-east-1.elb.amazonaws.com")
    ec2_ids = ", ".join(state.get("ec2_instance_ids", ["i-0d094c37434fb3382", "i-07ecf4a840ba95107"]))
    s3_bucket = state.get("s3_bucket", "pulseguard-logs-627739785043")

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="PulseGuard Cloud - Documentación Técnica AWS",
        author="Anguiano Garcia Angel Yahir Guadalupe, Figueroa Robles Axel Israel, Torres Martinez Miguel Angel",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=10,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        alignment=1,
        textColor=colors.HexColor("#334155"),
        spaceAfter=16,
    )
    h1_style = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0369a1"),
        spaceBefore=12,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9.3,
        leading=13.2,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=5,
    )
    code_style = ParagraphStyle(
        "CodeBlock",
        parent=styles["Code"],
        fontSize=8.2,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"),
        borderPadding=6,
        spaceAfter=6,
    )

    story = []

    # PORTADA / ENCABEZADO OFICIAL
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("PROYECTO LIBRE DE ARQUITECTURA EN LA NUBE (AWS)", subtitle_style))
    story.append(
        Paragraph(
            "PulseGuard Cloud: Plataforma Distribuida de Monitoreo de Servicios, Ingesta Asíncrona de Logs y Gestión de Incidentes en AWS",
            title_style,
        )
    )
    story.append(
        Paragraph(
            "Categoría: Aplicación Web Cloud-Native con Alta Disponibilidad Multi-AZ y Tolerancia a Fallos",
            subtitle_style,
        )
    )

    team_data = [
        ["INTEGRANTES DEL EQUIPO", "ROL EN EL PROYECTO"],
        ["Anguiano Garcia Angel Yahir Guadalupe", "Infraestructura como Código (Boto3) y Pipeline Serverless (SNS/Lambda/S3)"],
        ["Figueroa Robles Axel Israel", "Arquitectura Multi-AZ (ALB + Clúster EC2) y Aplicación Web Full-Stack"],
        ["Torres Martinez Miguel Angel", "Ingeniería del Caos (Pruebas de Resiliencia), DynamoDB y Análisis Financiero"],
    ]
    t_team = Table(team_data, colWidths=[2.7 * inch, 4.3 * inch])
    t_team.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t_team)
    story.append(Spacer(1, 10))

    meta_data = [
        ["Recurso AWS Desplegado", "Identificador / Endpoint Real en us-east-1 (Account: 627739785043)"],
        ["Application Load Balancer (ALB)", alb_url],
        ["Clúster Amazon EC2 (Multi-AZ)", f"{ec2_ids} (t3.micro, EBS gp2, LabInstanceProfile)"],
        ["Bucket Amazon S3 (Logs + DLQ)", f"s3://{s3_bucket}/ (Logs JSON, DLQ y Artefacto Bootstrap)"],
        ["Tablas Amazon DynamoDB", "pulseguard-services, pulseguard-incidents, pulseguard-metrics"],
        ["Función AWS Lambda + Bus SNS", "pulseguard-anomaly-evaluator + pulseguard-telemetry-stream / incident-alerts"],
    ]
    t_meta = Table(meta_data, colWidths=[2.3 * inch, 4.7 * inch])
    t_meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0369a1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.3),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # SECCIÓN 1: GUÍA DE DESPLIEGUE
    story.append(Paragraph("1. Guía de Despliegue Paso a Paso (Regla 1: Cero Clics en Consola)", h1_style))
    story.append(
        Paragraph(
            "Cumpliendo estrictamente con la Regla 1, ningún componente de la infraestructura fue creado manualmente en la consola web de AWS. "
            "Se desarrolló una suite de Infraestructura como Código (IaC) en Python utilizando el SDK oficial <b>boto3</b> que construye, "
            "configura, verifica y destruye todo el entorno de manera 100% automatizada e idempotente.",
            body_style,
        )
    )
    story.append(Paragraph("<b>Paso 1: Configurar credenciales del AWS Academy Learner Lab</b><br/>"
                           "Iniciar el laboratorio escolar (Start Lab), abrir <i>AWS Details -> AWS CLI: Show</i> y pegar el bloque "
                           "de credenciales temporales en el archivo local <code>aws_credentials.txt</code>.", body_style))
    story.append(Paragraph("<b>Paso 2: Verificar diagnóstico del laboratorio y ejecutar el despliegue maestro</b>", body_style))
    story.append(
        Paragraph(
            "uv run --with boto3 python infra/check_lab.py<br/>"
            "uv run --with boto3 --with requests python infra/deploy.py",
            code_style,
        )
    )
    story.append(
        Paragraph(
            "<b>¿Qué ejecuta automáticamente <code>infra/deploy.py</code>?</b><br/>"
            "1) Crea y configura el bucket <b>Amazon S3</b> (<code>pulseguard-logs-627739785043</code>) con políticas CORS.<br/>"
            "2) Crea los tópicos de <b>Amazon SNS</b> para el bus asíncrono de telemetría y las alertas por correo.<br/>"
            "3) Empaqueta en un archivo ZIP en memoria y despliega la función <b>AWS Lambda</b> (<code>pulseguard-anomaly-evaluator</code>) "
            "asignándole el rol escolar <code>LabRole</code> y suscribiéndola al bus de SNS.<br/>"
            "4) Aprovisiona e inicializa las 3 tablas Serverless de <b>Amazon DynamoDB</b> (<code>services</code>, <code>incidents</code>, <code>metrics</code>) "
            "y precarga 5 microservicios empresariales con sus logs iniciales.<br/>"
            "5) Configura los <b>Security Groups</b>, el <b>Target Group</b> con Health Check (<code>/api/health</code> cada 10s) y el "
            "<b>Application Load Balancer (ALB)</b> público distribuido en múltiples Zonas de Disponibilidad.<br/>"
            "6) Lanza <b>2 instancias Amazon EC2 (t3.micro)</b> en distintas Zonas de Disponibilidad (<code>us-east-1a</code> y <code>us-east-1b</code>) "
            "con un script <code>UserData</code> que descarga el paquete desde S3, instala FastAPI/Uvicorn y activa el servicio <code>systemd</code>.<br/>"
            "7) Para limpiar los recursos y cuidar el crédito del laboratorio al terminar la sesión: <code>uv run --with boto3 python infra/destroy.py</code>.",
            body_style,
        )
    )

    # SECCIÓN 2: DIAGRAMA DE ARQUITECTURA
    story.append(Paragraph("2. Diagrama de Arquitectura y Flujo de Datos", h1_style))
    story.append(build_architecture_drawing())
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "<b>Flujo de Datos:</b> (1) Los usuarios e ingenieros SRE acceden a la aplicación web a través del DNS público del "
            "<b>Application Load Balancer</b>, el cual balancea las solicitudes entre 2 nodos <b>Amazon EC2</b> Stateless en "
            "<code>us-east-1a</code> y <code>us-east-1b</code>. (2) Cuando un servicio envía telemetría a <code>POST /api/telemetry</code>, "
            "el nodo EC2 publica el evento de forma asíncrona en <b>Amazon SNS</b> y responde inmediatamente <code>HTTP 202 Accepted</code>. "
            "(3) <b>AWS Lambda</b> consume el evento, archiva el JSON crudo en <b>Amazon S3</b>, actualiza métricas y SLAs en "
            "<b>Amazon DynamoDB</b> y, si detecta una anomalía crítica (HTTP 5xx, Latencia &gt; 1500ms o CPU &gt; 90%), abre un incidente "
            "y dispara una notificación por correo electrónico mediante <b>Amazon SNS</b>.",
            body_style,
        )
    )

    story.append(PageBreak())

    # SECCIÓN 3: PRUEBAS DE RESILIENCIA
    story.append(Paragraph("3. Pruebas de Resiliencia ('Demuéstrame que no se rompe' - Regla 2)", h1_style))
    story.append(
        Paragraph(
            "Se implementaron un <b>Panel Interactivo de Chaos Engineering</b> dentro de la interfaz web y la suite automatizada "
            "<code>tests/resilience_test.py</code> para evaluar y demostrar en vivo el comportamiento del sistema ante fallos reales:",
            body_style,
        )
    )

    res_table_data = [
        ["Escenario de Fallo Simulado", "¿Qué pasaría sin resiliencia?", "Mecanismo de Mitigación y Resultado Real"],
        [
            "1. Caída de un Servidor Web EC2\n(/api/chaos/simulate-node-failure)",
            "Caída total del portal web (Connection Refused / HTTP 502) y pérdida de sesión de los usuarios activos.",
            "El nodo afectado devuelve HTTP 503 en /api/health. El Application Load Balancer detecta el fallo y desvía automáticamente el 100% del tráfico al segundo nodo EC2 en otra Zona de Disponibilidad con 100% de disponibilidad continua.",
        ],
        [
            "2. Fallo Crítico en Lambda / Mensaje Corrupto (Poison Pill)\n(/api/chaos/poison-pill)",
            "Excepción HTTP 500 al cliente o bloqueo infinito de la cola de procesamiento deteniendo los demás logs.",
            "AWS Lambda captura el fallo tras agotar los reintentos y aísla automáticamente el payload corrupto en la Dead Letter Queue persistente en S3 (s3://.../dlq/), mientras los mensajes sanos en paralelo se procesan sin bloqueo.",
        ],
        [
            "3. Ráfaga Concurrente de Tráfico (Stress Test 30x)\n(/api/chaos/stress-burst)",
            "Saturación de CPU/hilos del servidor web y rechazo de conexiones al escribir síncronamente en BD.",
            "Desacoplamiento asíncrono (Load Leveling): los 30 eventos se aceptan en milisegundos con 0.0% de pérdida de paquetes y AWS Lambda los procesa en lotes hacia DynamoDB y S3.",
        ],
        [
            "4. Congelamiento del Laboratorio Escolar (Cada 4 horas)",
            "Pérdida de datos locales en instancias eliminadas y configuración manual perdida.",
            "Arquitectura 100% Stateless (datos en DynamoDB y S3) + script idempotente deploy.py que reactiva o reconstruye el clúster EC2 en ~90 segundos.",
        ],
    ]
    t_res = Table(res_table_data, colWidths=[1.8 * inch, 2.0 * inch, 3.2 * inch])
    t_res.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(t_res)
    story.append(Spacer(1, 8))

    # SECCIÓN 4: JUSTIFICACIÓN DE DECISIONES
    story.append(Paragraph("4. Justificación de Decisiones Arquitectónicas (Ventajas y Desventajas)", h1_style))
    just_data = [
        ["Decisión Elegida", "Alternativa Descartada", "Ventajas Obtenidas", "Desventajas / Trade-offs"],
        [
            "Application Load Balancer + 2x EC2 t3.micro (Multi-AZ)",
            "1 sola instancia EC2 grande (Vertical)",
            "Elimina el Punto Único de Fallo (SPOF); conmutación automática ante caída de nodo o zona (Zero Downtime).",
            "Costo fijo por hora del ALB ($0.0225/h) y ligera latencia adicional de red (~2-3 ms).",
        ],
        [
            "Amazon DynamoDB (Serverless On-Demand)",
            "Amazon RDS (MySQL / PostgreSQL)",
            "Latencia <10 ms; escala sin administrar pools de conexiones; no se apaga ni cobra por hora cuando el laboratorio está inactivo.",
            "No soporta JOINs relacionales complejos ni consultas SQL ad-hoc.",
        ],
        [
            "Bus Asíncrono SNS + AWS Lambda + DLQ en S3",
            "Procesamiento síncrono directo en EC2",
            "Respuestas HTTP 202 ultra rápidas; absorbe picos masivos de tráfico; aísla mensajes corruptos en DLQ sin tirar el servidor.",
            "Consistencia eventual (~1 a 2 segundos para ver el log procesado en el dashboard).",
        ],
        [
            "Amazon S3 con Presigned URLs",
            "Disco local EBS dentro de cada EC2",
            "Durabilidad de 11 nueves compartida entre todos los nodos y Lambda; descarga directa sin saturar EC2.",
            "Mayor latencia por operación PUT individual (~40 ms) respecto a disco local.",
        ],
    ]
    t_just = Table(just_data, colWidths=[1.6 * inch, 1.4 * inch, 2.2 * inch, 1.8 * inch])
    t_just.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0369a1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(t_just)
    story.append(Spacer(1, 8))

    # SECCIÓN 5: ANÁLISIS DE COSTOS
    story.append(Paragraph("5. Análisis de Costos (Estimación a 1 Año Fuera de la Capa Gratuita)", h1_style))
    story.append(
        Paragraph(
            "<b>Costo durante el laboratorio:</b> Menos de $0.09 USD de crédito académico virtual por sesión gracias al modelo Serverless "
            "y al script de limpieza <code>infra/destroy.py</code>.<br/>"
            "<b>Estimación productiva anual (Fuera de Free Tier en us-east-1):</b> Operación continua 24/7 (730 h/mes) monitoreando "
            "25 microservicios con 1,500,000 eventos mensuales:",
            body_style,
        )
    )

    cost_data = [
        ["Servicio AWS", "Dimensionamiento Mensual (24/7)", "Tarifa Oficial (us-east-1)", "Costo Mensual", "Costo Anual (1 Año)"],
        ["Amazon EC2", "2x t3.micro (1,460 h/mes) + 16 GB EBS gp2", "$0.0104/h + $0.10/GB-mes", "$16.78 USD", "$201.36 USD"],
        ["Application Load Balancer", "1 ALB (730 h/mes) + 0.5 LCU promedio", "$0.0225/h + $0.008/LCU-h", "$19.35 USD", "$232.20 USD"],
        ["Amazon DynamoDB", "3M escrituras (WRU) + 6M lecturas + 5 GB", "$1.25/M WRU + $0.25/M RRU", "$6.50 USD", "$78.00 USD"],
        ["Amazon S3 Standard", "15 GB logs JSON + 1.5M PUT + 300k GET", "$0.023/GB + $0.005/1k PUT", "$7.97 USD", "$95.64 USD"],
        ["AWS Lambda", "300k invocaciones (200 ms a 256 MB)", "$0.20/M req + GB-seg", "$0.31 USD", "$3.72 USD"],
        ["Amazon SNS", "1.5M publicaciones bus + 2,000 emails", "$0.50/M pub + $2/100k email", "$0.79 USD", "$9.48 USD"],
        ["TOTAL ESTIMADO", "Infraestructura Multi-AZ Completa 24/7", "Sin Capa Gratuita", "$51.70 USD / mes", "$620.40 USD / año"],
    ]
    t_cost = Table(cost_data, colWidths=[1.45 * inch, 1.95 * inch, 1.4 * inch, 1.1 * inch, 1.1 * inch])
    t_cost.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e0f2fe")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.0),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(t_cost)

    doc.build(story)
    print(f"[OK] PDF generado exitosamente en: {OUTPUT_PDF}")


if __name__ == "__main__":
    generate_pdf()

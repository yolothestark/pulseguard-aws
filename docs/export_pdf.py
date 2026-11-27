"""
Generador del Entregable PDF Oficial: Documentación Técnica de PulseGuard Cloud.
Todas las celdas de las tablas utilizan objetos Paragraph de ReportLab para garantizar
ajuste automático de línea (word-wrap) perfecto y cero texto amontonado.
"""
import json
from pathlib import Path
from reportlab.graphics.shapes import Drawing, Line, Rect, String
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PDF = PROJECT_ROOT / "docs" / "DOCUMENTACION_PROYECTO_PULSEGUARD.pdf"
STATE_FILE = PROJECT_ROOT / "infra" / ".deployment_state.json"


def build_architecture_drawing() -> Drawing:
    """Dibuja el Diagrama de Arquitectura de Bloques de PulseGuard Cloud en vectorial para el PDF."""
    d = Drawing(500, 215)

    # Fondo oscuro elegante
    d.add(Rect(0, 0, 500, 215, fillColor=colors.HexColor("#0f172a"), strokeColor=colors.HexColor("#334155"), rx=8, ry=8))

    # Título interno del diagrama
    d.add(
        String(
            15,
            196,
            "DIAGRAMA DE BLOQUES: ARQUITECTURA MULTI-AZ Y PIPELINE SERVERLESS EN AWS (us-east-1)",
            fontSize=8.5,
            fontName="Helvetica-Bold",
            fillColor=colors.HexColor("#38bdf8"),
        )
    )

    # Bloque 1: Usuarios / Clientes
    d.add(Rect(14, 122, 85, 55, fillColor=colors.HexColor("#1e293b"), strokeColor=colors.HexColor("#38bdf8"), rx=5, ry=5))
    d.add(String(20, 158, "Clientes / SRE", fontSize=8, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(20, 145, "Navegador Web", fontSize=7, fontName="Helvetica", fillColor=colors.HexColor("#cbd5e1")))
    d.add(String(20, 133, "& Microservicios", fontSize=7, fontName="Helvetica", fillColor=colors.HexColor("#cbd5e1")))

    # Flecha Cliente -> ALB
    d.add(Line(99, 149, 120, 149, strokeColor=colors.HexColor("#38bdf8"), strokeWidth=1.5))

    # Bloque 2: Application Load Balancer
    d.add(Rect(120, 118, 92, 63, fillColor=colors.HexColor("#1e3a8a"), strokeColor=colors.HexColor("#60a5fa"), rx=5, ry=5))
    d.add(String(126, 165, "Application Load", fontSize=7.5, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(126, 154, "Balancer (ALB)", fontSize=7.5, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(126, 140, "Multi-AZ HTTP:80", fontSize=6.8, fontName="Helvetica", fillColor=colors.HexColor("#93c5fd")))
    d.add(String(126, 128, "Health: /api/health", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#bae6fd")))

    # Flechas ALB -> EC2 A y EC2 B
    d.add(Line(212, 162, 235, 174, strokeColor=colors.HexColor("#60a5fa"), strokeWidth=1.5))
    d.add(Line(212, 136, 235, 124, strokeColor=colors.HexColor("#60a5fa"), strokeWidth=1.5))

    # Bloque 3A: EC2 Nodo 1 (us-east-1a)
    d.add(Rect(235, 154, 112, 34, fillColor=colors.HexColor("#064e3b"), strokeColor=colors.HexColor("#34d399"), rx=4, ry=4))
    d.add(String(241, 174, "EC2 Nodo 1 (us-east-1a)", fontSize=7.2, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(241, 161, "FastAPI Stateless (t3.micro)", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#a7f3d0")))

    # Bloque 3B: EC2 Nodo 2 (us-east-1b)
    d.add(Rect(235, 108, 112, 34, fillColor=colors.HexColor("#064e3b"), strokeColor=colors.HexColor("#34d399"), rx=4, ry=4))
    d.add(String(241, 128, "EC2 Nodo 2 (us-east-1b)", fontSize=7.2, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(241, 115, "FastAPI Stateless (t3.micro)", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#a7f3d0")))

    # Flecha EC2 -> SNS Telemetry Stream
    d.add(Line(347, 149, 372, 149, strokeColor=colors.HexColor("#fbbf24"), strokeWidth=1.5))

    # Bloque 4: Amazon SNS Bus + Alertas
    d.add(Rect(372, 122, 114, 58, fillColor=colors.HexColor("#78350f"), strokeColor=colors.HexColor("#fbbf24"), rx=5, ry=5))
    d.add(String(378, 165, "Amazon SNS Bus", fontSize=7.8, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(378, 152, "1. telemetry-stream", fontSize=6.8, fontName="Helvetica", fillColor=colors.HexColor("#fde68a")))
    d.add(String(378, 140, "2. incident-alerts", fontSize=6.8, fontName="Helvetica", fillColor=colors.HexColor("#fde68a")))
    d.add(String(378, 128, "(Pub/Sub + Email Push)", fontSize=6.3, fontName="Helvetica", fillColor=colors.HexColor("#fef3c7")))

    # Flecha SNS -> AWS Lambda
    d.add(Line(428, 122, 428, 86, strokeColor=colors.HexColor("#f97316"), strokeWidth=1.5))

    # Bloque 5: AWS Lambda
    d.add(Rect(356, 26, 130, 60, fillColor=colors.HexColor("#7c2d12"), strokeColor=colors.HexColor("#fb923c"), rx=5, ry=5))
    d.add(String(363, 71, "AWS Lambda (LabRole)", fontSize=7.8, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(363, 59, "pulseguard-anomaly-evaluator", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#fed7aa")))
    d.add(String(363, 46, "- Evalua reglas SLA/CPU/HTTP", fontSize=6.3, fontName="Helvetica", fillColor=colors.white))
    d.add(String(363, 34, "- Aisla fallos en DLQ (S3)", fontSize=6.3, fontName="Helvetica", fillColor=colors.HexColor("#fca5a5")))

    # Bloque 6: Amazon DynamoDB (3 Tablas)
    d.add(Rect(182, 18, 152, 70, fillColor=colors.HexColor("#1e1b4b"), strokeColor=colors.HexColor("#818cf8"), rx=5, ry=5))
    d.add(String(190, 74, "Amazon DynamoDB (Serverless)", fontSize=7.8, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(190, 60, "- pulseguard-services (Estado/SLA)", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#c7d2fe")))
    d.add(String(190, 48, "- pulseguard-metrics (Telemetria)", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#c7d2fe")))
    d.add(String(190, 36, "- pulseguard-incidents (Incidentes)", fontSize=6.5, fontName="Helvetica", fillColor=colors.HexColor("#c7d2fe")))
    d.add(String(190, 24, "Modo: PAY_PER_REQUEST", fontSize=6.3, fontName="Helvetica-Bold", fillColor=colors.HexColor("#a5b4fc")))

    # Bloque 7: Amazon S3 (Logs + DLQ + Artifacts)
    d.add(Rect(14, 18, 146, 70, fillColor=colors.HexColor("#14532d"), strokeColor=colors.HexColor("#4ade80"), rx=5, ry=5))
    d.add(String(21, 74, "Amazon S3 Bucket", fontSize=7.8, fontName="Helvetica-Bold", fillColor=colors.white))
    d.add(String(21, 60, "pulseguard-logs-627739785043", fontSize=6.5, fontName="Helvetica-Bold", fillColor=colors.HexColor("#bbf7d0")))
    d.add(String(21, 48, "- /logs/ (JSON Auditable + URLs)", fontSize=6.4, fontName="Helvetica", fillColor=colors.white))
    d.add(String(21, 36, "- /dlq/ (Dead Letter Queue)", fontSize=6.4, fontName="Helvetica", fillColor=colors.HexColor("#fca5a5")))
    d.add(String(21, 24, "- /artifacts/app_bundle.zip", fontSize=6.4, fontName="Helvetica", fillColor=colors.HexColor("#86efac")))

    # Flechas Lambda -> DynamoDB y S3
    d.add(Line(356, 54, 334, 54, strokeColor=colors.HexColor("#818cf8"), strokeWidth=1.5))
    d.add(Line(182, 54, 160, 54, strokeColor=colors.HexColor("#4ade80"), strokeWidth=1.5))
    d.add(Line(258, 108, 258, 88, strokeColor=colors.HexColor("#818cf8"), strokeWidth=1.2))

    return d


def make_wrapped_table(rows, col_widths, header_bg="#0f172a", highlight_last_row=False):
    """Convierte cada celda en un Paragraph con salto de línea automático para que nada se amontone."""
    styles = getSampleStyleSheet()
    th_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.3,
        leading=11,
        textColor=colors.white,
    )
    td_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.9,
        leading=10.4,
        textColor=colors.HexColor("#1e293b"),
    )
    td_bold_style = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.0,
        leading=10.4,
        textColor=colors.HexColor("#0f172a"),
    )

    formatted_rows = []
    for r_idx, row in enumerate(rows):
        new_row = []
        is_header = r_idx == 0
        is_last = highlight_last_row and (r_idx == len(rows) - 1)
        for c_idx, cell_text in enumerate(row):
            if is_header:
                new_row.append(Paragraph(str(cell_text), th_style))
            elif is_last or c_idx == 0:
                new_row.append(Paragraph(str(cell_text), td_bold_style))
            else:
                new_row.append(Paragraph(str(cell_text), td_style))
        formatted_rows.append(new_row)

    tbl = Table(formatted_rows, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Filas cebreadas suaves
    for r_idx in range(1, len(rows)):
        bg = "#f8fafc" if r_idx % 2 == 1 else "#ffffff"
        style_cmds.append(("BACKGROUND", (0, r_idx), (-1, r_idx), colors.HexColor(bg)))

    if highlight_last_row:
        style_cmds.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e0f2fe")))

    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def generate_pdf():
    state = {}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))

    alb_url = state.get("alb_url", "http://pulseguard-alb-388362639.us-east-1.elb.amazonaws.com")
    ec2_ids = ", ".join(state.get("ec2_instance_ids", ["i-0fb4238d7d40beb66", "i-090f6ec7bd6218ebb"]))
    s3_bucket = state.get("s3_bucket", "pulseguard-logs-627739785043")

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title="PulseGuard Cloud - Documentación Técnica AWS",
        author="Anguiano Garcia Angel Yahir Guadalupe, Figueroa Robles Axel Israel, Torres Martinez Miguel Angel",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontSize=17.5,
        leading=21.5,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=13.5,
        alignment=1,
        textColor=colors.HexColor("#334155"),
        spaceAfter=10,
    )
    h1_style = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0369a1"),
        spaceBefore=10,
        spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=8.9,
        leading=12.5,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4,
    )
    code_style = ParagraphStyle(
        "CodeBlock",
        parent=styles["Code"],
        fontSize=8.0,
        leading=10.8,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"),
        borderPadding=5,
        spaceAfter=5,
    )

    story = []

    # =========================================================================
    # PÁGINA 1: PORTADA, RECURSOS REALES Y SECCIÓN 1 (GUÍA DE DESPLIEGUE)
    # =========================================================================
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
        [
            "Anguiano Garcia Angel Yahir Guadalupe",
            "Infraestructura como Código (Python Boto3) y Pipeline Serverless (SNS / AWS Lambda / Amazon S3)",
        ],
        [
            "Figueroa Robles Axel Israel",
            "Arquitectura de Alta Disponibilidad Multi-AZ (Application Load Balancer + Clúster EC2) y Aplicación Web",
        ],
        [
            "Torres Martinez Miguel Angel",
            "Ingeniería del Caos (Pruebas de Resiliencia), Base de Datos Amazon DynamoDB y Análisis de Costos",
        ],
    ]
    story.append(make_wrapped_table(team_data, [2.6 * inch, 4.4 * inch], header_bg="#0f172a"))
    story.append(Spacer(1, 8))

    meta_data = [
        ["Recurso AWS Desplegado", "Identificador / Endpoint Real en us-east-1 (Account: 627739785043)"],
        ["Application Load Balancer (ALB)", alb_url],
        ["Clúster Amazon EC2 (Multi-AZ)", f"{ec2_ids} (2x t3.micro, EBS gp2, LabInstanceProfile en us-east-1a y us-east-1b)"],
        ["Bucket Amazon S3 (Logs + DLQ)", f"s3://{s3_bucket}/ (Archivo de Logs JSON, Dead Letter Queue /dlq/ y Artefacto Bootstrap)"],
        ["Tablas Amazon DynamoDB", "pulseguard-services, pulseguard-incidents, pulseguard-metrics (Modo Serverless PAY_PER_REQUEST)"],
        ["Función AWS Lambda + Bus SNS", "pulseguard-anomaly-evaluator (LabRole) + Tópicos pulseguard-telemetry-stream e incident-alerts"],
    ]
    story.append(make_wrapped_table(meta_data, [2.2 * inch, 4.8 * inch], header_bg="#0369a1"))
    story.append(Spacer(1, 6))

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
    story.append(
        Paragraph(
            "<b>Paso 1: Configurar credenciales del AWS Academy Learner Lab</b> — Iniciar el laboratorio escolar (<i>Start Lab</i>), "
            "abrir <i>AWS Details &rarr; AWS CLI: Show</i> y pegar el bloque de credenciales temporales en el archivo local <code>aws_credentials.txt</code>.",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "<b>Paso 2: Verificar diagnóstico del laboratorio y ejecutar el despliegue automatizado</b>",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "uv run --with boto3 python infra/check_lab.py<br/>"
            "uv run --with boto3 --with requests python infra/deploy.py",
            code_style,
        )
    )
    story.append(
        Paragraph(
            "<b>¿Qué construye automáticamente <code>infra/deploy.py</code> sin tocar la consola web?</b><br/>"
            "1) Crea y configura el bucket <b>Amazon S3</b> (<code>pulseguard-logs-627739785043</code>) con políticas CORS.<br/>"
            "2) Crea dos tópicos en <b>Amazon SNS</b>: el bus asíncrono de telemetría y el canal de alertas por correo electrónico.<br/>"
            "3) Empaqueta en ZIP y despliega la función <b>AWS Lambda</b> (<code>pulseguard-anomaly-evaluator</code>) bajo <code>LabRole</code>.<br/>"
            "4) Aprovisiona las 3 tablas Serverless en <b>Amazon DynamoDB</b> (<code>services</code>, <code>incidents</code>, <code>metrics</code>) y precarga 5 microservicios.<br/>"
            "5) Configura los <b>Security Groups</b>, el <b>Target Group</b> con Health Check (<code>/api/health</code> cada 10s) y el <b>Application Load Balancer (ALB)</b>.<br/>"
            "6) Lanza <b>2 instancias Amazon EC2 (t3.micro)</b> en distintas Zonas de Disponibilidad (<code>us-east-1a</code> y <code>us-east-1b</code>) con bootstrap <code>UserData</code>.<br/>"
            "7) Para destruir los recursos y ahorrar créditos al cerrar sesión: <code>uv run --with boto3 python infra/destroy.py</code>.",
            body_style,
        )
    )

    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 2: SECCIÓN 2 (DIAGRAMA DE ARQUITECTURA) Y SECCIÓN 3 (RESILIENCIA)
    # =========================================================================
    story.append(Paragraph("2. Diagrama de Arquitectura y Flujo de Datos", h1_style))
    story.append(build_architecture_drawing())
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "<b>Flujo de Datos en la Arquitectura:</b> (1) Los usuarios e ingenieros SRE acceden a la aplicación web mediante el DNS público del "
            "<b>Application Load Balancer (ALB)</b>, el cual reparte el tráfico entre 2 nodos <b>Amazon EC2</b> Stateless ubicados en "
            "<code>us-east-1a</code> y <code>us-east-1b</code>. (2) Cuando un servicio envía un log o métrica a <code>POST /api/telemetry</code>, "
            "la instancia EC2 publica el evento de forma asíncrona en el bus de <b>Amazon SNS</b> y responde de inmediato <code>HTTP 202 Accepted</code>. "
            "(3) <b>AWS Lambda</b> es invocada por SNS, archiva el documento JSON original en <b>Amazon S3</b>, actualiza métricas y estado en "
            "<b>Amazon DynamoDB</b> y, si detecta una anomalía crítica (HTTP 5xx, Latencia &gt; 1500 ms o CPU &gt; 90%), abre un incidente "
            "automático y envía una alerta por correo electrónico mediante <b>Amazon SNS</b>.",
            body_style,
        )
    )

    story.append(Paragraph("3. Pruebas de Resiliencia ('Demuéstrame que no se rompe' - Regla 2)", h1_style))
    story.append(
        Paragraph(
            "Se integró un <b>Panel Interactivo de Chaos Engineering</b> dentro de la aplicación web junto con la suite automatizada "
            "<code>tests/resilience_test.py</code> para simular fallos reales en vivo y demostrar cómo la arquitectura se recupera sin romperse:",
            body_style,
        )
    )

    res_table_data = [
        [
            "Escenario de Fallo Simulado",
            "¿Qué pasaría en un sistema tradicional sin resiliencia?",
            "Cómo lo maneja nuestra arquitectura y Resultado Real Obtenido",
        ],
        [
            "1. Caída de un Servidor Web EC2<br/>(<i>/api/chaos/simulate-node-failure</i>)",
            "El portal web dejaría de cargar por completo (<i>Connection Refused / HTTP 502</i>) y se perderían las sesiones activas.",
            "El nodo afectado reporta HTTP 503 en <code>/api/health</code>. El <b>Application Load Balancer</b> detecta el fallo y desvía automáticamente el 100% del tráfico a la segunda instancia EC2 en otra Zona de Disponibilidad logrando <b>100.0% de disponibilidad continua (8/8 respuestas HTTP 200 OK)</b>.",
        ],
        [
            "2. Fallo Crítico en Lambda / Mensaje Corrupto (Poison Pill)<br/>(<i>/api/chaos/poison-pill</i>)",
            "Error HTTP 500 al usuario o bloqueo infinito de la cola de procesamiento impidiendo que se procesen los demás logs.",
            "Tras agotar sus reintentos automáticos, <b>AWS Lambda</b> captura la excepción y aísla el mensaje corrupto en la <b>Dead Letter Queue (DLQ)</b> en Amazon S3 (<code>s3://.../dlq/</code>), mientras los mensajes sanos enviados en paralelo se procesan sin ningún bloqueo.",
        ],
        [
            "3. Ráfaga Masiva Concurrente (Stress Test 30 Eventos)<br/>(<i>/api/chaos/stress-burst</i>)",
            "Saturación de CPU/RAM del servidor web y rechazo de conexiones por bloqueo de escritura en base de datos.",
            "Gracias al desacoplamiento asíncrono (<i>Load Leveling</i>), los 30 eventos concurrentes se aceptan en <b>720.7 ms (24.02 ms por evento) con 0.0% de pérdida de paquetes</b> y Lambda los procesa en segundo plano.",
        ],
        [
            "4. Congelamiento del Laboratorio Escolar (Cada 4 horas)",
            "Pérdida total de archivos guardados en el disco local de las máquinas virtuales eliminadas por el laboratorio.",
            "Instancias EC2 <b>100% Stateless</b> (toda la información vive en DynamoDB y S3) + script idempotente <code>deploy.py</code> que reactiva o reconstruye el clúster EC2 en ~90 segundos sin perder datos.",
        ],
    ]
    story.append(make_wrapped_table(res_table_data, [1.85 * inch, 2.05 * inch, 3.1 * inch], header_bg="#0f172a"))

    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 3: SECCIÓN 4 (JUSTIFICACIÓN DE DECISIONES) Y SECCIÓN 5 (COSTOS)
    # =========================================================================
    story.append(Paragraph("4. Justificación de Decisiones Arquitectónicas (Ventajas y Desventajas)", h1_style))
    story.append(
        Paragraph(
            "A continuación se fundamenta por qué se eligió cada servicio de AWS frente a otras alternativas disponibles, "
            "analizando sus ventajas técnicas y sus desventajas o compromisos (<i>trade-offs</i>):",
            body_style,
        )
    )

    just_data = [
        [
            "Servicio AWS Elegido",
            "Alternativa Descartada",
            "Ventajas Obtenidas en el Proyecto",
            "Desventajas / Trade-offs Encontrados",
        ],
        [
            "Application Load Balancer (ALB) + 2 Instancias EC2 t3.micro (Multi-AZ)",
            "1 sola instancia EC2 grande (Escalado Vertical)",
            "Elimina el Punto Único de Fallo (SPOF); reparte tráfico entre <code>us-east-1a</code> y <code>us-east-1b</code> y realiza failover automático con <i>Zero Downtime</i> si un servidor cae.",
            "El ALB tiene un costo fijo por hora ($0.0225/h) adicional a las instancias y añade ~2 a 3 ms de latencia de red.",
        ],
        [
            "Amazon DynamoDB (Serverless On-Demand)",
            "Amazon RDS (MySQL / PostgreSQL)",
            "Latencia inferior a 10 ms; escala instantáneamente sin administrar conexiones; al ser Serverless no cobra por hora en reposo ni se apaga cuando el laboratorio se congela.",
            "Al ser NoSQL clave-valor, no permite realizar consultas relacionales con <code>JOINs</code> complejos ni agregaciones SQL.",
        ],
        [
            "Bus Asíncrono Amazon SNS + AWS Lambda + DLQ en S3",
            "Procesamiento síncrono directo dentro de EC2",
            "La API web responde <code>HTTP 202</code> en milisegundos; absorbe picos masivos de tráfico sin saturar EC2 y aísla payloads corruptos en la Dead Letter Queue.",
            "Introduce consistencia eventual: los eventos tardan entre 1 y 2 segundos en procesarse en segundo plano antes de verse en el dashboard.",
        ],
        [
            "Amazon S3 con Presigned URLs",
            "Almacenamiento en disco local EBS de cada EC2",
            "Durabilidad del 99.999999999% (11 nueves) accesible desde ambos nodos EC2 y desde Lambda; descarga segura de logs JSON directo desde S3.",
            "Mayor latencia de escritura individual (~35-50 ms por operación <code>PUT Object</code>) comparada con escribir en un disco NVMe local.",
        ],
    ]
    story.append(make_wrapped_table(just_data, [1.65 * inch, 1.35 * inch, 2.15 * inch, 1.85 * inch], header_bg="#0369a1"))
    story.append(Spacer(1, 10))

    # SECCIÓN 5: ANÁLISIS DE COSTOS
    story.append(Paragraph("5. Análisis de Costos (Estimación a 1 Año Fuera de la Capa Gratuita)", h1_style))
    story.append(
        Paragraph(
            "<b>1. Costo real generado en el laboratorio escolar:</b> Menos de <b>$0.09 USD</b> de crédito académico virtual por sesión de pruebas, "
            "gracias a que DynamoDB, S3, Lambda y SNS operan bajo demanda y se incluye el script <code>infra/destroy.py</code> para apagar el ALB y EC2 al terminar.<br/>"
            "<b>2. Estimación para mantener la solución en producción por 1 Año (Fuera de la Capa Gratuita en us-east-1):</b> "
            "Considerando operación ininterrumpida 24/7 (730 horas/mes) para una empresa que monitorea 25 microservicios con un volumen de "
            "<b>1,500,000 eventos de telemetría al mes</b>:",
            body_style,
        )
    )

    cost_data = [
        [
            "Servicio AWS",
            "Volumen y Dimensionamiento Mensual (24/7)",
            "Precio Unitario Oficial (us-east-1)",
            "Costo Mensual (USD)",
            "Costo Anual (12 Meses)",
        ],
        [
            "Amazon EC2",
            "2 instancias t3.micro encendidas 24/7 (1,460 horas/mes) + 16 GB de almacenamiento EBS gp2",
            "$0.0104 / hora por instancia + $0.10 / GB-mes EBS",
            "$16.78 USD",
            "$201.36 USD",
        ],
        [
            "Application Load Balancer (ALB)",
            "1 Load Balancer activo 24/7 (730 horas/mes) + 0.5 LCU promedio de procesamiento",
            "$0.0225 / hora ($16.43) + $0.008 / LCU-hora ($2.92)",
            "$19.35 USD",
            "$232.20 USD",
        ],
        [
            "Amazon DynamoDB",
            "Modo On-Demand: 3,000,000 escrituras (WRU) + 6,000,000 lecturas (RRU) + 5 GB almacenados",
            "$1.25 / millón WRU + $0.25 / millón RRU + $0.25 / GB-mes",
            "$6.50 USD",
            "$78.00 USD",
        ],
        [
            "Amazon S3 (Standard)",
            "15 GB acumulados de logs JSON + 1,500,000 peticiones PUT y 300,000 peticiones GET al mes",
            "$0.023 / GB-mes + $0.005 / 1,000 PUT + $0.0004 / 1,000 GET",
            "$7.97 USD",
            "$95.64 USD",
        ],
        [
            "AWS Lambda",
            "300,000 invocaciones mensuales (procesando en lotes) x 200 ms promedio con 256 MB de RAM",
            "$0.20 / millón de invocaciones + $0.0000166667 / GB-segundo",
            "$0.31 USD",
            "$3.72 USD",
        ],
        [
            "Amazon SNS",
            "1,500,000 publicaciones en el bus de telemetría + 2,000 notificaciones de incidentes por correo",
            "$0.50 / millón de publicaciones + $2.00 / 100,000 correos",
            "$0.79 USD",
            "$9.48 USD",
        ],
        [
            "TOTAL ESTIMADO",
            "Infraestructura Multi-AZ 24/7 + Pipeline Serverless Completo (Sin Capa Gratuita)",
            "Tarifa Estándar de Producción en us-east-1",
            "$51.70 USD / mes",
            "$620.40 USD / año",
        ],
    ]
    story.append(
        make_wrapped_table(
            cost_data,
            [1.35 * inch, 2.15 * inch, 1.5 * inch, 1.0 * inch, 1.0 * inch],
            header_bg="#0f172a",
            highlight_last_row=True,
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "<b>Conclusión del Análisis Financiero:</b> Mantener la plataforma completa operando 24/7 fuera de la capa gratuita cuesta "
            "<b>$51.70 USD al mes ($620.40 USD al año)</b>. El 70% del presupuesto corresponde al cómputo continuo 24/7 (ALB + 2 instancias EC2), "
            "mientras que toda la capa Serverless (DynamoDB, S3, Lambda y SNS) procesando 1.5 millones de eventos mensuales representa solo "
            "<b>$15.57 USD al mes</b>, demostrando una alta eficiencia costo-beneficio.",
            body_style,
        )
    )

    doc.build(story)
    print(f"[OK] PDF regenerado sin texto amontonado en: {OUTPUT_PDF}")


if __name__ == "__main__":
    generate_pdf()

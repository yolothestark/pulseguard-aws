# PulseGuard Cloud — Plataforma Distribuida de Monitoreo de Servicios, Logs y Gestión de Incidentes en AWS

**Categoría:** Aplicación Web Cloud-Native de Alta Disponibilidad y Tolerancia a Fallos  
**Región AWS:** `us-east-1` (N. Virginia) — Compatible al 100% con *AWS Academy Learner Lab* (`LabRole`)

## Integrantes del Equipo
* **Anguiano Garcia Angel Yahir Guadalupe**
* **Figueroa Robles Axel Israel**
* **Torres Martinez Miguel Angel**

---

## Descripción General

**PulseGuard Cloud** es una plataforma web centralizada de observabilidad, monitoreo de microservicios, ingesta asíncrona de logs y gestión automatizada de incidentes construida sobre **Amazon Web Services (AWS)**.

El sistema cumple estrictamente con las 4 reglas del proyecto:
1. **Infraestructura 100% Automatizada (Cero Clics en Consola Web):** Todo el entorno en AWS (S3, DynamoDB, SQS, DLQ, SNS, Lambda, Security Groups, EC2 en múltiples zonas de disponibilidad y Application Load Balancer) se construye automáticamente mediante el script `infra/deploy.py` usando **Python (`boto3`)**.
2. **Pruebas de Resiliencia Integradas ("Demuéstrame que no se rompe"):** Incluye tanto un **Simulador de Chaos Engineering interactivo en la interfaz web** como la suite automatizada `tests/resilience_test.py` que demuestra:
   * **Failover Multi-AZ de Servidores Web EC2** detrás de un **Application Load Balancer (ALB)** con *Zero Downtime*.
   * **Aislamiento de Fallos Asíncronos (*Poison Pill*)** en **AWS Lambda** mediante reintentos de **Amazon SQS** y desvío automático a una **Dead Letter Queue (DLQ)**.
   * **Absorción de Ráfagas de Tráfico (*Queue-Based Load Leveling*)** sin pérdida de paquetes (`0% data loss`).
3. **Aplicación Web Completa:** Backend API REST en **FastAPI (`app/backend/main.py`)**, procesador serverless en **AWS Lambda (`app/worker/lambda_function.py`)** y Dashboard Reactivo en tiempo real (`app/frontend/index.html`).
4. **Arquitectura de Nivel Empresarial (Esfuerzo de 1 Mes):** Desacoplamiento completo de cómputo (*Stateless EC2*), almacenamiento caliente (*DynamoDB*), archivo histórico frío auditable con *Presigned URLs* (*Amazon S3*), colas de mensajería (*SQS + DLQ*) y alertas push (*Amazon SNS*).

---

## Estructura del Repositorio

```text
pulseguard-aws/
├── README.md                                  # Guía principal del repositorio
├── requirements.txt                           # Dependencias Python (boto3, fastapi, uvicorn, requests)
├── aws_credentials.txt                        # Credenciales temporales del AWS Learner Lab (ignorado en Git)
├── infra/                                     # REGLA 1: Infraestructura como Código (Boto3)
│   ├── config.py                              # Parámetros globales y cargador de sesión AWS
│   ├── check_lab.py                           # Diagnóstico rápido de permisos del Learner Lab
│   ├── deploy.py                              # Despliegue automatizado completo en AWS (Cero Clics)
│   ├── seed_demo.py                           # Precarga de servicios, logs en S3 e incidentes en DynamoDB
│   └── destroy.py                             # Limpieza total de recursos para ahorrar créditos del laboratorio
├── app/                                       # REGLA 3: Aplicación Web y Procesador Asíncrono
│   ├── backend/
│   │   └── main.py                            # Servidor Web FastAPI + API REST + Endpoints de Chaos Engineering
│   ├── worker/
│   │   └── lambda_function.py                 # Función AWS Lambda consumidora de SQS, evaluadora de anomalías y SNS
│   └── frontend/
│       └── index.html                         # Dashboard Web en Tiempo Real + Panel Interactivo de Resiliencia
├── tests/                                     # REGLA 2: Pruebas de Resiliencia ("Demuéstrame que no se rompe")
│   └── resilience_test.py                     # Suite automatizada de Chaos Engineering y Stress Test
└── docs/                                      # Documentación Técnica Completa (Lista para PDF) y Presentación
    ├── DOCUMENTACION_PROYECTO_PULSEGUARD.md   # Documento técnico con las 5 secciones obligatorias
    └── GUION_PRESENTACION_DEFENSA.md          # Guion minuto a minuto para la Demo en Vivo (5m) + Defensa (5m)
```

---

## Inicio Rápido (Despliegue en 2 Minutos)

### 1. Configurar Credenciales del AWS Academy Learner Lab
Inicia tu laboratorio (*Start Lab*), abre **AWS Details -> AWS CLI: Show** y pega el bloque `[default]` en `aws_credentials.txt`.

### 2. Verificar Conexión con el Laboratorio
```powershell
uv run --with boto3 python infra/check_lab.py
```

### 3. Desplegar Toda la Infraestructura en AWS (Cero Clics)
```powershell
uv run --with boto3 --with requests python infra/deploy.py
```
Al finalizar, el script imprimirá en consola la **URL pública del Application Load Balancer (`http://pulseguard-alb-...us-east-1.elb.amazonaws.com`)**.

### 4. Ejecutar Pruebas Automatizadas de Resiliencia
```powershell
uv run --with boto3 --with requests python tests/resilience_test.py
```

### 5. Destruir Recursos al Terminar la Sesión (Ahorro de Créditos)
```powershell
uv run --with boto3 python infra/destroy.py
```

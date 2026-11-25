# Documentación Técnica del Proyecto: PulseGuard Cloud
## Plataforma Distribuida de Monitoreo de Servicios, Ingesta Asíncrona de Logs y Gestión de Incidentes en AWS

---

### Portada Oficial
* **Proyecto:** PulseGuard Cloud — Plataforma Centralizada de Observabilidad, Logs y Gestión de Incidentes Tolerante a Fallos en AWS
* **Categoría:** Aplicación Web Cloud-Native Distribuida
* **Integrantes del Equipo:**
  * **Anguiano Garcia Angel Yahir Guadalupe**
  * **Figueroa Robles Axel Israel**
  * **Torres Martinez Miguel Angel**
* **Región de Despliegue:** `us-east-1` (Norte de Virginia)
* **Cuenta AWS (Learner Lab):** `627739785043`
* **Infraestructura como Código (Regla 1):** 100% automatizada con Python (`boto3`) sin interacción manual en la consola web.

---

## 1. Guía de Despliegue (Paso a Paso desde Cero)

Esta guía describe cómo cualquier evaluador o ingeniero puede configurar, desplegar, probar y destruir la infraestructura completa de **PulseGuard Cloud** desde cero utilizando un único comando en terminal, cumpliendo con la **Regla 1 (Cero Clics en la Consola de AWS)**.

### 1.1 Requisitos Previos
1. **Sistema Operativo:** Windows 10/11, Linux o macOS con acceso a terminal (PowerShell o Bash).
2. **Entorno de Python:** Python 3.10+ o gestor `uv` (`boto3`, `fastapi`, `uvicorn`, `requests`, `pydantic`).
3. **Acceso a AWS:** Cuenta activa de *AWS Academy Learner Lab* (o cuenta estándar de AWS con permisos equivalentes a `LabRole`).

### 1.2 Paso 1: Clonar el Repositorio del Proyecto
```bash
git clone <URL_DEL_REPOSITORIO_GIT>
cd pulseguard-aws
```

### 1.3 Paso 2: Configurar las Credenciales Temporales de AWS
1. En el portal de **AWS Academy Learner Lab**, hacer clic en **Start Lab** y esperar a que el indicador del laboratorio cambie a color verde.
2. Hacer clic en **AWS Details** y, junto a **AWS CLI:**, presionar el botón **Show**.
3. Copiar el bloque de credenciales temporales (`aws_access_key_id`, `aws_secret_access_key` y `aws_session_token`) y pegarlo en el archivo `aws_credentials.txt` en la raíz del proyecto (este archivo está excluido en `.gitignore` por seguridad):
   ```ini
   [default]
   aws_access_key_id=ASIA...
   aws_secret_access_key=...
   aws_session_token=...
   ```

### 1.4 Paso 3: Validar la Conexión y Permisos del Laboratorio
Ejecutar el script de diagnóstico para confirmar la identidad STS, el `Account ID`, la disponibilidad del rol `LabRole` y la VPC por defecto en `us-east-1`:
```powershell
uv run --with boto3 python infra/check_lab.py
```

### 1.5 Paso 4: Ejecutar el Despliegue Automatizado (`deploy.py`)
Ejecutar el script maestro de aprovisionamiento:
```powershell
uv run --with boto3 --with requests python infra/deploy.py
```

**¿Qué construye automáticamente `infra/deploy.py` sin tocar la consola web?**
1. **Amazon S3 (`pulseguard-logs-<account_id>`):** Crea el bucket de almacenamiento histórico de logs, configura las reglas CORS y sube el paquete de código de la aplicación (`artifacts/app_bundle.zip`).
2. **Amazon DynamoDB:** Crea 3 tablas *Serverless* en modo `PAY_PER_REQUEST` y espera hasta que estén `ACTIVE`:
   * `pulseguard-services` (PK: `service_id`)
   * `pulseguard-incidents` (PK: `incident_id`)
   * `pulseguard-metrics` (PK: `metric_id`)
3. **Amazon SQS (`pulseguard-telemetry-queue` y `pulseguard-telemetry-dlq`):** Crea primero la *Dead Letter Queue (DLQ)* y luego la cola principal vinculada mediante `RedrivePolicy` (`maxReceiveCount = 2`, `VisibilityTimeout = 10s`).
4. **Amazon SNS (`pulseguard-incident-alerts`):** Crea el tópico de notificaciones push por correo electrónico para incidentes críticos.
5. **AWS Lambda (`pulseguard-anomaly-evaluator`):** Empaqueta en memoria `app/worker/lambda_function.py`, crea la función en Python 3.12 asignándole `LabRole`, inyecta las variables de entorno y registra el *Event Source Mapping* (trigger automático) desde la cola SQS principal.
6. **VPC Security Groups (`pulseguard-alb-sg` y `pulseguard-ec2-sg`):** Configura las reglas de firewall permitiendo tráfico HTTP (puerto 80) hacia el balanceador y las instancias.
7. **Application Load Balancer (`pulseguard-alb`) y Target Group (`pulseguard-tg`):** Aprovisiona un balanceador de carga de capa 7 distribuido en múltiples subredes/Zonas de Disponibilidad (`us-east-1a` y `us-east-1b`) con chequeos de salud cada 10 segundos hacia `/api/health`.
8. **Clúster de 2 Instancias Amazon EC2 (`t3.micro`) con Bootstrap `UserData`:** Consulta en AWS SSM la imagen AMI más reciente de *Amazon Linux 2023*, lanza 2 servidores en distintas Zonas de Disponibilidad con `LabInstanceProfile`, instala automáticamente FastAPI/Uvicorn, descarga el código desde S3 y registra el servicio `systemd` (`pulseguard.service`).
9. **Semilla de Datos (`seed_demo.py`):** Precarga 5 microservicios empresariales, logs históricos en S3 e incidentes iniciales en DynamoDB.

Al finalizar, la terminal imprime la **URL pública del Application Load Balancer** (`http://pulseguard-alb-...us-east-1.elb.amazonaws.com`) lista para abrirse en cualquier navegador web.

### 1.6 Paso 5: Manejo del Congelamiento del Laboratorio y Limpieza (`destroy.py`)
* **Si el laboratorio escolar se congela tras 4 horas:** Basta con iniciar nuevamente el laboratorio, actualizar `aws_credentials.txt` y correr otra vez `python infra/deploy.py`. Al ser un script **idempotente** y una arquitectura **Stateless**, reutilizará los datos de S3 y DynamoDB y reactivará o recreará las instancias EC2 automáticamente.
* **Para apagar y eliminar la infraestructura al terminar de trabajar (ahorro de créditos):**
  ```powershell
  uv run --with boto3 python infra/destroy.py
  ```

---

## 2. Diagrama de Arquitectura

La arquitectura de **PulseGuard Cloud** implementa dos patrones fundamentales de ingeniería en la nube: **Alta Disponibilidad Activo-Activo (Multi-AZ)** en la capa web y **Procesamiento Asíncrono Desacoplado con Aislamiento de Fallos (Queue-Based Load Leveling + Dead Letter Queue)** en la capa de ingesta y análisis.

```mermaid
flowchart TB
    subgraph Clientes ["Capa de Clientes y Servicios Monitoreados"]
        Browser["Ingeniero SRE / Navegador Web<br/>(Dashboard & Chaos Panel)"]
        Microservices["Microservicios / Agentes de Telemetría<br/>(Envío de Logs y Métricas)"]
    end

    subgraph Red_VPC ["VPC AWS (us-east-1) - Capa de Cómputo de Alta Disponibilidad"]
        ALB["Application Load Balancer (ALB)<br/>pulseguard-alb (Multi-AZ, Puerto 80)<br/>Health Check: /api/health cada 10s"]
        
        subgraph AZ_A ["Zona de Disponibilidad us-east-1a"]
            EC2_A["Amazon EC2 Nodo 1 (t3.micro)<br/>FastAPI + Uvicorn (Stateless)<br/>Rol IAM: LabInstanceProfile"]
        end

        subgraph AZ_B ["Zona de Disponibilidad us-east-1b"]
            EC2_B["Amazon EC2 Nodo 2 (t3.micro)<br/>FastAPI + Uvicorn (Stateless)<br/>Rol IAM: LabInstanceProfile"]
        end
    end

    subgraph Async_Layer ["Capa de Mensajería y Procesamiento Serverless"]
        SQS_Main["Amazon SQS (Cola Principal)<br/>pulseguard-telemetry-queue<br/>VisibilityTimeout: 10s"]
        SQS_DLQ["Amazon SQS (Dead Letter Queue)<br/>pulseguard-telemetry-dlq<br/>Aísla mensajes tras 2 fallos"]
        Lambda["AWS Lambda (Python 3.12)<br/>pulseguard-anomaly-evaluator<br/>Motor de Reglas y Anomalías"]
        SNS["Amazon SNS<br/>pulseguard-incident-alerts<br/>Alertas Críticas por Email"]
    end

    subgraph Storage_Layer ["Capa de Persistencia Serverless (Cero Pérdida de Estado)"]
        DDB_Srv[("Amazon DynamoDB<br/>pulseguard-services<br/>(Estado y SLA)")]
        DDB_Met[("Amazon DynamoDB<br/>pulseguard-metrics<br/>(Telemetría en Caliente)")]
        DDB_Inc[("Amazon DynamoDB<br/>pulseguard-incidents<br/>(Gestión de Incidentes)")]
        S3_Logs[("Amazon S3 Bucket<br/>pulseguard-logs-627739785043<br/>(Archivo JSON Auditable + Presigned URLs)")]
    end

    Browser & Microservices -->|HTTP :80| ALB
    ALB -->|Balanceo Round-Robin| EC2_A & EC2_B

    EC2_A & EC2_B -->|1. Encola telemetría (202 Accepted)| SQS_Main
    EC2_A & EC2_B -->|Consulta Dashboard y Presigned URLs| DDB_Srv & DDB_Met & DDB_Inc & S3_Logs

    SQS_Main -->|2. Trigger Event Source Mapping| Lambda
    SQS_Main -.->|RedrivePolicy (si falla 2 veces)| SQS_DLQ

    Lambda -->|3. Archiva payload crudo JSON| S3_Logs
    Lambda -->|4. Registra métrica y actualiza SLA| DDB_Met & DDB_Srv
    Lambda -->|5. Si detecta anomalía: Abre Incidente| DDB_Inc
    Lambda -->|6. Si es CRITICAL: Publica Alerta| SNS
```

### Flujo de Datos Paso a Paso
1. **Tráfico Síncrono (Dashboard y API):** El usuario accede al DNS público del **Application Load Balancer (`pulseguard-alb`)**, el cual reparte las solicitudes entre **2 instancias EC2 (`t3.micro`)** ubicadas en distintas Zonas de Disponibilidad (`us-east-1a` y `us-east-1b`).
2. **Ingesta Asíncrona de Telemetría:** Cuando llega un log o métrica a `POST /api/telemetry`, el nodo EC2 no bloquea al cliente procesándolo síncronamente; lo deposita en **Amazon SQS (`pulseguard-telemetry-queue`)** y responde inmediatamente `HTTP 202 Accepted` en pocos milisegundos.
3. **Evaluación Serverless:** **AWS Lambda (`pulseguard-anomaly-evaluator`)** es invocada automáticamente por el *Event Source Mapping* de SQS en lotes de hasta 5 mensajes.
4. **Persistencia Dual (Caliente + Fría):** Lambda archiva el documento JSON original en **Amazon S3** (para auditoría forense y descarga mediante *Presigned URLs*) y actualiza las tablas de **Amazon DynamoDB** (`pulseguard-metrics` y `pulseguard-services`).
5. **Detección de Incidentes y Alertas:** Si un evento supera los umbrales críticos (`HTTP >= 500`, `latencia >= 1500 ms` o `CPU >= 90%`), Lambda abre un incidente en `pulseguard-incidents` y dispara una notificación inmediata por correo electrónico a través de **Amazon SNS (`pulseguard-incident-alerts`)**.

---

## 3. Pruebas de Resiliencia ("Demuéstrame que no se rompe" — Regla 2)

Para demostrar empíricamente que la arquitectura resiste fallos de infraestructura, errores de software y picos de tráfico sin colapsar ni perder datos, se diseñaron y ejecutaron **3 pruebas de resistencia (Chaos Engineering)** tanto desde el panel interactivo de la aplicación web como mediante el script automatizado `tests/resilience_test.py`.

### Escenario 1: Caída de un Servidor Web EC2 (Failover Multi-AZ con Application Load Balancer)
* **Hipótesis (¿Qué pasaría en un sistema tradicional?):** Si la aplicación estuviera alojada en una sola máquina virtual y el proceso web colapsa o la instancia falla, todos los usuarios recibirían `Connection Refused` o `502 Bad Gateway`, provocando una caída del 100% del sistema.
* **Simulación ejecutada:** Se invoca el experimento de caos `POST /api/chaos/simulate-node-failure`, el cual provoca que el nodo EC2 alcanzado reporte estado crítico (`HTTP 503 Service Unavailable`) en su endpoint `/api/health`.
* **Cómo lo maneja nuestra arquitectura:**
  1. El **Application Load Balancer (ALB)** ejecuta *Health Checks* cada 10 segundos contra `/api/health`.
  2. Al detectar que el Nodo 1 (`us-east-1a`) falla el chequeo, el ALB lo marca como `unhealthy` y **redirige automáticamente el 100% del tráfico entrante hacia el Nodo 2 (`us-east-1b`)**.
  3. Dado que las instancias EC2 son **100% Stateless** (toda la sesión y los datos residen en DynamoDB y S3), el usuario final sigue navegando, consultando logs y gestionando incidentes con **0% de pérdida de sesión y alta disponibilidad continua**.

### Escenario 2: Fallo Crítico en el Procesador Serverless / Mensaje Corrupto (*Poison Pill* → SQS + Dead Letter Queue)
* **Hipótesis (¿Qué pasaría sin desacoplamiento ni DLQ?):** Si un microservicio envía un payload corrupto que dispara una excepción no controlada en el procesador, en una arquitectura síncrona tumbaría el hilo del servidor (`HTTP 500`), y en una cola simple sin DLQ quedaría en un bucle infinito de reintentos bloqueando todos los mensajes posteriores.
* **Simulación ejecutada:** Se envía a la cola SQS un evento con el flag `"simulate_worker_crash": true` (*Poison Pill*) seguido inmediatamente por un evento de telemetría sano.
* **Cómo lo maneja nuestra arquitectura:**
  1. **AWS Lambda** intenta procesar el mensaje corrupto y lanza intencionalmente un `RuntimeError`.
  2. **Amazon SQS** retiene el mensaje y, tras expirar el `VisibilityTimeout` (10s), realiza un segundo intento automático.
  3. Al fallar por segunda vez (`maxReceiveCount = 2`), la **`RedrivePolicy`** de SQS **aísla automáticamente el mensaje defectuoso moviéndolo a la Dead Letter Queue (`pulseguard-telemetry-dlq`)**.
  4. El mensaje sano enviado en paralelo se procesa limpiamente en DynamoDB y S3 sin sufrir bloqueo alguno, y los operadores pueden inspeccionar la DLQ desde el dashboard web.

### Escenario 3: Ráfaga Masiva Concurrente de Tráfico (*Stress Test / Queue-Based Load Leveling*)
* **Hipótesis (¿Qué pasaría bajo un pico repentino de tráfico?):** Cuando ocurre una caída en cascada en un centro de datos, cientos de agentes envían logs y alertas al mismo segundo. Si el servidor web intentara escribir y evaluar cada log directamente contra la base de datos y S3 en el hilo HTTP, agotaría sus workers y rechazaría conexiones.
* **Simulación ejecutada:** El script `tests/resilience_test.py` (y el botón *Lanzar Ráfaga* del dashboard) inyecta una ráfaga concurrente de **30 eventos de telemetría** en milisegundos hacia `pulseguard-telemetry-queue`.
* **Cómo lo maneja nuestra arquitectura:**
  1. **Amazon SQS** absorbe la ráfaga completa en menos de 250 ms con **0% de pérdida de paquetes (`packet_loss_pct = 0.0%`)**.
  2. **AWS Lambda** escala horizontalmente de forma automática para drenar la cola en lotes (`BatchSize = 5`), archivando los 30 eventos en S3, actualizando DynamoDB y disparando la alerta crítica en SNS sin degradar el tiempo de respuesta de la interfaz web.

---

## 4. Justificación de Decisiones Arquitectónicas

En este apartado se fundamenta técnicamente por qué se seleccionó cada servicio de AWS frente a sus alternativas dentro del ecosistema cloud, analizando sus ventajas y desventajas reales.

### 4.1 Application Load Balancer (ALB) + 2 Instancias Amazon EC2 (`t3.micro`) vs. Instancia EC2 Única Vertical
* **Por qué se eligió:** Un solo servidor grande (`t3.large`) sigue siendo un **Punto Único de Fallo (SPOF)**: si la Zona de Disponibilidad sufre un corte o el proceso web se bloquea, toda la plataforma cae. Con un **ALB + 2 instancias `t3.micro` en distintas Zonas de Disponibilidad (`us-east-1a` y `us-east-1b`)**, logramos redundancia real Activo-Activo y conmutación automática (*failover*).
* **Ventajas:** Alta disponibilidad Multi-AZ real; permite mantenimiento o caída de un nodo con *Zero Downtime*; health checks automáticos de capa 7 (`/api/health`).
* **Desventajas:** El ALB tiene un costo fijo por hora más alto que una IP elástica directa y añade ~2-4 ms de latencia por salto de red.

### 4.2 Amazon SQS + Dead Letter Queue (DLQ) + AWS Lambda vs. Procesamiento Síncrono en EC2
* **Por qué se eligió:** Procesar, evaluar reglas de negocio, escribir en base de datos, archivar en S3 y enviar correos SNS dentro de la misma petición HTTP acopla todos los componentes. Al introducir **Amazon SQS + AWS Lambda**, desacoplamos la recepción del procesamiento pesado.
* **Ventajas:** Si Lambda, DynamoDB o SNS experimentan latencia temporal, la API web sigue aceptando logs sin fallar; la **DLQ** garantiza que ningún evento fallido se pierda ni bloquee la cola; Lambda cuesta \$0 cuando no hay tráfico.
* **Desventajas:** Introduce **consistencia eventual** (los logs tardan entre 1 y 3 segundos en reflejarse en el dashboard tras ser aceptados en SQS) y requiere manejar idempotencia.

### 4.3 Amazon DynamoDB (`PAY_PER_REQUEST`) vs. Amazon RDS (MySQL / PostgreSQL)
* **Por qué se eligió:** Los datos de telemetría, estado de servicios e incidentes tienen un patrón de acceso clave-valor y series de tiempo de alta velocidad de escritura. **Amazon DynamoDB** ofrece latencias de un solo dígito de milisegundo (< 10 ms), es 100% *Serverless* y no se apaga ni pierde disponibilidad cuando el laboratorio educativo detiene instancias de cómputo.
* **Ventajas:** Escalabilidad instantánea sin administrar servidores ni conexiones (*connection pooling*); replicación automática en 3 instalaciones dentro de `us-east-1`; pago estricto por lectura/escritura.
* **Desventajas:** No permite consultas relacionales complejas (`JOINs`) ni agregaciones analíticas SQL ad-hoc sin exportar los datos.

### 4.4 Amazon S3 (con *Presigned URLs*) vs. Almacenamiento Local en Disco EBS de EC2
* **Por qué se eligió:** Guardar archivos de logs en el disco EBS local de una instancia EC2 viola el principio *Stateless*: el nodo EC2-B no podría ver los archivos guardados en el nodo EC2-A, y si la instancia se elimina al congelarse el laboratorio, toda la evidencia forense se perdería. **Amazon S3** ofrece durabilidad del `99.999999999%` (11 nueves) compartida por todos los nodos y funciones Lambda.
* **Ventajas:** Durabilidad extrema, bajo costo por GB (\$0.023/GB-mes) y descarga segura directa desde el navegador mediante URLs pre-firmadas temporales (*Presigned URLs*) sin saturar el ancho de banda de las instancias EC2.
* **Desventajas:** Mayor latencia por operación de escritura individual (`PUT Object` ~30-60 ms) comparado con un disco NVMe local.

---

## 5. Análisis de Costos (Estimación Anual Fuera de la Capa Gratuita y Consumo en Laboratorio)

### 5.1 Consumo Real durante el Desarrollo en el Laboratorio Escolar
Durante el desarrollo y las pruebas en el **AWS Academy Learner Lab**, todos los recursos operaron dentro del crédito académico virtual. Gracias al uso del script de limpieza `infra/destroy.py` al finalizar cada sesión y al modelo *On-Demand* de DynamoDB, Lambda, SQS y S3, el costo real consumido por sesión de prueba de 2 horas es **inferior a \$0.09 USD** de crédito virtual.

### 5.2 Estimación de Costos de Producción por 1 Año (Fuera de la Capa Gratuita — Región `us-east-1`)
Supuesto de carga de producción para una empresa mediana que monitorea **25 microservicios** enviando telemetría continua (**1,500,000 eventos de telemetría al mes**, 24/7, los 365 días del año = 730 horas/mes), sin aplicar descuentos de *AWS Free Tier*:

| Servicio AWS | Configuración y Volumen Mensual Estimado | Precio Unitario Oficial (`us-east-1`) | Costo Mensual (USD) | Costo Anual (12 Meses - USD) |
| :--- | :--- | :--- | :---: | :---: |
| **Amazon EC2** | 2 instancias `t3.micro` (2 vCPU, 1 GB RAM c/u) encendidas 24/7 (730 h/mes × 2 = 1,460 horas) + 2 volúmenes EBS `gp3` de 8 GB | \$0.0104 / hora por instancia + \$0.08 / GB-mes EBS | \$16.46 | **\$197.52** |
| **Application Load Balancer (ALB)** | 1 ALB activo 24/7 (730 h/mes) + consumo estimado de 0.5 LCU promedio | \$0.0225 / hora (\$16.43) + \$0.008 / LCU-hora (\$2.92) | \$19.35 | **\$232.20** |
| **Amazon DynamoDB** | Modo *On-Demand*: 3,000,000 de escrituras (WRU) y 6,000,000 de lecturas (RRU) al mes + 5 GB de almacenamiento | \$1.25 / millón WRU + \$0.25 / millón RRU + \$0.25 / GB-mes | \$6.50 | **\$78.00** |
| **Amazon S3 (`Standard`)** | 15 GB acumulados de logs JSON comprimidos + 1,500,000 peticiones `PUT` y 300,000 `GET` al mes | \$0.023 / GB-mes + \$0.005 / 1,000 PUT + \$0.0004 / 1,000 GET | \$7.97 | **\$95.64** |
| **Amazon SQS (Main + DLQ)** | 3,000,000 de peticiones mensuales (recepción, entrega y borrado en lotes) | \$0.40 / millón de peticiones (sin capa gratuita) | \$1.20 | **\$14.40** |
| **AWS Lambda** | 300,000 invocaciones/mes (BatchSize=5) × 200 ms promedio a 256 MB RAM | \$0.20 / millón req + \$0.0000166667 / GB-segundo | \$0.31 | **\$3.72** |
| **Amazon SNS** | 2,000 notificaciones de incidentes por correo electrónico + llamadas API | \$2.00 / 100,000 notificaciones por email | \$0.04 | **\$0.48** |
| **TOTAL ESTIMADO** | **Infraestructura Multi-AZ 24/7 + Pipeline Serverless para 1.5M eventos/mes** | — | **\$51.83 USD / mes** | **\$621.96 USD / año** |

> **Conclusión Financiera:** Mantener **PulseGuard Cloud** operando 24/7 en producción con alta disponibilidad Multi-AZ fuera de la capa gratuita cuesta aproximadamente **\$51.83 USD al mes (\$621.96 USD al año)**. El 69% del costo corresponde a mantener encendidos el Application Load Balancer y las 2 instancias EC2 las 24 horas, mientras que toda la capa *Serverless* (DynamoDB, S3, SQS, Lambda y SNS) procesando 1.5 millones de logs mensuales representa únicamente **\$16.02 USD al mes**, demostrando la alta eficiencia económica del diseño híbrido desacoplado.

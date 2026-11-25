# Guion de Presentación y Defensa en Clase — PulseGuard Cloud
**Duración Total:** 8 a 10 minutos (5 min Demostración en Vivo + 3–5 min Explicación Técnica)

## Integrantes del Equipo y Distribución Sugerida de Roles
1. **Anguiano Garcia Angel Yahir Guadalupe:** Automatización IaC con Python `boto3` (Regla 1) y Flujo del Pipeline Asíncrono (SQS, DLQ, Lambda, S3).
2. **Figueroa Robles Axel Israel:** Demostración en Vivo de la Aplicación Web, Alta Disponibilidad Multi-AZ (ALB + 2 EC2) y Simulación de Caída de Servidor.
3. **Torres Martinez Miguel Angel:** Pruebas de Resiliencia (Chaos Engineering), Justificación de Decisiones Arquitectónicas y Análisis de Costos Anual.

---

## Parte 1: Demostración en Vivo (5 Minutos)

> **Preparación 10 minutos antes de pasar al frente:**
> 1. Iniciar el *AWS Academy Learner Lab* y pegar las credenciales en `aws_credentials.txt`.
> 2. Ejecutar `uv run --with boto3 --with requests python infra/deploy.py` (toma ~90 segundos si ya estaba creado o ~2.5 minutos desde cero).
> 3. Tener abierta una pestaña con la URL pública del **Application Load Balancer (`http://pulseguard-alb-...us-east-1.elb.amazonaws.com`)** y otra con la terminal mostrando la salida de `deploy.py` y `resilience_test.py`.

### Minuto 0:00 – 1:15 | Evidencia de la Regla 1 (Cero Clics) y Vista General de la Web
* **Qué mostrar en pantalla:** Terminal con el resultado de `python infra/deploy.py` y luego el Dashboard de **PulseGuard Cloud** corriendo en el DNS del Application Load Balancer.
* **Qué decir:**
  > *"Buenas tardes. Presentamos **PulseGuard Cloud**, una plataforma web distribuida de monitoreo de microservicios, ingesta asíncrona de logs y gestión de incidentes en AWS. Cumpliendo la **Regla 1**, ningún recurso fue creado haciendo clics en la consola web: nuestro script `infra/deploy.py` en Python con `boto3` aprovisionó automáticamente el bucket S3, 3 tablas en DynamoDB, colas SQS principal y Dead Letter Queue, función AWS Lambda, tópico SNS, Security Groups, un Application Load Balancer y 2 instancias EC2 en distintas Zonas de Disponibilidad (`us-east-1a` y `us-east-1b`)."*
* **Detalle visual clave:** Señalar arriba a la derecha en la barra del dashboard el indicador **"Nodo EC2 Respondiendo (ALB)"**, mostrando cómo el balanceador alterna tráfico entre las dos instancias EC2 reales.

### Minuto 1:15 – 2:30 | Flujo Funcional Completo (Servicios, Telemetría, S3, DynamoDB y SNS)
* **Qué hacer en vivo:**
  1. Hacer clic en **"+ Enviar Log / Métrica Manual"** (o mostrar los 5 servicios monitoreados).
  2. Enviar un evento con nivel `CRITICAL` (`Latencia: 1850 ms`, `HTTP 503`, `CPU: 93%`).
  3. En 2 a 3 segundos, ver cómo **Amazon SQS** dispara **AWS Lambda**, el servicio pasa a estado `DOWN`, aparece automáticamente el nuevo incidente en el **Centro de Incidentes**, y hacer clic en el botón **`JSON S3`** en la tabla de telemetría para abrir la evidencia archivada directamente desde **Amazon S3** con una *Presigned URL*.

### Minuto 2:30 – 5:00 | El Momento Estrella: Pruebas de Resiliencia en Vivo ("Demuéstrame que no se rompe" — Regla 2)
Usar el panel amarillo **"Regla 2: Chaos Engineering en Vivo"** integrado en el dashboard:

1. **Prueba 1 — Derribar un Servidor Web EC2 en Vivo (Min 2:30 – 3:30):**
   * Presionar el botón rojo **"Derribar Nodo EC2 Actual (75s)"**.
   * **Qué explicar mientras ocurre:** *"Acabamos de inyectar un fallo crítico en la instancia EC2 que nos estaba atendiendo para que su endpoint `/api/health` devuelva `HTTP 503`. Como pueden ver, la aplicación web NO se cae: el Application Load Balancer detecta el nodo enfermo y conmuta automáticamente el 100% de las peticiones a la segunda instancia EC2 en la otra Zona de Disponibilidad con Zero Downtime."*
2. **Prueba 2 — Inyectar un Mensaje Corrupto / Caída de Lambda → Dead Letter Queue (Min 3:30 – 4:15):**
   * Presionar el botón ámbar **"Inyectar Fallo Lambda → DLQ"**.
   * **Qué explicar:** *"Ahora enviamos un 'Poison Pill' que lanza una excepción fatal dentro de AWS Lambda. En vez de colgar al usuario o bloquear la cola en un ciclo infinito, Amazon SQS reintenta 2 veces y, mediante su `RedrivePolicy`, aísla automáticamente el mensaje corrupto en la **Dead Letter Queue (DLQ)**."* Presionar **"Ver DLQ"** para mostrar el mensaje aislado mientras el resto del sistema sigue procesando logs sanos.
3. **Prueba 3 — Ráfaga Masiva Concurrente (Min 4:15 – 5:00):**
   * Presionar el botón verde **"Lanzar Ráfaga (30 Eventos)"**.
   * Mostrar cómo SQS acepta los 30 eventos en menos de 200 ms con **0% pérdida de paquetes** y Lambda los drena en segundo plano.

---

## Parte 2: Explicación Técnica (3 a 5 Minutos)

### 1. Recorrido por el Diagrama de Arquitectura (1.5 min)
* Explicar la separación en **3 capas desacopladas**:
  1. **Capa Web Multi-AZ Activo-Activo:** `Application Load Balancer` → `2x EC2 t3.micro (Stateless)` en `us-east-1a` y `us-east-1b`. Ningún dato se guarda en el disco local de EC2; por eso, incluso si el laboratorio escolar congela o elimina una instancia, no se pierde información.
  2. **Capa de Ingesta y Evaluación Asíncrona:** `Amazon SQS` (amortiguador de picos) + `Dead Letter Queue` (aislamiento de fallos) → `AWS Lambda` (evaluador serverless) → `Amazon SNS` (alertas por correo).
  3. **Capa de Persistencia Serverless:** `Amazon DynamoDB` (3 tablas *On-Demand* con latencia < 10 ms para consultas en caliente) + `Amazon S3` (archivo auditable de logs JSON con durabilidad de 11 nueves).

### 2. Justificación de Decisiones: Ventajas y Desventajas (1.5 min)
* **¿Por qué DynamoDB + S3 en lugar de RDS o disco local?**
  * *Ventaja:* Escalabilidad serverless instantánea, cero mantenimiento de conexiones y persistencia intacta aunque las instancias EC2 se apaguen al cerrarse el laboratorio.
  * *Desventaja:* No soporta `JOINs` SQL complejos (se resuelve estructurando claves de partición por `service_id`, `incident_id` y `metric_id`).
* **¿Por qué SQS + Lambda en lugar de procesar todo dentro de EC2?**
  * *Ventaja:* Desacoplamiento total; la API responde `202 Accepted` en milisegundos y nunca pierde eventos bajo picos de tráfico gracias al patrón *Queue-Based Load Leveling* y la *Dead Letter Queue*.
  * *Desventaja:* Consistencia eventual de ~1–2 segundos entre la recepción del log y su aparición en el dashboard.

### 3. Análisis de Costos a 1 Año Fuera de la Capa Gratuita (1 min)
* Presentar el resumen de la tabla financiera para **1.5 millones de eventos mensuales operando 24/7 (730 h/mes)**:
  * **Cómputo y Balanceo 24/7 (ALB + 2x EC2 `t3.micro`):** \$35.81 USD/mes (\$429.72 USD/año).
  * **Capa Serverless Completa (DynamoDB + S3 + SQS + Lambda + SNS):** Solo \$16.02 USD/mes (\$192.24 USD/año).
  * **Costo Total Anual Estimado:** **\$621.96 USD al año (\$51.83 USD/mes)**, demostrando una arquitectura empresarial de alta disponibilidad a una fracción del costo de servidores dedicados tradicionales.

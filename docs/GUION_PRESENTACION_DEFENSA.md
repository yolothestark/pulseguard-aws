# Guion Paso a Paso Explicado (Palabra por Palabra) para Grabar el Video
**Proyecto:** PulseGuard Cloud — Monitoreo Distribuido, Logs e Incidentes en AWS  
**Equipo:** Anguiano Garcia Angel Yahir Guadalupe · Figueroa Robles Axel Israel · Torres Martinez Miguel Angel  

---

> ### Antes de Empezar a Grabar (Deja estas 3 ventanas abiertas en tu computadora):
> 1. **La Terminal abierta:** Dale doble clic a `ABRIR_TERMINAL_PARA_VIDEO.bat` dentro de tu carpeta `Descargas\pulseguard-aws`.
> 2. **Tu Navegador Web con 2 pestañas:**
>    * **Pestaña 1 (Tu App en AWS):** http://pulseguard-alb-388362639.us-east-1.elb.amazonaws.com
>    * **Pestaña 2 (Tu GitHub):** https://github.com/yolothestark/pulseguard-aws
> 3. **Tu PDF abierto:** Abre `Descargas\pulseguard-aws\docs\DOCUMENTACION_PROYECTO_PULSEGUARD.pdf`.

---

## PARTE 1: Introducción y Demostración de la Regla 1 (Cero Clics en Consola)
*(Duración aproximada: 2 minutos)*

### Paso 1: Qué es el proyecto y qué problema resuelve
* **¿Qué muestras en pantalla?:** Empieza mostrando la pantalla principal de la aplicación web (**http://pulseguard-alb-388362639.us-east-1.elb.amazonaws.com**) o la portada de tu PDF.
* **¿Qué estás haciendo y por qué?:** Le estás presentando al profesor de qué trata la aplicación web para que entienda que no es una página simple, sino un sistema empresarial completo (Reglas 3 y 4).
* **LO QUE DICES EN EL VIDEO (Léelo con naturalidad):**
  > *"Hola profesor, nosotros somos el equipo conformado por Angel Yahir Anguiano Garcia, Axel Israel Figueroa Robles y Miguel Angel Torres Martinez. Nuestro proyecto libre de AWS se llama **PulseGuard Cloud**.*
  >
  > *¿Qué es PulseGuard Cloud y qué problema resuelve? Cuando una empresa tiene múltiples servicios en producción —como una pasarela de pagos, un servidor de inicio de sesión o un procesador de pedidos—, necesita saber en tiempo real si alguno de esos servicios se pone lento, si sube demasiado su uso de procesador o si empieza a arrojar errores, para detectar incidentes automáticamente, guardar evidencia forense de los logs y alertar por correo a los ingenieros antes de que todo el sistema colapse. Eso es exactamente lo que hace nuestra aplicación web."*

---

### Paso 2: Demostrar la Regla 1 (Infraestructura 100% Automatizada con Script en Python)
* **¿Qué muestras en pantalla?:**
  1. Cambia a la pestaña de tu repositorio en **GitHub** (`https://github.com/yolothestark/pulseguard-aws`) y entra brevemente al archivo `infra/deploy.py` para que se vea el código.
  2. Luego cambia a la ventana negra de la **Terminal** (`ABRIR_TERMINAL_PARA_VIDEO.bat`), copia y pega este comando y dale `Enter`:
     ```powershell
     C:\Users\Yahir\.local\bin\uv.exe run --with boto3 --with requests python infra/deploy.py
     ```
* **¿Qué está haciendo ese comando por detrás en AWS?:**
  Ese script lee tus credenciales del laboratorio escolar y usa la librería oficial `boto3` de Python para conectarse directamente a la API de AWS en la región `us-east-1` (Norte de Virginia). Sin que nosotros hagamos un solo clic en la página web de AWS, el script verifica o crea 7 servicios conectados entre sí.
* **LO QUE DICES EN EL VIDEO MIENTRAS CORRE EL COMANDO EN LA TERMINAL:**
  > *"Para cumplir con la **Regla 1**, nosotros no creamos ningún recurso haciendo clics manuales en la consola web de AWS. Todo el código está en nuestro repositorio de GitHub y toda la infraestructura se construye automáticamente con nuestro script `infra/deploy.py` programado en Python con el SDK oficial `boto3`.*
  >
  > *Aquí en la terminal estamos ejecutando `deploy.py` en vivo y podemos ver paso por paso los 7 componentes que el script construye y configura automáticamente en nuestra cuenta de AWS usando el rol escolar `LabRole`:*
  > 1. *Primero, en el paso 1, crea y configura un bucket en **Amazon S3** llamado `pulseguard-logs-627739785043`, donde se van a archivar todos los logs en formato JSON, la cola de errores aislados y el paquete de código.*
  > 2. *En el paso 2, crea dos tópicos en **Amazon SNS**: uno que funciona como bus de mensajería asíncrono para recibir la telemetría sin saturar el servidor, y otro para enviar alertas por correo electrónico.*
  > 3. *En el paso 3, empaqueta en un archivo ZIP y despliega nuestra función **AWS Lambda** llamada `pulseguard-anomaly-evaluator`, y la conecta automáticamente como suscriptora del bus de SNS.*
  > 4. *En el paso 4, aprovisiona tres tablas Serverless en la base de datos NoSQL **Amazon DynamoDB** (`pulseguard-services`, `pulseguard-incidents` y `pulseguard-metrics`) y les precarga el catálogo inicial de microservicios.*
  > 5. *En el paso 5 y 6, crea los **Security Groups** (el firewall de la red VPC), crea un **Target Group** que revisa la salud de los servidores cada 10 segundos en la ruta `/api/health`, y despliega un **Application Load Balancer (ALB)** público frente a internet.*
  > 6. *Finalmente, en el paso 7, lanza **dos instancias Amazon EC2 `t3.micro`** ubicadas en dos Zonas de Disponibilidad distintas (`us-east-1a` y `us-east-1b`), les inyecta un script de arranque `UserData` que descarga nuestra aplicación FastAPI desde S3, la activa como servicio del sistema operativo y nos entrega al final la URL pública del Load Balancer lista para usarse."*

---

## PARTE 2: Demostración en Vivo de la Aplicación Web Funcionando
*(Duración aproximada: 1.5 minutos)*

### Paso 3: Explicar la pantalla principal y el Balanceo de Carga entre las 2 instancias EC2
* **¿Qué muestras en pantalla?:** Regresa al navegador en la pestaña de la aplicación web (**http://pulseguard-alb-388362639.us-east-1.elb.amazonaws.com**).
  * Señala con el mouse el recuadro de arriba a la derecha que dice **"Nodo EC2 Respondiendo (ALB)"**.
  * Dale clic 2 o 3 veces al botón **"Actualizar Ahora"** que está al lado derecho para que se vea cómo el ID del nodo cambia entre las dos instancias EC2 (`i-090f6ec7bd6218ebb` e `i-0fb4238d7d40beb66`).
* **¿Qué está pasando por detrás?:** Cada vez que la página consulta `/api/overview`, el **Application Load Balancer** de AWS reparte la petición (Round-Robin) entre el Servidor EC2 #1 (en la zona `us-east-1a`) y el Servidor EC2 #2 (en la zona `us-east-1b`). El servidor que contesta lee sus propios metadatos internos de AWS y le dice a la página: *"Te estoy contestando yo"*.
* **LO QUE DICES EN EL VIDEO:**
  > *"Al abrir la URL pública que nos dio el Application Load Balancer, entramos a la interfaz web de **PulseGuard Cloud**.*
  >
  > *Lo primero que queremos destacar está arriba a la derecha, en el indicador **'Nodo EC2 Respondiendo (ALB)'** y en la sección inferior **'Clúster de Servidores Web EC2'**. Si observamos mientras la página se actualiza cada 2.5 segundos —o al presionar 'Actualizar Ahora'—, vemos cómo el identificador del servidor cambia dinámicamente entre nuestras dos instancias EC2 reales desplegadas en distintas Zonas de Disponibilidad (`us-east-1a` y `us-east-1b`). Esto comprueba en vivo que el Application Load Balancer está distribuyendo la carga entre ambos servidores.*
  >
  > *Más abajo tenemos las tarjetas con los indicadores clave en tiempo real leídos desde **Amazon DynamoDB** y **Amazon S3**: cuántos microservicios estamos monitoreando, cuántos están saludables o degradados, cuántos incidentes están abiertos, la latencia promedio en milisegundos y cuántos archivos de auditoría llevamos guardados en el bucket de S3."*

---

### Paso 4: Registrar un servicio, enviar un Log Crítico y ver cómo reaccionan SNS, Lambda, DynamoDB y S3
* **¿Qué haces en pantalla paso por paso?:**
  1. Baja a la sección **"Stream de Telemetría y Auditoría en Amazon S3"** y dale clic al botón **"+ Enviar Log / Métrica Manual"**.
  2. Se abre una ventana emergente. Déjala con los valores críticos que ya trae por defecto (`Latencia: 1850 ms`, `Código HTTP: 503`, `Uso CPU: 93%`, `Nivel de Log: CRITICAL`) y dale clic al botón azul **"Encolar en Amazon SQS / Bus Asíncrono"**.
  3. Espera 2 segundos: verás que el servicio cambia a estado rojo **`DOWN`**, en la columna derecha (**Centro de Incidentes**) aparece un nuevo incidente rojo **`OPEN · CRITICAL`**, y en la tabla inferior aparece el nuevo registro con un botón azul que dice **`JSON S3`**.
  4. Dale clic a ese botón azul **`JSON S3`**: se abrirá una nueva pestaña en tu navegador mostrando el archivo JSON descargado directamente desde los servidores de **Amazon S3** (`s3.amazonaws.com`).
  5. Regresa a la pestaña de PulseGuard y en el incidente rojo de la derecha dale clic al botón verde **"Mitigar / Resolver"** para que vean cómo pasa a **`Resuelto`** y el servicio vuelve a estado verde **`HEALTHY`**.
* **¿Qué está pasando por detrás en AWS durante estos clics?:**
  1. Tu navegador manda el log al servidor **EC2**.
  2. El servidor EC2 lo publica en el tópico de **Amazon SNS (`pulseguard-telemetry-stream`)** para que se procese de forma asíncrona sin trabar al usuario.
  3. **Amazon SNS** dispara automáticamente la función **AWS Lambda (`pulseguard-anomaly-evaluator`)**.
  4. **AWS Lambda** analiza los números: como ve que `HTTP 503` es un error de servidor y la latencia de `1850 ms` supera el límite permitido de `1500 ms`, hace 4 cosas automáticamente:
     * Guarda una copia completa del log en un archivo `.json` dentro del bucket de **Amazon S3**.
     * Registra la métrica en la tabla `pulseguard-metrics` de **DynamoDB**.
     * Marca el servicio como caído (`DOWN`) en la tabla `pulseguard-services` de **DynamoDB**.
     * Crea una alerta en la tabla `pulseguard-incidents` de **DynamoDB** y envía un correo electrónico mediante el tópico de alertas de **Amazon SNS**.
  5. Cuando le das clic a **`JSON S3`**, el backend usa `boto3` para generar una **URL Pre-firmada (*Presigned URL*) de Amazon S3** con validez temporal de 15 minutos, permitiendo descargar la evidencia directamente desde S3 de forma segura.
* **LO QUE DICES EN EL VIDEO MIENTRAS HACES ESOS CLICS:**
  > *"Ahora vamos a demostrar el flujo completo de datos entre los servicios de AWS enviando un evento de telemetría crítico.*
  >
  > *Hacemos clic en **'+ Enviar Log / Métrica Manual'**. Aquí simulamos que uno de nuestros microservicios reporta una latencia crítica de 1850 milisegundos, un error HTTP 503 y un uso de CPU del 93%. Al enviarlo, ¿qué ocurre por detrás en AWS?*
  >
  > *La instancia EC2 recibe la petición y la publica de inmediato en nuestro bus asíncrono de **Amazon SNS**, respondiendo al instante sin bloquear al usuario. Ese bus despierta automáticamente a nuestra función Serverless **AWS Lambda**. Lambda evalúa las reglas de negocio, detecta que los umbrales fueron superados y realiza cuatro acciones en paralelo:*
  > 1. *Actualiza el estado del servicio a caído (`DOWN`) en la tabla de servicios de **Amazon DynamoDB**.*
  > 2. *Registra la métrica en la tabla de telemetría de **DynamoDB**.*
  > 3. *Abre automáticamente este nuevo incidente crítico que vemos aquí a la derecha en el **Centro de Incidentes** y dispara la notificación por correo a través de **Amazon SNS**.*
  > 4. *Y guarda el documento original de auditoría en nuestro bucket de **Amazon S3**. Si hacemos clic aquí en el botón **`JSON S3`**, el servidor genera una URL Pre-firmada (*Presigned URL*) de S3 y podemos ver el archivo JSON crudo descargado directamente desde Amazon S3.*
  >
  > *Además, desde el Centro de Incidentes podemos gestionar la falla: si presionamos el botón verde **'Mitigar / Resolver'**, se actualiza el registro en DynamoDB y el servicio vuelve a estado saludable (`HEALTHY`)."*

---

## PARTE 3: Demostración en Vivo de la Regla 2 — Pruebas de Resiliencia ("Demuéstrame que no se rompe")
*(Duración aproximada: 2 minutos)*

### Paso 5: Ejecutar las 3 Pruebas de Resiliencia desde el Panel de Chaos Engineering
* **¿Qué muestras en pantalla?:** Enfoca el recuadro central con borde amarillo titulado **"Regla 2: Chaos Engineering en Vivo — Simulador de Pruebas de Resiliencia y Tolerancia a Fallos"**.

#### 5.1 Escenario 1: Simular la Caída de un Servidor Web EC2 (Alta Disponibilidad con ALB)
* **¿Qué haces?:**
  1. Presiona el botón rojo **"Derribar Nodo EC2 Actual (75s)"**.
  2. Aparecerá un recuadro negro abajo confirmando qué instancia EC2 fue derribada.
  3. Señala cómo la página **sigue funcionando perfectamente**, las gráficas/tablas siguen cargando y en la sección **"Clúster de Servidores Web EC2"** todo el tráfico ahora es atendido por la otra instancia EC2 sana.
* **LO QUE DICES EN EL VIDEO:**
  > *"Para cumplir con la **Regla 2 (Pruebas de Resiliencia: 'Demuéstrame que no se rompe')**, integramos este panel de Ingeniería del Caos directamente en la aplicación para provocar fallos reales en vivo.*
  >
  > *En el **Escenario 1**, vamos a simular que uno de nuestros servidores web EC2 sufre una caída crítica presionando el botón rojo **'Derribar Nodo EC2 Actual'**. En este momento, esa instancia EC2 empieza a devolver error `HTTP 503 Service Unavailable` en su chequeo de salud `/api/health`.*
  >
  > *¿Qué pasaría en un proyecto tradicional con un solo servidor? Toda la página web dejaría de funcionar. Pero como nosotros pusimos un **Application Load Balancer** frente a dos instancias EC2 en distintas Zonas de Disponibilidad, y nuestras instancias son **100% Stateless** (no guardan nada en su disco local porque todo vive en DynamoDB y S3), el Load Balancer detecta el nodo caído y redirige automáticamente el 100% de nuestras peticiones al segundo servidor EC2 sobreviviente. Como pueden ver, puedo seguir usando y recargando la aplicación con **cero tiempo de caída (Zero Downtime)**."*
  *(Opcional: después de mostrarlo 15 segundos, puedes darle clic al botón gris **"Restaurar"** al lado del botón rojo para devolver el nodo a la normalidad).*

#### 5.2 Escenario 2: Inyectar un Mensaje Corrupto / Fallo en AWS Lambda (Dead Letter Queue)
* **¿Qué haces?:**
  1. En la tarjeta de en medio (*Escenario 2*), presiona el botón ámbar **"Inyectar Fallo Lambda → DLQ"**.
  2. Espera 3 segundos y presiona el botón gris **"Ver DLQ"** que está justo al lado.
  3. En el recuadro negro inferior se mostrará el contenido de la **Dead Letter Queue (`s3://pulseguard-logs-627739785043/dlq/`)** con el mensaje corrupto que fue puesto en cuarentena (`receive_count: 2 (Max Retries Exhausted)`).
* **LO QUE DICES EN EL VIDEO:**
  > *"En el **Escenario 2**, probamos qué pasa si llega un mensaje corrupto —conocido como 'Poison Pill'— que provoca que el código de nuestra función **AWS Lambda** truene con una excepción fatal (`RuntimeError`).*
  >
  > *Al presionar **'Inyectar Fallo Lambda → DLQ'**, enviamos ese payload defectuoso. Si el sistema fuera síncrono o no tuviera manejo de errores, ese mensaje fallido bloquearía el procesador en un ciclo infinito impidiendo que se procesen los demás logs. En nuestra arquitectura, tras agotar sus dos reintentos automáticos, Lambda captura el fallo y aísla el mensaje defectuoso dentro de nuestra **Dead Letter Queue (DLQ)** respaldada en Amazon S3. Si hacemos clic en **'Ver DLQ'**, aquí vemos el mensaje corrupto aislado en cuarentena con el motivo exacto del error para que un ingeniero lo audite después, mientras que la tarjeta superior de 'Dead Letter Queue' subió su contador y el resto del sistema sigue procesando eventos sanos sin interrupción."*

#### 5.3 Escenario 3: Ráfaga Masiva Concurrente (Prueba de Estrés)
* **¿Qué haces?:**
  1. En la tercera tarjeta (*Escenario 3*), presiona el botón verde **"Lanzar Ráfaga (30 Eventos)"**.
  2. Señala el resultado en el recuadro negro inferior (`requested_events: 30`, `accepted_events: 30`, `packet_loss_pct: 0`) y cómo subió el contador de **"Logs en S3"** en la barra superior.
* **LO QUE DICES EN EL VIDEO:**
  > *"Por último, en el **Escenario 3**, ejecutamos una prueba de estrés presionando **'Lanzar Ráfaga (30 Eventos)'**. Esto bombardea la arquitectura con 30 eventos de telemetría concurrentes más un pico crítico al mismo tiempo. Como vemos en el reporte en pantalla, gracias al desacoplamiento asíncrono con AWS Lambda, los 30 eventos fueron aceptados en menos de un segundo con **0% de pérdida de paquetes (`packet_loss_pct: 0`)**, y todos quedaron procesados y archivados en DynamoDB y S3 sin saturar la memoria de las instancias EC2."*

---

## PARTE 4: Explicación Técnica Recorriendo el PDF (3 a 4 Minutos)
*(Cambia ahora a la ventana donde tienes abierto tu archivo **`DOCUMENTACION_PROYECTO_PULSEGUARD.pdf`**)*

### Paso 6: Explicar el Diagrama de Arquitectura (Página 1 del PDF)
* **¿Qué muestras en pantalla?:** Haz zoom al **Diagrama de Bloques de color azul oscuro** que está en la parte inferior de la **Página 1** del PDF. Ve señalando con el cursor del mouse cada bloque de izquierda a derecha mientras hablas.
* **LO QUE DICES EN EL VIDEO:**
  > *"Pasando a la explicación técnica en nuestra documentación PDF, aquí en la Página 1 tenemos nuestro **Diagrama de Arquitectura** dividido en capas:*
  > 1. *A la izquierda tenemos los **Clientes y Microservicios**, que envían tráfico HTTP por el puerto 80 hacia nuestro **Application Load Balancer (ALB)**.*
  > 2. *Al centro arriba tenemos nuestra **Capa de Cómputo de Alta Disponibilidad en la VPC (`us-east-1`)**, compuesta por el **Nodo EC2 1 en `us-east-1a`** y el **Nodo EC2 2 en `us-east-1b`**. Ambos corren nuestro servidor FastAPI en instancias `t3.micro` bajo el perfil `LabInstanceProfile`.*
  > 3. *A la derecha arriba tenemos el **Bus de Amazon SNS**, que desacopla la recepción de logs del procesamiento pesado y además gestiona el envío de correos de alerta.*
  > 4. *Abajo a la derecha está el motor Serverless **AWS Lambda (`pulseguard-anomaly-evaluator`)**, que recibe los eventos desde SNS, evalúa si hay anomalías de latencia, CPU o errores HTTP, y si un mensaje viene corrupto lo desvía hacia la **Dead Letter Queue**.*
  > 5. *Finalmente, abajo al centro y a la izquierda tenemos nuestra **Capa de Persistencia Serverless**: las **3 tablas de Amazon DynamoDB** (`services`, `metrics` e `incidents`) en modo bajo demanda para consultas rápidas en milisegundos, y el bucket de **Amazon S3** para el almacenamiento histórico auditable de archivos JSON."*

---

### Paso 7: Explicar la Justificación de Decisiones — Ventajas y Desventajas (Página 2 del PDF)
* **¿Qué muestras en pantalla?:** Baja a la **Página 2** del PDF y señala la **Sección 4: Justificación de Decisiones Arquitectónicas (tabla azul)**.
* **LO QUE DICES EN EL VIDEO:**
  > *"En la Sección 4 de la Página 2 justificamos por qué elegimos estos servicios de AWS frente a otras alternativas, junto con sus ventajas y desventajas:*
  > * **Primero, ¿por qué elegimos un Application Load Balancer con 2 instancias EC2 pequeñas (`t3.micro`) en vez de una sola instancia EC2 grande?** Porque un solo servidor, por grande que sea, es un Punto Único de Fallo: si se cae esa máquina o esa zona, se cae todo el sistema. Con 2 instancias en distintas zonas detrás de un Load Balancer logramos alta disponibilidad real sin tiempo de caída. La única desventaja es el costo fijo por hora del Load Balancer.*
  > * **Segundo, ¿por qué elegimos Amazon DynamoDB en lugar de una base de datos relacional tradicional como Amazon RDS?** Porque para monitoreo de telemetría necesitamos escrituras ultra rápidas en menos de 10 milisegundos y escalabilidad automática sin administrar conexiones. Además, en un laboratorio educativo que apaga servidores cada 4 horas, DynamoDB al ser Serverless nunca se apaga ni pierde datos, y no cobra por hora cuando no hay tráfico. Su desventaja es que no permite hacer consultas SQL con `JOINs` complejos.*
  > * **Tercero, ¿por qué usamos procesamiento asíncrono con SNS, AWS Lambda y una Dead Letter Queue en lugar de procesar todo directamente dentro de EC2?** La ventaja es que la página web responde al instante (`HTTP 202`), soporta ráfagas masivas de tráfico sin colapsar y aísla errores en la DLQ. El trade-off o desventaja es la consistencia eventual, ya que el log tarda entre 1 y 2 segundos en procesarse en segundo plano.*
  > * **Y cuarto, ¿por qué guardamos los logs en Amazon S3 con URLs Pre-firmadas en lugar del disco duro local EBS de cada EC2?** Porque si guardáramos un archivo en el disco local del Servidor EC2 #1, el Servidor EC2 #2 no podría verlo, y si una instancia se elimina se perderían los archivos. Con Amazon S3 tenemos una durabilidad del 99.999999999% (11 nueves) accesible desde cualquier nodo."*

---

### Paso 8: Explicar el Análisis de Costos a 1 Año Fuera de la Capa Gratuita (Página 2 del PDF)
* **¿Qué muestras en pantalla?:** Señala la última tabla de la **Página 2** del PDF (**Sección 5: Análisis de Costos**).
* **LO QUE DICES EN EL VIDEO (Cierre del video):**
  > *"Para concluir, en la Sección 5 presentamos el **Análisis de Costos**.*
  >
  > *Durante el desarrollo y nuestras pruebas en el laboratorio escolar, el consumo real por sesión fue menor a **9 centavos de dólar (\$0.09 USD)** del crédito académico, gracias a que DynamoDB, S3, Lambda y SNS solo cobran por petición y contamos con el script `infra/destroy.py` para apagar el Load Balancer y las instancias EC2 al terminar de trabajar.*
  >
  > *También calculamos cuánto costaría mantener **PulseGuard Cloud** en producción real para una empresa fuera de la capa gratuita de AWS durante **1 año completo (operando 24/7, las 730 horas del mes en la región `us-east-1`)**, monitoreando 25 microservicios que generen 1.5 millones de eventos mensuales:*
  > * Mantener encendidas las **2 instancias EC2 `t3.micro`** con sus discos EBS cuesta **\$16.78 dólares al mes (\$201.36 USD al año)**.*
  > * El **Application Load Balancer** activo las 24 horas cuesta **\$19.35 dólares al mes (\$232.20 USD al año)**.*
  > * Y toda nuestra capa **Serverless** completa —incluyendo 3 millones de escrituras y 6 millones de lecturas en **DynamoDB** (\$6.50/mes), 15 GB y 1.5 millones de archivos en **Amazon S3** (\$7.97/mes), 300 mil invocaciones de **AWS Lambda** (\$0.31/mes) y 1.5 millones de eventos en **Amazon SNS** (\$0.79/mes)— suma apenas **\$15.57 dólares al mes**.*
  > * En total, mantener toda esta arquitectura empresarial de alta disponibilidad operando las 24 horas cuesta **\$51.70 dólares al mes**, lo que equivale a un costo anual de **\$620.40 dólares al año** fuera de la capa gratuita.*
  >
  > *Con esto concluimos la demostración en vivo y la defensa técnica de **PulseGuard Cloud**. Muchas gracias."*

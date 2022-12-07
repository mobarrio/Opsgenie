# Opsgenie
Conexion a Opsgenie via API para tareas de administración tanto en Opsgenie como en Zabbix (DELETE Alerts, Hosts, etc)

# Docker Compose para RabbitMQ
**# vi docker-compose.yml**
```
services:
    rabbitmq:
        image: rabbitmq:management-alpine
        container_name: rabbitmq
        ports:
            - 5672:5672
            - 15672:15672
```

**# docker-compose up -d**

# Start
```
 [root]# ./cleanAlertsWaiting.py 
 [*] Waiting for messages. To exit press CTRL+C

```

```
# ./cleanAlerts.py -h
usage: cleanAlerts.py [-h] [-f FROM] [-t TO] [--Delete | --no-Delete] [--Close | --no-Close] [--List | --no-List]

optional arguments:
  -h, --help            show this help message and exit
  -f FROM, --From FROM  Fecha desde Ej. 2022-12-05 10:00:00
  -t TO, --To TO        Fecha hasta Ej. 2022-12-05 11:00:00
  --Delete, --no-Delete
                        Elimina las alertas que cumplen la consulta (default: False)
  --Close, --no-Close   Cierra las alertas que cumplen la consulta (default: False)
  --List, --no-List     Lista las alertas que cumplen la consulta (default: True)
```

## Ejemplos
```
 # ./cleanAlerts.py -t "2022-12-07 15:00:00" --Delete
 # ./cleanAlerts.py -t "2022-12-07 15:00:00" --Close
 # ./cleanAlerts.py -t "2022-12-07 15:00:00" --List

```

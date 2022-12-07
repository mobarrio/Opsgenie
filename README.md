# Opsgenie
Conexion a Opsgenie via API para tareas de administración tanto en Opsgenie como en Zabbix (DELETE Alerts, Hosts, etc)

# Docker Compose para RabbitMQ
```
**# vi docker-compose.yml**
services:
    rabbitmq:
        image: rabbitmq:management-alpine
        container_name: rabbitmq
        ports:
            - 5672:5672
            - 15672:15672

**# docker-compose up -d**
```

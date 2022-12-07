# Opsgenie
Conexion a Opsgenie via API para tareas de administración tanto en Opsgenie como en Zabbix (DELETE Alerts, Hosts, etc)

# Opsgenie Daemon Start
```
# docker-compose up --build
# docker-compose -f docker-compose-precompiles.yml up 
```

# Opsgenie Client
## Create virtual environment
```
python3.9 -m venv pyzabbix
cd pyzabbix
source bin/activate
python -m pip install --upgrade pip
cp ../requirements.txt .
cp ../opsgenie-client.py .
cp ../.env .
pip install -r requirements.txt
```

## OPSGENIE-CLIENT USAGE
```
# ./opsgenie-client.py -h
usage: opsgenie-client.py [-h] [-f FROM] [-t TO] [--Delete | --no-Delete] [--Close | --no-Close] [--List | --no-List]

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
./opsgenie-client.py -t "2022-12-07 15:00:00" --List
./opsgenie-client.py -t "2022-12-07 15:00:00" --Close
./opsgenie-client.py -t "2022-12-07 15:00:00" --Delete
```


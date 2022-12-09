#!/usr/bin/env python

import sys
import os
import logging
import argparse
import time
import datetime
import opsgenie_sdk
import pika
import json
from datetime import timezone, datetime, timedelta
from dateutil import tz
from distutils.util import strtobool
from pprint import pprint
from opsgenie_sdk.rest import ApiException
from dotenv import load_dotenv
load_dotenv(".env")

DEBUG = bool(strtobool(os.environ.get('DEBUG','False')))
DEBUG = True
tzone = tz.gettz('Europe/Madrid')
nListed = 0

if(DEBUG):
  stream = logging.StreamHandler(sys.stdout)
  stream.setLevel(logging.DEBUG)
  log = logging.getLogger('pyzabbix')
  log.addHandler(stream)
  log.setLevel(logging.DEBUG)

# Configure OPS connection
configuration = opsgenie_sdk.Configuration()
configuration.api_key['Authorization'] = os.environ.get('OPSGENIE_API_KEY')
configuration.host = os.environ.get('OPSGENIE_API_URL')
opsapi = opsgenie_sdk.AlertApi(opsgenie_sdk.ApiClient(configuration))
identifier_type = 'id'
close_alert_payload = opsgenie_sdk.CloseAlertPayload(source=os.environ.get('OPSGENIE_CLOSER_SOURCE'), user=os.environ.get('OPSGENIE_CLOSER_USER'), note=os.environ.get('OPSGENIE_CLOSER_NOTE'))

def ops_publish_identifier(queue,message):
    credentials = pika.PlainCredentials(os.environ.get('RABBITMQ_DEFAULT_USERNAME'), os.environ.get('RABBITMQ_DEFAULT_PASSWORD'))
    config      = pika.ConnectionParameters(host=os.environ.get('RABBITMQ_DEFAULT_SERVER'), port=os.environ.get('RABBITMQ_DEFAULT_PORT'), credentials=credentials)
    connection  = pika.BlockingConnection(config)
    props       = pika.BasicProperties(delivery_mode = 2)
    channel     = connection.channel()
    channel.queue_declare(queue=queue,
                          durable=True)
    channel.basic_publish(exchange='',
                          routing_key=queue,
                          body=json.dumps(message),
                          properties=props)
    connection.close()

def ops_CloseAlerts(identifier,date,msg):
   try:
      print(date, ' - ', identifier, ' - ', msg, ' - Closed.')
      api_response = opsapi.close_alert(identifier,identifier_type=identifier_type,close_alert_payload=close_alert_payload)
   except Exception as e:
      print(str(e))

def ops_DeleteAlerts(identifier,date,msg):
   try:
      print(date, ' - ', identifier, ' - ', msg, ' - Deleted.')
      api_response = opsapi.delete_alert(identifier, identifier_type=identifier_type, user=os.environ.get('OPSGENIE_CLOSER_USER'), source=os.environ.get('OPSGENIE_CLOSER_SOURCE'))
   except Exception as e:
      print(str(e))

def ops_CountAlets(QueryString):
   api_response = opsapi.count_alerts(query=QueryString)
   return(api_response.data.count)

def ops_DoWork(offset,QueryString,Option):
   try:
      alerts = opsapi.list_alerts(limit=100, offset=offset, sort='updatedAt', order='asc', query=QueryString)
      global nListed
      for alert in alerts.data:
        nListed += 1
        created_at = alert.created_at.astimezone(tzone).strftime("%Y-%m-%d %H:%M:%S")
        if Option == 'Close':
           ops_publish_identifier('opsgenie',{'created_at': created_at, 'id':alert.id, 'message': alert.message,'action':'Close'})
        elif Option == 'Delete':
           ops_publish_identifier('opsgenie',{'created_at': created_at, 'id':alert.id, 'message': alert.message,'action':'Delete'})
        elif Option == 'List':
           print("%s - [%08d] - %s - %s" % (created_at,nListed,alert.id,alert.message))
        else:
           print(parser.print_help())

   except Exception as e:
      print(str(e))

parser = argparse.ArgumentParser("opsgenie-client.py")
parser.add_argument('-f', '--From', help="Fecha desde Ej. 2022-12-05 10:00:00", type=str)
parser.add_argument('-t', '--To', help="Fecha hasta Ej. 2022-12-05 11:00:00", type=str)
parser.add_argument('--Delete', help="Elimina las alertas que cumplen la consulta", default=False, action=argparse.BooleanOptionalAction)
parser.add_argument('--Close', help="Cierra las alertas que cumplen la consulta", default=False, action=argparse.BooleanOptionalAction)
parser.add_argument('--List', help="Lista las alertas que cumplen la consulta", default=True, action=argparse.BooleanOptionalAction)
parser.add_argument('--Count', help="Muestra el numero de alertas en el sistema (Abiertas y Cerradas)", default=False, action=argparse.BooleanOptionalAction)
args = parser.parse_args()

try:
   if not (args.From or args.To or args.List):
      print(parser.print_help())
   else:
      query = ""
      if args.From:
         desde = int(datetime.strptime(args.From, '%Y-%m-%d %H:%M:%S').timestamp())
         if query:
            query += ' and createdAt>='+str(desde)
         else:
            query = 'createdAt>='+str(desde)

      if args.To:
         hasta = int(datetime.strptime(args.To, '%Y-%m-%d %H:%M:%S').timestamp())
         if query:
            query += ' and createdAt<='+str(hasta)
         else:
            query = 'createdAt<='+str(hasta)
      else:
         hasta = int(datetime.now().timestamp())
         query = 'createdAt<'+str(hasta)

      countAlerts = ops_CountAlets(query)
      if args.Count:
         countAlertsOpen = ops_CountAlets("status=open")
         countAlertsClosed = ops_CountAlets("status=closed")
         print(json.dumps({"Total": countAlerts, "Open":countAlertsOpen, "Closed":countAlertsClosed}))
      else:
         max = int(round(countAlerts/100))+1
         #print("Query : [",query,"] Records: [",countAlerts,"] Iteracciones: [",max,"]")
         print("Procesando",countAlerts,"registros.")
         for i in range(0,max+1):
            offset=(((max-i)*100))
            if args.Close:
               ops_DoWork(offset,query,'Close')
            elif args.Delete:
               ops_DoWork(offset,query,'Delete')
            elif args.List:
               ops_DoWork(offset,query,'List')
         print(countAlerts,"registros procesados.")
except Exception as e:
   print({"Status": e})

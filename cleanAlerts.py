#!/usr/lib/zabbix/externalscripts/pyzabbix/bin/python

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
load_dotenv("/usr/lib/zabbix/externalscripts/pyzabbix/.env")

DEBUG = bool(strtobool(os.environ.get('DEBUG','False')))
tzone = tz.gettz('Europe/Madrid')

if(DEBUG):
  stream = logging.StreamHandler(sys.stdout)
  stream.setLevel(logging.DEBUG)
  log = logging.getLogger('pyzabbix')
  log.addHandler(stream)
  log.setLevel(logging.DEBUG)

# Configure OPS connection
configuration = opsgenie_sdk.Configuration()
configuration.api_key['Authorization'] = os.environ.get('ops_api_key')
configuration.host = os.environ.get('ops_api_url')
opsapi = opsgenie_sdk.AlertApi(opsgenie_sdk.ApiClient(configuration))
identifier_type = 'id'
close_alert_payload = opsgenie_sdk.CloseAlertPayload(source=os.environ.get('ops_closer_source'), user=os.environ.get('ops_closer_user'), note=os.environ.get('ops_closer_note'))

def ops_publish_identifier(queue,message):
    credentials = pika.PlainCredentials(os.environ.get('rmq_username'), os.environ.get('rmq_password'))
    config      = pika.ConnectionParameters(host=os.environ.get('rmq_server'), port=os.environ.get('rmq_port'), credentials=credentials)
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
      api_response = opsapi.delete_alert(identifier, identifier_type=identifier_type, user=os.environ.get('ops_closer_user'), source=os.environ.get('ops_closer_source'))
   except Exception as e:
      print(str(e))

def ops_CountAlets(QueryString):
   api_response = opsapi.count_alerts(query=QueryString)
   return(api_response.data.count)

def ops_ListAlerts(offset,QueryString,Option):
   try:
      alerts = opsapi.list_alerts(limit=100, offset=offset, sort='updatedAt', order='asc', query=QueryString)
      for alert in alerts.data:
        created_at = alert.created_at.astimezone(tzone).strftime("%Y-%m-%d %H:%M:%S")
        # print(created_at, ' - ',alert.id, ' - ', alert.message)
        if Option == 'Close':
           #ops_CloseAlerts(alert.id,alert.created_at,alert.message)
           ops_publish_identifier('opsgenie',{'created_at': created_at, 'id':alert.id, 'message': alert.message,'action':'Close'})
        elif Option == 'Delete':
           #ops_DeleteAlerts(alert.id,alert.created_at,alert.message)
           ops_publish_identifier('opsgenie',{'created_at': created_at, 'id':alert.id, 'message': alert.message,'action':'Delete'})
        elif Option == 'List':
           print(created_at, ' - ',alert.id, ' - ', alert.message)
        else:
           print(parser.print_help())

   except Exception as e:
      print(str(e))

parser = argparse.ArgumentParser("cleanAlerts.py")
parser.add_argument('-f', '--From', help="Fecha desde Ej. 2022-12-05 10:00:00", type=str)
parser.add_argument('-t', '--To', help="Fecha hasta Ej. 2022-12-05 11:00:00", type=str)
parser.add_argument('--Delete', help="Elimina las alertas que cumplen la consulta", default=False, action=argparse.BooleanOptionalAction)
parser.add_argument('--Close', help="Cierra las alertas que cumplen la consulta", default=False, action=argparse.BooleanOptionalAction)
parser.add_argument('--List', help="Lista las alertas que cumplen la consulta", default=True, action=argparse.BooleanOptionalAction)
args = parser.parse_args()

try:
   if not (args.From or args.To or args.List):
      print(parser.print_help())
   else:
      query = ""
      if args.From:
         desde = datetime.strptime(args.From, '%Y-%m-%d %H:%M:%S').strftime('%s')
         if query:
            query += ' and createdAt>='+desde
         else:
            query = 'createdAt>='+desde

      if args.To:
         hasta = datetime.strptime(args.To, '%Y-%m-%d %H:%M:%S').strftime('%s')
         if query:
            query += ' and createdAt<='+hasta
         else:
            query = 'createdAt<='+hasta
      else:
         hasta = datetime.now().strftime('%s')
         query = 'createdAt<'+hasta

      print("Procesando [",ops_CountAlets(query),"] registros")
      max = int(round(ops_CountAlets(query)/100))+1
      for i in range(0,max+1):
         offset=(((max-i)*100))
         if args.Close:
            ops_ListAlerts(offset,query,'Close')
         elif args.Delete:
            ops_ListAlerts(offset,query,'Delete')
         elif args.List:
            ops_ListAlerts(offset,query,'List')
except Exception as e:
   print({"Status": e})

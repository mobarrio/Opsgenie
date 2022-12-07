#!/usr/local/bin/python

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
load_dotenv("/app/.env")

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

def main():
    credentials = pika.PlainCredentials(os.environ.get('rmq_username'), os.environ.get('rmq_password'))
    connection  = pika.BlockingConnection(pika.ConnectionParameters( host=os.environ.get('rmq_server'), port=os.environ.get('rmq_port'), credentials=credentials ))
    channel = connection.channel()
    channel.queue_declare(queue='opsgenie', durable=True)

    def callback(ch, method, properties, body):
        payload = json.loads(body) 
        if payload['action'] == 'Close':
           ops_CloseAlerts(payload['id'],payload['created_at'],payload['message'])
        elif payload['action'] == 'Delete':
           ops_DeleteAlerts(payload['id'],payload['created_at'],payload['message'])

    channel.basic_consume(queue='opsgenie', on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

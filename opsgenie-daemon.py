#!/usr/bin/env python

import sys
import os
import logging
import argparse
import time
import datetime
import opsgenie_sdk
import functools
import threading
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
tzone = tz.gettz(os.environ.get('TZ','Europe/Madrid'))

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


def ops_CloseAlerts(identifier,date,msg):
   try:
      queuesize = ops_CountAlets()
      print(date,' - ', queuesize, ' - ', identifier, ' - ', msg, ' - Closed.')
      api_response = opsapi.close_alert(identifier,identifier_type=identifier_type,close_alert_payload=close_alert_payload)
   except Exception as e:
      print(str(e))

def ops_DeleteAlerts(identifier,date,msg):
   try:
      print(date, ' - ', identifier, ' - ', msg, ' - Deleted.')
      api_response = opsapi.delete_alert(identifier, identifier_type=identifier_type, user=os.environ.get('OPSGENIE_CLOSER_USER'), source=os.environ.get('OPSGENIE_CLOSER_SOURCE'))
   except Exception as e:
      print(str(e))

def ops_CountAlets():
   api_response = opsapi.count_alerts()
   return(api_response.data.count)

#def callback(ch, method, properties, body):
#    payload = json.loads(body)
#    if payload['action'] == 'Close':
#        ops_CloseAlerts(payload['id'],payload['created_at'],payload['message'])
#    elif payload['action'] == 'Delete':
#        ops_DeleteAlerts(payload['id'],payload['created_at'],payload['message'])

def ack_message(ch, delivery_tag):
    if ch.is_open:
        ch.basic_ack(delivery_tag)
    else:
        pass

def do_work(conn, ch, delivery_tag, body):
    thread_id = threading.get_ident()

    payload = json.loads(body)
    if payload['action'] == 'Close':
        ops_CloseAlerts(payload['id'],payload['created_at'],payload['message'])
    elif payload['action'] == 'Delete':
        ops_DeleteAlerts(payload['id'],payload['created_at'],payload['message'])

    cb = functools.partial(ack_message, ch, delivery_tag)
    conn.add_callback_threadsafe(cb)


def on_message(ch, method_frame, _header_frame, body, args):
    (conn, thrds) = args
    delivery_tag = method_frame.delivery_tag
    t = threading.Thread(target=do_work, args=(conn, ch, delivery_tag, body))
    t.start()
    thrds.append(t)


def main():
    host = os.environ.get('RABBITMQ_DEFAULT_SERVER')
    port = os.environ.get('RABBITMQ_DEFAULT_PORT')
    username = os.environ.get('RABBITMQ_DEFAULT_USERNAME')
    password = os.environ.get('RABBITMQ_DEFAULT_PASSWORD')
    credentials = pika.PlainCredentials(username, password)
    parameters  = pika.ConnectionParameters( host=host, port=port, credentials=credentials, heartbeat=60 )
    connection  = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue='opsgenie', durable=True)
    channel.basic_qos(prefetch_count=10)
    # channel.basic_consume(queue='opsgenie', on_message_callback=callback, auto_ack=True)

    threads = []
    on_message_callback = functools.partial(on_message, args=(connection, threads))
    channel.basic_consume('opsgenie', on_message_callback)

    print(' [*] Connecting to host ['+username+'@'+host+':'+port+']. Waiting for messages. To exit press CTRL+C')

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        print('Interrupted')

    connection.close()

if __name__ == '__main__':
    main()


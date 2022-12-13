#!/usr/lib/zabbix/externalscripts/pyzabbix/bin/python

import sys
import os
import logging
import argparse
import time
import opsgenie_sdk
from datetime import datetime
from pprint import pprint
from distutils.util import strtobool
from opsgenie_sdk.rest import ApiException
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv 
load_dotenv("/usr/lib/zabbix/externalscripts/pyzabbix/.env")
file = open('/usr/lib/zabbix/externalscripts/pyzabbix/deleteByName.log', 'a')

DEBUG = bool(strtobool(os.environ.get('DEBUG','False')))

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
 
zapi = ZabbixAPI(os.environ.get('zbx_api_url'))
zapi.login(api_token=os.environ.get('zbx_api_token'))

def zbx_getHostID(hostName):
   try:
      hosts = zapi.host.get(filter={"host": hostName}, output=["hostid"])
      return(hosts[0]["hostid"])
   except Exception as e:
      print(str(e))

def zbx_deleteHostByID(hostID):
   try:
      result = zapi.host.delete(hostID)
   except Exception as e:
      print(e)

def getProblemByName(host_name,problem_name):
   problems = zapi.problem.get(filter={ "value": 1, "host": host_name },output=[ "name","eventid" ],selectTags= "extend",tags=[{"tag": "__zbx_ops_issuekey"}],search={"name": "*"+str(problem_name)+"*"},searchWildcardsEnabled=True,sortorder="ASC")
   for a in problems:
      for tag in a['tags']:
         if '__zbx_ops_issuekey' in tag['tag']:
            identifier = tag['value']
            save2log("getProblemByName - Hostname: [" + str(host_name) + "] - Problem: [" + str(problem_name) + "] - ID: [" + str(identifier) + "]")
            try:
                api_response = opsapi.close_alert(identifier,identifier_type=identifier_type,close_alert_payload=close_alert_payload)
            except Exception as e:
                #print(e)
                pass
def ops_CountAlets(QueryString):
   api_response = opsapi.count_alerts(query=QueryString)
   return(api_response.data.count)
   
def CloseProblemByMessage(msg):
   try:
      query = "status : open and message : *"+str(msg)+"*"
      offset = 0
      limit = 100
      sort = 'createdAt'
      order = 'desc'
      countAlerts = ops_CountAlets(query)
      max = int(round(countAlerts/100))+1
      #print("Query : [",query,"] Records: [",countAlerts,"] Iteracciones: [",max,"]")
      #print("Procesando",countAlerts,"registros.")
      for i in range(0,max+1):
         offset=(((max-i)*100))
         api_response = opsapi.list_alerts(query=query, offset=offset, limit=limit, sort=sort, order=order)
         for alert in api_response.data:
            api_response = opsapi.close_alert(alert.id,identifier_type=identifier_type,close_alert_payload=close_alert_payload)
            save2log("CloseProblemByHostname - Query: [" + str(msg) + "] - Problem: [" + str(alert.message) + "] - ID: [" + str(alert.id) + "]")
   except Exception as e:
      #print(e)
      save2log("CloseProblemByHostname - Query: [" + str(msg) + "] - Problem: [" + str(alert.message) + "] - ID: [" + str(alert.id) + "] ERROR: ["+str(e)+"]")
      pass

def zbx_CloseActiveProblems(host_name):
   save2log("zbx_CloseActiveProblems - Hostname: [" + str(host_name) + "]")
   # Get a list of all issues (AKA tripped triggers)
   triggers = zapi.trigger.get( only_true=1, active=1, output="extend", expandDescription=1, selectHosts=["host"], filter={"host": host_name, "value": 1})
   # Print a list containing only "tripped" triggers
   for t in triggers:
       if int(t["value"]) == 1:
          getProblemByName(host_name,t["description"])

def save2log(line):
   # current dateTime
   now = datetime.now()
   date_time_str = now.strftime("%Y-%m-%d %H:%M:%S - ")
   file.writelines("{}\n".format(str(date_time_str) + str(line)))

parser = argparse.ArgumentParser("settriggerdependency.py")
parser.add_argument('-n', '--hostname', help="Nombre del Host en Zabbix", type=str)
parser.add_argument('-m', '--message', help="Cierro problemas por nombre", type=str)
args = parser.parse_args()

if args.hostname:
   zbx_CloseActiveProblems(args.hostname)
   zbx_deleteHostByID(zbx_getHostID(args.hostname))
elif args.message:
   CloseProblemByMessage(args.message)
else:
   print(parser.print_help())

file.close()

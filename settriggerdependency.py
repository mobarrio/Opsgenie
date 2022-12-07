#!/usr/lib/zabbix/externalscripts/pyzabbix/bin/python

import sys
import os
import logging
import argparse
import time
from distutils.util import strtobool
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv 
load_dotenv("/usr/lib/zabbix/externalscripts/pyzabbix/.env")

DEBUG = bool(strtobool(os.environ.get('DEBUG','False')))

if(DEBUG):
  stream = logging.StreamHandler(sys.stdout)
  stream.setLevel(logging.DEBUG)
  log = logging.getLogger('pyzabbix')
  log.addHandler(stream)
  log.setLevel(logging.DEBUG)

zapi = ZabbixAPI(os.environ.get('zbx_api_url'))
zapi.login(api_token=os.environ.get('zbx_api_token'))

def getTriggerId(host_name,trigger_desc):
   try:
      triggers = zapi.trigger.get(filter={"host": host_name, "value": 1}, search={"description": "*"+trigger_desc+"*"}, output=["triggerid","description","value","priority"], searchWildcardsEnabled=True,selectHosts=["host","hostid"])
      return(triggers[0]['triggerid'])
   except:
      return(-1)

def settriggerDependecy(hijo,padre):
   triggers = zapi.trigger.update(triggerid=hijo,dependencies=[{"triggerid":padre}])

parser = argparse.ArgumentParser("settriggerdependency.py")
parser.add_argument('-n', '--hostname', help="Nombre del Host en Zabbix", type=str)
parser.add_argument('-a', '--hijo', help="Descripcion del trigger HIJO (HIJO Depende del PADRE)", type=str)
parser.add_argument('-b', '--padre', help="Descripcion del trigger PADRE (HIJO Depende del PADRE)", type=str)
args = parser.parse_args()

try:
   if args.hostname and args.padre and args.hijo:
      padre=getTriggerId(args.hostname,args.padre)
      hijo=getTriggerId(args.hostname,args.hijo)
      settriggerDependecy(hijo,padre)
   else:
      print(parser.print_help())
except:
   print({"Status": "Error"})

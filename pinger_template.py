import asyncio
from timeit import default_timer
from aiohttp import ClientSession
import aiohttp
import yaml
import aws_lambda_logging
import logging
import time
import botocore.config
import boto3
import slackweb
import ast
import datetime
import json

# JSON logger initialisation
logger = logging.getLogger()
from aws_lambda_logging import setup
setup('log-level')

# Parameters from SSM
cfg = botocore.config.Config(retries={'max_attempts': 0})
ssm = boto3.client('ssm',config=cfg,region_name='specify-region')

# Parameters for Slack Notification
notification = "none"
if notification == "slack": 
    slack_webhook = ssm.get_parameter(Name='slack_webhook',WithDecryption=True)
    slack_payload = {"fallback": "Weburl ping status critical","color": "#ff0000","author_name": "Pinger","title": "Weburl Ping Status","title_link": "https://api.slack.com/","text": "Weburl not responding, HTTP error code ~~~ERRORCODE~~~","fields": [{"title": "Priority","value": "High"},{"title": "View details logs in cloud watch","value":'https://specify-region.console.aws.amazon.com/cloudwatch/home?region=specify-region#logStream:group=%252Faws%252Flambda%252Fpinger'}],"footer": "Slack API","footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png","ts": 1532746720.06}   
    slack = slackweb.Slack(url=slack_webhook['Parameter']['Value'])

# Parameters & functions for state machine s3 bucket
state_machine_s3 = "s3-bucket-name"
s3 = boto3.resource("s3").Bucket(state_machine_s3)
json.load_s3 = lambda filename: json.load(s3.Object(key=filename).get()["Body"])
json.dump_s3 = lambda object, filename: s3.Object(key=filename).put(Body=json.dumps(object))
yaml.load_s3 = lambda filename: yaml.load(s3.Object(key=filename).get()["Body"])
state_machine = json.load_s3('state_machine')



def slack_notification(url,status_code,status):
    """ Send notifications to slack """
    if notification == "slack":    
        if status == "StatusOK":
            attachments = []
            slack_payload['color'] = "#36a64f"
            slack_payload['text'] = '%s is back healthy and responding with status code %d' % (url, status_code)
            slack_payload['fallback'] = "Weburl ping status, Normal!!!"
            slack_payload['title_link'] = url
            slack_payload['fields'][0]['value'] = 'Normal'
            slack_payload['ts'] = time.time()
            attachments.append(slack_payload)
            slack.notify(attachments=attachments)
        else:
            attachments = []
            slack_payload['color'] = "#ff0000"
            slack_payload['text'] = '%s is not healthy and failing with error message "%s" exit/status code %d' % (url, status, status_code)
            slack_payload['fallback'] = "Weburl ping status, Critical!!!"
            slack_payload['title_link'] = url
            slack_payload['fields'][0]['value'] = 'High'
            slack_payload['ts'] = time.time()
            attachments.append(slack_payload)
            slack.notify(attachments=attachments)

def ping_urls(urls):
    """Fetch response code and response time of web pages asynchronously."""
    start_time = default_timer()

    loop = asyncio.get_event_loop() # event loop
    future = asyncio.ensure_future(fetch_all(urls)) # tasks to do
    loop.run_until_complete(future) # loop until done

    tot_elapsed = default_timer() - start_time
    logger.info('{" TotalRuntime": %5.2f }' % (tot_elapsed))

async def fetch_all(urls):
    """Launch requests for all web pages."""
    tasks = []
    fetch.start_time = dict() # dictionary of start times for each url
    async with ClientSession(connector=aiohttp.TCPConnector(ssl=False),timeout=aiohttp.ClientTimeout(total=60)) as session:
        for url in urls:
            # print("get status for %s" % (url))
            task = asyncio.ensure_future(fetch(url, session))
            tasks.append(task) # create list of tasks
        _ = await asyncio.gather(*tasks) # gather task responses

async def fetch(url, session):
    """Fetch a url, using specified ClientSession."""
    fetch.start_time[url] = default_timer()
    try:
        async with session.get(url) as response:
            resp = await response.read()
            elapsed = default_timer() - fetch.start_time[url]
            if response.status == 200:
                message = "StatusOK"
            else:
                message = "StatusNOK"
            logger.info('{"URL": "%s", "StatusCode": %d, "ResponseTime": %5.2f, "Message": "%s"}' % (url,response.status,elapsed,message))
            # print('{"URL": "%s", "StatusCode": %d, "ResponseTime": %5.2f, "Message": "%s"}' % (url,response.status,elapsed,message))
            await update_state_machine(url,response.status,message)
            return resp
    except aiohttp.InvalidURL as e:
        logger.critical('{"URL": "%s", "StatusCode": %d, "ResponseTime": %5.2f, "Message": "%s"}' % (url,1,0.0,"Error::InvalidURL"))
        await update_state_machine(url,1,"Error::InvalidURL")
        pass
    except asyncio.TimeoutError as e:
        logger.critical('{"URL": "%s", "StatusCode": %d, "ResponseTime": %5.2f, "Message": "%s"}' % (url,1,0.0,"Error::client timeout after waiting for 60 secs, Increase client timeout if this is excepted behaviour"))
        await update_state_machine(url,1,"Error::client timeout after waiting for 60 secs, Increase client timeout if this is excepted behaviour")
        pass         
    except  aiohttp.ClientError as e:
        logger.critical('{"URL": "%s", "StatusCode": %d, "ResponseTime": %5.2f, "Message": "%s"}' % (url,1,0.0,e))
        await update_state_machine(url,1,str(e))
        pass

async def update_state_machine(url,status_code,message):
    """update the state machine with current status and send notification to slack"""
    if url in state_machine.keys():
        if state_machine[url] != message:
            slack_notification(url,status_code,message)
            state_machine[url] = message
    else:
        if message != "StatusOK":
            state_machine.update({ url : message})
            slack_notification(url,status_code,message)
        else:
            state_machine.update({ url : message})
    # print(state_machine)


def ping_handler(event, context):
    config = yaml.load_s3('config.yaml')
    if config['monitor']['urls'] != None:
        ping_urls(config['monitor']['urls'])
    json.dump_s3(state_machine,'state_machine')
import urllib3
import json
import boto3

client = boto3.client('sns')
ssm = boto3.client('ssm')


slack_url = str()
http = urllib3.PoolManager()


def get_alarm_attributes(sns_message, currentEnv, severity, runbookLink):
    alarm = dict()

    alarm['name'] = sns_message['AlarmName']
    alarm['description'] = sns_message['AlarmDescription']
    alarm['reason'] = sns_message['NewStateReason']
    alarm['region'] = sns_message['Region']
    alarm['instance_id'] = sns_message['Trigger']['Dimensions'][0]['value']
    alarm['state'] = sns_message['NewStateValue']
    alarm['previous_state'] = sns_message['OldStateValue']
    alarm['currentEnv'] = currentEnv
    alarm['severity'] = severity
    alarm['runbookLink'] = runbookLink
    
    return alarm


def activate_alarm(alarm):
    return {
        "type": "plain_text",
        "text" : alarm['name'] + "alarm triggered --- " + alarm['currentEnv'],
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":red_circle: Alarm: " + alarm['name'],
                }
            },
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Environment: " + alarm['currentEnv'],
                }
            },
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Resource: " + alarm['instance_id'],
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Documentation Link: " + alarm['runbookLink']
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "_" + alarm['reason'] + "_"
                },
                "block_id": "text1"
            },
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Region: *" + alarm['region'] + "*"
                    }
                ]
            }
        ]
    }
def resolve_alarm(alarm):
    return {
        "type": "plain_text",
        "text" : alarm['name'] + "alarm resolved --- " + alarm['currentEnv'],
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":large_green_circle: Alarm: " + alarm['name'] + " was resolved ",
                }
            },
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Environment: " + alarm['currentEnv'],
                }
            },
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Resource: " + alarm['instance_id'],
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "_" + alarm['reason'] + "_"
                },
                "block_id": "text1"
            },
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Region: *" + alarm['region'] + "*"
                    }
                ]
            }
        ]
    }


def lambda_handler(event, context):
    sns_topic_arn = event["Records"][0]["Sns"]["TopicArn"]
    sns_message = json.loads(event["Records"][0]["Sns"]["Message"])

    response = client.list_tags_for_resource(
        ResourceArn = sns_topic_arn
    )
    
    tagList = response['Tags']
    currentEnv = 'Null'
    severity = 'Null'
    slackChannel = 'Null'
    runbookLink = 'Null'
    
    
    for tag in tagList:
        if tag['Key'] == 'Environment':
            currentEnv = str(tag['Value'])
        if tag['Key'] == 'Severity':
            severity = str(tag['Value'])
        if tag['Key'] == 'Channel':
            slackChannel = str(tag['Value'])
        if tag['Key'] == 'Runbook':
            runbookLink = str(tag['Value'])

    
    variable = currentEnv + '/slack/' + slackChannel + '/webhook'
    
    parameter = ssm.get_parameter(
        Name=variable,
        WithDecryption=True
    )
                
    slack_url = parameter['Parameter']['Value']
            
    alarm = get_alarm_attributes(sns_message, currentEnv, severity, runbookLink)

    msg = str()
    

    # if alarm['severity'] == 'High':
    #     slack_url = emergencyUrl
    # if alarm['severity'] == 'Low':
    #     slack_url = alertsUrl
        
    if alarm['previous_state'] == 'OK' and alarm['state'] == 'ALARM':
        msg = activate_alarm(alarm)
    elif alarm['previous_state'] == 'ALARM' and alarm['state'] == 'OK':
        msg = resolve_alarm(alarm)

    encoded_msg = json.dumps(msg).encode("utf-8")
    resp = http.request("POST", slack_url, body=encoded_msg, headers={'Content-Type': 'application/json'})
    
    print(
        {
            "message": msg,
            "status_code": resp.status,
            "response": resp.data,
        }
    )
    

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os

import boto3
from aws_lambda_powertools import Logger, Tracer
import dynamodb.tenant_management_util as tenant_management_util

tracer = Tracer()
logger = Logger()

event_bus = boto3.client('events')
eventbus_name = os.environ['EVENTBUS_NAME']
event_source = os.environ['EVENT_SOURCE']
dynamodb = boto3.resource('dynamodb')
tenant_details_table = dynamodb.Table(os.environ['TENANT_DETAILS_TABLE'])


def __provision_onboarding(event):
    try:
        item = event['previousOutput']['Payload']
        item['taskToken'] = event['taskToken']

        response = tenant_management_util.update_tenant(item['tenantId'], item)
        logger.info('update_tenant %s:', response)
        return item
    except Exception as e:
        raise Exception("Error provision onboarding: ", e)


@tracer.capture_lambda_handler
def lambda_handler(event, context):
    try:
        response = __provision_onboarding(event)
        return response
    except Exception as e:
        raise Exception("Error lambda_handler: ", e)

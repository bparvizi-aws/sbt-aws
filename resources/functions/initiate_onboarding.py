# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
import uuid

import boto3
from aws_lambda_powertools import Logger, Tracer
from models.control_plane_event_types import ControlPlaneEventTypes

tracer = Tracer()
logger = Logger()

event_bus = boto3.client('events')
eventbus_name = os.environ['EVENTBUS_NAME']
event_source = os.environ['EVENT_SOURCE']
dynamodb = boto3.resource('dynamodb')
tenant_details_table = dynamodb.Table(os.environ['TENANT_DETAILS_TABLE'])


@tracer.capture_method
def __initiate_onboarding(event):
    input_details = event
    input_item = {}
    input_details['tenantId'] = str(uuid.uuid4())

    try:
        for key, value in input_details.items():
            input_item[key] = value

        input_item['isActive'] = True
        input_item['taskToken'] = ''

        response = tenant_details_table.put_item(Item=input_item)
        return {
            'Payload': input_item
        }
    except Exception as e:
        raise Exception("Error creating a new tenant", e)


@tracer.capture_lambda_handler
def lambda_handler(event, context):
    logger.info('lambda_handler event %s:', event)
    try:
        response = __initiate_onboarding(event)
        return response
    except Exception as e:
        raise Exception("Error lambda_handler: ", e)

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import json
import boto3
import dynamodb.tenant_management_util as tenant_management_util
from aws_lambda_powertools import Logger, Tracer
from datetime import datetime
from models.control_plane_event_types import ControlPlaneEventTypes

tracer = Tracer()
logger = Logger()

event_bus = boto3.client('events')
eventbus_name = os.environ['EVENTBUS_NAME']
event_source = os.environ['EVENT_SOURCE']


def __provision_onboarding(event):
    try:
        # Update db record.
        item = event['previousOutput']['Payload']
        item['taskToken'] = event['taskToken']
        # now = datetime.now()
        item['tenantStatus']['Provision Onboarding'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        response = tenant_management_util.update_tenant(item['tenantId'], item)

        # Publish event to EventBridge.
        __create_control_plane_event(
            json.dumps(item), ControlPlaneEventTypes.ONBOARDING.value)
        logger.info('update_tenant success %s:', response)
        return item
    except Exception as e:
        raise Exception("Error provision onboarding: ", e)


def __create_control_plane_event(eventDetails, eventType):
    logger.info('Control plane event info:', eventbus_name, event_source, eventType)
    logger.info('Control plane event eventDetails: %s', eventDetails)
    response = event_bus.put_events(
        Entries=[
            {
                'EventBusName': eventbus_name,
                'Source': event_source,
                'DetailType': eventType,
                'Detail': eventDetails,
            }
        ]
    )
    logger.info(response)


@tracer.capture_lambda_handler
def lambda_handler(event, context):
    try:
        response = __provision_onboarding(event)
        return response
    except Exception as e:
        raise Exception("Error lambda_handler: ", e)

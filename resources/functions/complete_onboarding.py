# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

#import json
import os

import boto3
from aws_lambda_powertools import Logger, Tracer
#from models.control_plane_event_types import ControlPlaneEventTypes
#from models.onboarding_event_types import OnboardingEventTypes

tracer = Tracer()
logger = Logger()

event_bus = boto3.client('events')
eventbus_name = os.environ['EVENTBUS_NAME']
event_source = os.environ['EVENT_SOURCE']
dynamodb = boto3.resource('dynamodb')
tenant_details_table = dynamodb.Table(os.environ['TENANT_DETAILS_TABLE'])


@tracer.capture_method
def update_tenant(event):
    try:
        logger.info("update_tenant:  %s", event)
    except Exception as e:
        raise Exception("Error updating tenant", e)


def __create_control_plane_event(eventDetails, eventType):
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
        logger.info('complete Onboarding event %s:', event)
    except Exception as e:
        raise Exception("Error lambda_handler: ", e)

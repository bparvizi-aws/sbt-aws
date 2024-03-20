# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
import uuid

import boto3
from aws_lambda_powertools import Logger, Tracer
from models.control_plane_event_types import ControlPlaneEventTypes
from models.onboarding_event_types import OnboardingEventTypes

tracer = Tracer()
logger = Logger()

event_bus = boto3.client('events')
eventbus_name = os.environ['EVENTBUS_NAME']
event_source = os.environ['EVENT_SOURCE']
dynamodb = boto3.resource('dynamodb')
tenant_details_table = dynamodb.Table(os.environ['TENANT_DETAILS_TABLE'])


@tracer.capture_method
def create_tenant(event):
    input_details = app.current_event.json_body
    input_item = {}
    input_details['tenantId'] = str(uuid.uuid4())

    try:
        for key, value in input_details.items():
            input_item[key] = value

        input_item['isActive'] = True

        response = tenant_details_table.put_item(Item=input_item)

        logger.info("Event input_details: ", input_details, ControlPlaneEventTypes.ONBOARDING.value)

    except Exception as e:
        raise Exception("Error creating a new tenant", e)
    else:
        return "New tenant created", HTTPStatus.OK


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


def __initiate_onboarding(event):
    try:
        logger.info("__initiate_onboarding: %s", event)
        # create_tenant(event)
    except Exception as e:
        raise Exception("Error initiating onboarding: ", e)


@tracer.capture_lambda_handler
def lambda_handler(event, context):
    logger.info('lambda_handler event %s:', event)
    logger.info('lambda_handler context %s:', context)
    try:
        __initiate_onboarding(event)
    except Exception as e:
        raise Exception("Error lambda_handler: ", e)

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
from http import HTTPStatus
import uuid

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import (APIGatewayRestResolver,
                                                 CORSConfig)
from aws_lambda_powertools.logging import correlation_paths
from models.control_plane_event_types import ControlPlaneEventTypes
from models.onboarding_event_types import OnboardingEventTypes

tracer = Tracer()
logger = Logger()
# TODO Make sure we fill in an appropriate origin for this call (the CloudFront domain)
cors_config = CORSConfig(allow_origin="*", max_age=300)
app = APIGatewayRestResolver(cors=cors_config)

event_bus = boto3.client('events')
eventbus_name = os.environ['EVENTBUS_NAME']
event_source = os.environ['EVENT_SOURCE']
dynamodb = boto3.resource('dynamodb')
tenant_details_table = dynamodb.Table(os.environ['TENANT_DETAILS_TABLE'])


@app.post("/tenants")
@tracer.capture_method
def create_tenant():
    input_details = app.current_event.json_body
    input_item = {}
    input_details['tenantId'] = str(uuid.uuid4())

    try:
        for key, value in input_details.items():
            input_item[key] = value

        input_item['isActive'] = True

        response = tenant_details_table.put_item(Item=input_item)

        logger.info("Event input_details: ", input_details, ControlPlaneEventTypes.ONBOARDING.value)

        __create_control_plane_event(
            json.dumps(input_details), ControlPlaneEventTypes.ONBOARDING.value)

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


def __handle_onboarding_events(event):
    logger.info("__handle_onboarding_events: ", event)
    try:
        def handle_onboarding_initiated():
            logger.info("handle_onboarding_initiated: ")
            return

        def handle_onboarding_valid():
            logger.info("handle_onboarding_valid: ")
            return

        def handle_onboarding_deployed():
            logger.info("handle_onboarding_provisioned: ")
            return

        def handle_onboarding_provisioned():
            logger.info("handle_onboarding_provisioned: ")
            return

        def handle_onboarding_completed():
            logger.info("handle_onboarding_completed: ")
            return

        def handle_onboarding_failed():
            logger.info("handle_onboarding_failed: ")
            return

        def handle_onboarding_default():
            logger.info("handle_onboarding_default: ")
            return

        detail_type = event.get('detail-type', '')
        match detail_type:
            case OnboardingEventTypes.ONBOARDING_INITIATED:
                return handle_onboarding_initiated()
            case OnboardingEventTypes.ONBOARDING_VALID:
                return handle_onboarding_valid()
            case OnboardingEventTypes.ONBOARDING_DEPLOYED:
                return handle_onboarding_deployed()
            case OnboardingEventTypes.ONBOARDING_PROVISIONED:
                return handle_onboarding_provisioned()
            case OnboardingEventTypes.ONBOARDING_COMPLETED:
                return handle_onboarding_completed()
            case OnboardingEventTypes.ONBOARDING_FAILED:
                return handle_onboarding_failed()

    except Exception as e:
        raise Exception("Error handling onboarding events: ", e)


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST, log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    logger.info(event)
    try:
        if 'httpMethod' in event:
            return app.resolve(event, context)
        elif "source" in event:
            __handle_onboarding_events(event)
            return {
                'statusCode': 200,
                'body': json.dumps('Event processed.')
            }
    except Exception as e:
        raise Exception("Error lambda_handler: ", e)

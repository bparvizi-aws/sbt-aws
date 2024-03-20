# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# import json
import os

import boto3
from aws_lambda_powertools import Logger, Tracer

# from aws_lambda_powertools.logging import correlation_paths
# from models.control_plane_event_types import ControlPlaneEventTypes
# from models.onboarding_event_types import OnboardingEventTypes

tracer = Tracer()
logger = Logger()

event_bus = boto3.client('events')
eventbus_name = os.environ['EVENTBUS_NAME']
event_source = os.environ['EVENT_SOURCE']
dynamodb = boto3.resource('dynamodb')
tenant_details_table = dynamodb.Table(os.environ['TENANT_DETAILS_TABLE'])


@tracer.capture_lambda_handler
def lambda_handler(event, context):
    try:
        logger.info('lambda_handler event %s:', event)
        logger.info('lambda_handler context %s:', context)
    except Exception as e:
        raise Exception("Error error_handler: ", e)

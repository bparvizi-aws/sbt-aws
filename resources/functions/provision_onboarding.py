# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import boto3
from aws_lambda_powertools import Logger, Tracer

tracer = Tracer()
logger = Logger()

event_bus = boto3.client('events')
eventbus_name = os.environ['EVENTBUS_NAME']
event_source = os.environ['EVENT_SOURCE']
dynamodb = boto3.resource('dynamodb')
tenant_details_table = dynamodb.Table(os.environ['TENANT_DETAILS_TABLE'])


def __provision_onboarding(event):
    try:
        logger.info('__provision_onboarding %s:', event)
    except Exception as e:
        raise Exception("Error initiating onboarding: ", e)


@tracer.capture_lambda_handler
def lambda_handler(event, context):
    try:
        __provision_onboarding(event)
    except Exception as e:
        raise Exception("Error lambda_handler: ", e)

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import boto3
from aws_lambda_powertools import Logger, Tracer
from datetime import datetime
import dynamodb.tenant_management_util as tenant_management_util

tracer = Tracer()
logger = Logger()

event_bus = boto3.client('events')
eventbus_name = os.environ['EVENTBUS_NAME']
event_source = os.environ['EVENT_SOURCE']
dynamodb = boto3.resource('dynamodb')
tenant_details_table = dynamodb.Table(os.environ['TENANT_DETAILS_TABLE'])


@tracer.capture_method
def __initiate_onboarding(event):
    try:
        # set tenant status.
        now = datetime.now()
        event['tenantStatus'] = {"Initiate Onboarding": now.strftime('%Y-%m-%d %H:%M:%S')}
        tenant = tenant_management_util.create_tenant(event)
        logger.info("tenant_management_util.create_tenant success: %s", tenant)
        return {
            'Payload': tenant
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

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
from aws_lambda_powertools import Logger, Tracer
import dynamodb.tenant_management_util as tenant_management_util

tracer = Tracer()
logger = Logger()

@tracer.capture_method
def __complete_onboarding(event):
    try:
        # Get tenant record.
        tenant_id = event.get('tenantId')
        logger.info('__complete_onboarding tenant_id %s:', tenant_id)
        response = tenant_management_util.get_tenant(tenant_id)
        item = response['Item']

        # Update db record.
        item['tenantStatus']['Onboarding Complete'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        response = tenant_management_util.update_tenant(item['tenantId'], item)

        return item
    except Exception as e:
        raise Exception("Error complete Onboarding: ", e)


@tracer.capture_lambda_handler
def lambda_handler(event, context):
    try:
        logger.info('complete Onboarding event %s:', event)
        __complete_onboarding(event)
    except Exception as e:
        raise Exception("Error lambda_handler: ", e)

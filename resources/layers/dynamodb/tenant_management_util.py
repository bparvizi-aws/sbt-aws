# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# import json
import os
import uuid

import boto3
from aws_lambda_powertools import Logger, Tracer

tracer = Tracer()
logger = Logger()

dynamodb = boto3.resource('dynamodb')
tenant_details_table = dynamodb.Table(os.environ['TENANT_DETAILS_TABLE'])


@tracer.capture_method
def get_tenant(tenant_id):
    try:
        response = tenant_details_table.get_item(Key={'tenantId': tenant_id})
        return response
    except Exception as e:
        raise Exception('Error getting tenant', e)


@tracer.capture_method
def create_tenant(event):
    input_details = event
    input_item = {}
    input_details['tenantId'] = str(uuid.uuid4())
    try:
        for key, value in input_details.items():
            input_item[key] = value

        input_item['isActive'] = True
        input_item['taskToken'] = ''

        response = tenant_details_table.put_item(Item=input_item)
        return input_item
    except Exception as e:
        raise Exception("Error creating a new tenant", e)


@tracer.capture_method
def update_tenant(tenantId, tenant):
    try:
        # Remove the tenantId if the incoming object has one
        input_details = {key: tenant[key] for key in tenant if key != 'tenantId'}
        update_expression = []
        update_expression.append("set ")
        expression_attribute_values = {}
        for key, value in input_details.items():
            key_variable = f":{key}Variable"
            update_expression.append(''.join([key, " = ", key_variable]))
            update_expression.append(",")
            expression_attribute_values[key_variable] = value

        # remove the last comma
        update_expression.pop()

        response_update = tenant_details_table.update_item(
            Key={
                'tenantId': tenantId,
            },
            UpdateExpression=''.join(update_expression),
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="UPDATED_NEW"
        )

        return response_update
    except Exception as e:
        raise Exception("Error updating tenant", e)

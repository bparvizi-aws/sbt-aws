
import os
import json
import boto3
import dynamodb.tenant_management_util as tenant_management_util
from aws_lambda_powertools import Logger, Tracer

tracer = Tracer()
logger = Logger()

# Initialize the Boto3 Step Functions client
sfn_client = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')
tenant_details_table = dynamodb.Table(os.environ['TENANT_DETAILS_TABLE'])

def lambda_handler(event, context):
    detail = event.get('detail')

    # Extract result (success or failure) from the event.
    process_result = detail.get('result')

    # Extract the task token from the event.
    task_token = detail.get('taskToken')
    tenant_id = detail.get('tenantId')

    tenant_details = tenant_management_util.get_tenant(tenant_id)
    logger.info('Get tenant_details success Refactor 1: %s', tenant_details)

    try:
        if process_result == 'success':
            # If process is successful, send task success
            response = sfn_client.send_task_success(
                taskToken=task_token,
                output=json.dumps({"tenantId": tenant_id, "message": "Provisioning completed successfully"})
            )
            return {
                'statusCode': 200,
                'body': json.dumps('Task success sent.')
            }
        else:
            # If process fails, send task failure
            response = sfn_client.send_task_failure(
                taskToken=task_token,
                error='ProcessFailed',
                cause='Provisioning failed.'
            )
            return {
                'statusCode': 400,
                'body': json.dumps('Task failure sent.')
            }
    except Exception as e:
        print(f"Error sending task response: {str(e)}")
        # Handle exceptions or errors as necessary
        return {
            'statusCode': 500,
            'body': json.dumps('Error sending task response.')
        }

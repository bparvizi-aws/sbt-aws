import json
import boto3

# Initialize the Boto3 Step Functions client
sfn_client = boto3.client('stepfunctions')


def lambda_handler(event, context):
    # Extract the task token from the event. Adjust the key based on your actual event structure.
    task_token = event.get('taskToken')

    # Get result of success or failure
    process_result = event.get('result')

    try:
        if process_result == 'success':
            # If process is successful, send task success
            response = sfn_client.send_task_success(
                taskToken=task_token,
                output=json.dumps({"message": "Provisioning completed successfully"})
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

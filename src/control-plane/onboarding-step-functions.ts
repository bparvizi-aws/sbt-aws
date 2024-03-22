// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as path from 'path';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import { ManagedPolicy, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as stepfunctions from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { NagSuppressions } from 'cdk-nag';
import { Construct } from 'constructs';

export interface OnboardingStepFunctionsProps {
  readonly initiateOnboarding: PythonFunction;
  readonly provisionOnboarding: PythonFunction;
  readonly completeOnboarding: PythonFunction;
  readonly errorHandler: PythonFunction;
}

export class OnboardingStepFunctions extends Construct {
  constructor(scope: Construct, id: string, props: OnboardingStepFunctionsProps) {
    super(scope, id);

    // Error handler task.
    const errorHandlerTask = new tasks.LambdaInvoke(this, 'ErrorHandlerTask', {
      lambdaFunction: props.errorHandler,
    });

    // Initiate Onboarding.
    const initiateOnboardingTask = new tasks.LambdaInvoke(this, 'InitiateOnboarding', {
      lambdaFunction: props.initiateOnboarding,
      integrationPattern: stepfunctions.IntegrationPattern.REQUEST_RESPONSE,
      outputPath: '$.Payload',
      taskTimeout: stepfunctions.Timeout.duration(cdk.Duration.minutes(5)),
    }).addCatch(errorHandlerTask);

    // Provision Onboarding.
    const provisionOnboardingTask = new tasks.LambdaInvoke(this, 'ProvisionOnboarding', {
      lambdaFunction: props.provisionOnboarding,
      integrationPattern: stepfunctions.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
      inputPath: '$',
      payload: stepfunctions.TaskInput.fromObject({
        taskToken: stepfunctions.JsonPath.taskToken, // Save token to external checkpointing system, e.g., DynamoDB
        'previousOutput.$': '$',
      }),
      taskTimeout: stepfunctions.Timeout.duration(cdk.Duration.hours(2)),
    }).addCatch(errorHandlerTask);

    // Complete Onboarding.
    const completeOnboardingTask = new tasks.LambdaInvoke(this, 'CompleteOnboarding', {
      lambdaFunction: props.completeOnboarding,
      integrationPattern: stepfunctions.IntegrationPattern.REQUEST_RESPONSE,
      taskTimeout: stepfunctions.Timeout.duration(cdk.Duration.minutes(30)),
    }).addCatch(errorHandlerTask);

    // State Machine.
    const logGroup = new logs.LogGroup(this, 'StepFunctionsLogGroup', {
      logGroupName: '/aws/OnboardingStateMachineLogs',
      retention: logs.RetentionDays.THREE_DAYS,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    const definition = initiateOnboardingTask
      .next(provisionOnboardingTask)
      .next(completeOnboardingTask);
    const stateMachine = new stepfunctions.StateMachine(this, 'OnboardingStateMachine', {
      definitionBody: stepfunctions.DefinitionBody.fromChainable(definition),
      logs: {
        destination: logGroup,
        level: stepfunctions.LogLevel.ALL,
      },
      tracingEnabled: true,
    });

    // Onboarding Event bridge handler.
    const lambdaExecRole = new Role(this, 'lambdaExecRole', {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
    });
    lambdaExecRole.addManagedPolicy(
      ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
    );
    lambdaExecRole.addManagedPolicy(
      ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLambdaInsightsExecutionRolePolicy')
    );
    lambdaExecRole.addManagedPolicy(
      ManagedPolicy.fromAwsManagedPolicyName('AWSXrayWriteOnlyAccess')
    );
    const policyStatement = new iam.PolicyStatement({
      actions: ['states:SendTaskSuccess', 'states:SendTaskFailure'],
      resources: [stateMachine.stateMachineArn],
    });
    lambdaExecRole.addToPolicy(policyStatement);
    NagSuppressions.addResourceSuppressions(
      lambdaExecRole,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'Index name(s) not known beforehand.',
          appliesTo: [`Resource::<ControlPlanetablesstackTenantDetails78527218.Arn>/index/*`],
        },
        {
          id: 'AwsSolutions-IAM4',
          reason:
            'Suppress usage of AWSLambdaBasicExecutionRole, CloudWatchLambdaInsightsExecutionRolePolicy, and AWSXrayWriteOnlyAccess.',
          appliesTo: [
            'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
            'Policy::arn:<AWS::Partition>:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy',
            'Policy::arn:<AWS::Partition>:iam::aws:policy/AWSXrayWriteOnlyAccess',
          ],
        },
      ],
      true // applyToChildren = true, so that it applies to policies created for the role.
    );

    new PythonFunction(this, 'OnboardingEventsHandler', {
      entry: path.join(__dirname, '../../resources/functions/'),
      runtime: Runtime.PYTHON_3_12,
      index: 'onboarding_events_handler.py',
      handler: 'lambda_handler',
      role: lambdaExecRole,
    });

    NagSuppressions.addResourceSuppressions(
      stateMachine,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'Wildcard required in order pass tenantId in path.',
          appliesTo: ['Resource::*'],
        },
      ],
      true // applyToChildren = true, so that it applies to the APIGW role created by cdk in the controlPlaneAPI construct
    );
  }
}

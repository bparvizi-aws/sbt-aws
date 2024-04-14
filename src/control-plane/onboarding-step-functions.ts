// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as path from 'path';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import * as cdk from 'aws-cdk-lib';
import { Duration } from 'aws-cdk-lib';
import { EventBus } from 'aws-cdk-lib/aws-events';
import { LambdaFunction } from 'aws-cdk-lib/aws-events-targets';
import { ManagedPolicy, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Runtime, LayerVersion } from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as stepfunctions from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { NagSuppressions } from 'cdk-nag';
import { Construct } from 'constructs';
import { Tables } from './tables';

export interface OnboardingStepFunctionsProps {
  readonly controlPlaneEventSource: string;
  readonly eventBus: EventBus;
  readonly lambdaLayer: LayerVersion;
  readonly tables: Tables;
}

export class OnboardingStepFunctions extends Construct {
  lambdaEventTarget: LambdaFunction;

  constructor(scope: Construct, id: string, props: OnboardingStepFunctionsProps) {
    super(scope, id);

    // Lambda Execution Role:
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
    props.tables.tenantDetails.grantReadWriteData(lambdaExecRole);
    props.eventBus.grantPutEventsTo(lambdaExecRole);
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
      true
    );

    // Lambda Functions:
    // Onboarding services.
    const initiateOnboarding = new PythonFunction(this, 'InitiateOnboarding', {
      entry: path.join(__dirname, '../../resources/functions/'),
      runtime: Runtime.PYTHON_3_12,
      index: 'initiate_onboarding.py',
      handler: 'lambda_handler',
      timeout: Duration.seconds(60),
      role: lambdaExecRole,
      layers: [props.lambdaLayer],
      environment: {
        EVENTBUS_NAME: props.eventBus.eventBusName,
        EVENT_SOURCE: props.controlPlaneEventSource,
        TENANT_DETAILS_TABLE: props.tables.tenantDetails.tableName,
      },
    });

    const provisionOnboarding = new PythonFunction(this, 'ProvisionOnboarding', {
      entry: path.join(__dirname, '../../resources/functions/'),
      runtime: Runtime.PYTHON_3_12,
      index: 'provision_onboarding.py',
      handler: 'lambda_handler',
      timeout: Duration.seconds(60),
      role: lambdaExecRole,
      layers: [props.lambdaLayer],
      environment: {
        EVENTBUS_NAME: props.eventBus.eventBusName,
        EVENT_SOURCE: props.controlPlaneEventSource,
        TENANT_DETAILS_TABLE: props.tables.tenantDetails.tableName,
      },
    });

    const completeOnboarding = new PythonFunction(this, 'CompleteOnboarding', {
      entry: path.join(__dirname, '../../resources/functions/'),
      runtime: Runtime.PYTHON_3_12,
      index: 'complete_onboarding.py',
      handler: 'lambda_handler',
      timeout: Duration.seconds(60),
      role: lambdaExecRole,
      layers: [props.lambdaLayer],
      environment: {
        EVENTBUS_NAME: props.eventBus.eventBusName,
        EVENT_SOURCE: props.controlPlaneEventSource,
        TENANT_DETAILS_TABLE: props.tables.tenantDetails.tableName,
      },
    });

    // Error handler.
    const errorHandler = new PythonFunction(this, 'ErrorHandler', {
      entry: path.join(__dirname, '../../resources/functions/'),
      runtime: Runtime.PYTHON_3_12,
      index: 'error_handler.py',
      handler: 'lambda_handler',
      timeout: Duration.seconds(60),
      role: lambdaExecRole,
      layers: [props.lambdaLayer],
      environment: {
        EVENTBUS_NAME: props.eventBus.eventBusName,
        EVENT_SOURCE: props.controlPlaneEventSource,
        TENANT_DETAILS_TABLE: props.tables.tenantDetails.tableName,
      },
    });

    // Tasks:
    // Error handler task.
    const errorHandlerTask = new tasks.LambdaInvoke(this, 'ErrorHandlerTask', {
      lambdaFunction: errorHandler,
    });

    // Initiate Onboarding task.
    const initiateOnboardingTask = new tasks.LambdaInvoke(this, 'InitiateOnboardingTask', {
      lambdaFunction: initiateOnboarding,
      integrationPattern: stepfunctions.IntegrationPattern.REQUEST_RESPONSE,
      outputPath: '$.Payload',
      taskTimeout: stepfunctions.Timeout.duration(cdk.Duration.minutes(5)),
    }).addCatch(errorHandlerTask);

    // Provision Onboarding task.
    const provisionOnboardingTask = new tasks.LambdaInvoke(this, 'ProvisionOnboardingTask', {
      lambdaFunction: provisionOnboarding,
      integrationPattern: stepfunctions.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
      inputPath: '$',
      payload: stepfunctions.TaskInput.fromObject({
        taskToken: stepfunctions.JsonPath.taskToken, // Save token to external checkpointing system, e.g., DynamoDB
        'previousOutput.$': '$',
      }),
      taskTimeout: stepfunctions.Timeout.duration(cdk.Duration.hours(2)),
    }).addCatch(errorHandlerTask);

    // Complete Onboarding task.
    const completeOnboardingTask = new tasks.LambdaInvoke(this, 'CompleteOnboardingTask', {
      lambdaFunction: completeOnboarding,
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
    NagSuppressions.addResourceSuppressions(
      stateMachine,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'Wildcard required in order pass tenantId in path.',
          appliesTo: [
            'Resource::*',
            `Resource::<ControlPlaneonboardingstepfunctionsInitiateOnboardingF9A53C91.Arn>:*`,
            `Resource::<ControlPlaneonboardingstepfunctionsProvisionOnboardingE086955D.Arn>:*`,
            `Resource::<ControlPlaneonboardingstepfunctionsCompleteOnboarding70D66CB2.Arn>:*`,
            `Resource::<ControlPlaneonboardingstepfunctionsErrorHandlerA8C5CE51.Arn>:*`,
          ],
        },
      ],
      true
    );

    const lambdaEventHandlerExecRole = new Role(this, 'lambdaEventHandlerExecRole', {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
    });
    lambdaEventHandlerExecRole.addManagedPolicy(
      ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
    );
    lambdaEventHandlerExecRole.addManagedPolicy(
      ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLambdaInsightsExecutionRolePolicy')
    );
    lambdaEventHandlerExecRole.addManagedPolicy(
      ManagedPolicy.fromAwsManagedPolicyName('AWSXrayWriteOnlyAccess')
    );
    props.tables.tenantDetails.grantReadWriteData(lambdaEventHandlerExecRole);

    NagSuppressions.addResourceSuppressions(
      lambdaEventHandlerExecRole,
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
      true
    );
    const policyStatement = new PolicyStatement({
      actions: ['states:SendTaskSuccess', 'states:SendTaskFailure'],
      resources: [stateMachine.stateMachineArn],
    });
    lambdaEventHandlerExecRole.addToPolicy(policyStatement);

    // Onboarding Event bridge handler.
    const onboardingEventsHandler = new PythonFunction(this, 'OnboardingEventsHandler', {
      entry: path.join(__dirname, '../../resources/functions/'),
      runtime: Runtime.PYTHON_3_12,
      index: 'onboarding_events_handler.py',
      handler: 'lambda_handler',
      timeout: Duration.seconds(60),
      role: lambdaEventHandlerExecRole,
      layers: [props.lambdaLayer],
      environment: {
        TENANT_DETAILS_TABLE: props.tables.tenantDetails.tableName,
      },
    });
    this.lambdaEventTarget = new LambdaFunction(onboardingEventsHandler);
  }
}

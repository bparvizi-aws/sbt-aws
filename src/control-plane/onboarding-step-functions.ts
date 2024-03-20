// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import * as cdk from 'aws-cdk-lib';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as stepfunctions from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { NagSuppressions } from 'cdk-nag';
import { Construct } from 'constructs';

export interface OnboardingStepFunctionsProps {
  readonly initiateOnboarding: PythonFunction;
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
      taskTimeout: stepfunctions.Timeout.duration(cdk.Duration.minutes(5)),
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
    const definition = initiateOnboardingTask.next(completeOnboardingTask);
    const stepfunction = new stepfunctions.StateMachine(this, 'OnboardingStateMachine', {
      definitionBody: stepfunctions.DefinitionBody.fromChainable(definition),
      logs: {
        destination: logGroup,
        level: stepfunctions.LogLevel.ALL,
      },
      tracingEnabled: true,
    });

    NagSuppressions.addResourceSuppressions(
      stepfunction,
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

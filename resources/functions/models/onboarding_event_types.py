# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from enum import Enum


class OnboardingEventTypes(Enum):
    ONBOARDING_INITIATED = 'Onboarding Initiated'
    ONBOARDING_VALID = "Onboarding Validated"
    ONBOARDING_DEPLOYED = "Onboarding Deployed"
    ONBOARDING_PROVISIONED = "Onboarding Provisioned"
    ONBOARDING_COMPLETED = "Onboarding Completed"
    ONBOARDING_FAILED = "Onboarding Failed"

    def __str__(self):
        return str(self.value)

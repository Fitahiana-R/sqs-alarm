# Alias pour déployer en DEV vers AWS réel (mode PRODUCTION)
alias sam-dev='sam build && sam deploy \
  --stack-name producer-sqs-alarm-dev \
  --region eu-west-1 \
  --profile 879381257984_AWS-Sandbox-AdminAccess \
  --capabilities CAPABILITY_NAMED_IAM \
  --resolve-s3 \
  --no-confirm-changeset \
  --parameter-overrides EnvironmentName=dev client=mgitservice LocalStackTest=false AlarmThreshold=100 PeriodAlarm=300'
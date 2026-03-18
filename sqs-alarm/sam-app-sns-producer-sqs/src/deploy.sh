#!/bin/bash
set -e

ENDPOINT="http://localhost:4566"
ROLE_NAME="lambda-execution-role"
FUNCTION_NAME="test-handler"
POLICY_NAME="lambda-logs-policy"

echo "🚀 Déploiement LocalStack..."

# Credentials
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=eu-west-1

# 1. IAM Role
aws --endpoint-url=$ENDPOINT iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Principal":{"Service":"lambda.amazonaws.com"},
      "Action":"sts:AssumeRole"
    }]
  }' 2>/dev/null || echo "✅ Rôle existant"

# 2. IAM Policy
POLICY_ARN=$(aws --endpoint-url=$ENDPOINT iam create-policy \
  --policy-name $POLICY_NAME \
  --policy-document '{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
      "Resource":"arn:aws:logs:*:*:*"
    }]
  }' --query 'Policy.Arn' --output text 2>/dev/null) || echo "✅ Policy existante"

# attaché le policy 
aws --endpoint-url=$ENDPOINT iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn $POLICY_ARN 2>/dev/null || echo "✅ Policy attachée"

# 3.  création Log Group
aws --endpoint-url=$ENDPOINT logs create-log-group \
  --log-group-name /aws/lambda/$FUNCTION_NAME 2>/dev/null || echo "✅ Log group existant"

# 4. Packaging
echo "📦 Packaging..."
rm -rf package lambda.zip
mkdir package
pip install boto3 -t package/
cp app_sqs.py package/
cd package && zip -r ../lambda.zip . && cd ..

# 5. Lambda (create or update)
aws --endpoint-url=$ENDPOINT lambda create-function \
  --function-name $FUNCTION_NAME \
  --runtime python3.11 \
  --handler app_sqs.lambda_handler \
  --role arn:aws:iam::000000000000:role/$ROLE_NAME \
  --zip-file fileb://lambda.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment Variables="{
    SNS_TOPIC_ARN=arn:aws:sns:eu-west-1:000000000000:test-topic,
    SNS_ENDPOINT=http://localhost:4566,
    LOCALSTACK_TEST=true
  }" 2>/dev/null || aws --endpoint-url=$ENDPOINT lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://lambda.zip

echo "Déploiement terminé !"
echo "Tester avec : aws --endpoint-url=$ENDPOINT lambda invoke --function-name $FUNCTION_NAME --payload file://test_sqs_event.json --cli-binary-format raw-in-base64-out out.json"
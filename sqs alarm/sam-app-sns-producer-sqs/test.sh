export LOCALSTACK_TEST="true"
export SNS_ENDPOINT="http://localhost:4566"
export SNS_TOPIC_ARN="arn:aws:sns:eu-west-1:000000000000:test-topic"

sam build && sam local invoke SlackDistributorFunction --event src/test_sqs_event.json
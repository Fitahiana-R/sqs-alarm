##################################
docker run --rm -it \
  -p 4566:4566 \
  -p 4510-4559:4510-4559 \
  -e SERVICES=lambda,sns,logs,iam,cloudwatch,sqs \
  -e DEBUG=1 \
  -e LAMBDA_EXECUTOR=docker-reuse \
  -v "/var/run/docker.sock:/var/run/docker.sock" \
  localstack/localstack:latest

# 1. Packager manuellement
pip install boto3 -t package/
cp app_sqs.py package/
cd package && zip -r ../lambda.zip . && cd ..

# 2. Déployer manuellement
awslocal lambda create-function \
  --function-name test-handler \
  --runtime python3.11 \
  --handler app_sqs.lambda_handler \
  --role arn:aws:iam::000000000000:role/lambda-execution-role \
  --zip-file fileb://lambda.zip


# Vérifier que la Lambda est déployée
aws --endpoint-url=http://localhost:4566 lambda list-functions

# Tester directement la Lambda
aws --endpoint-url=http://localhost:4566 lambda invoke \
  --function-name test-handler \
  --payload '{"detail":{}}' \
  --cli-binary-format raw-in-base64-out \
  out.json && cat out.json


# Voir le résultat
cat response.json
# → {"status": "sent", ...}

 ################
 #####Installation permanente de awslocal
 ###############
 # Credentials AWS fictifs pour LocalStack
echo 'export AWS_ACCESS_KEY_ID=test' >> ~/.zshrc
echo 'export AWS_SECRET_ACCESS_KEY=test' >> ~/.zshrc
echo 'export AWS_DEFAULT_REGION=eu-west-1' >> ~/.zshrc

# Alias pratique awslocal
echo 'alias awslocal="aws --endpoint-url=http://localhost:4566"' >> ~/.zshrc
source ~/.zshrc
awslocal iam list-roles
# → Doit afficher une liste JSON sans erreur


# Tester directement la Lambda
awslocal lambda invoke \
  --function-name test-handler \
  --payload file://test_sqs_event.json \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json

#liste function 
awslocal lambda list-functions
import os
import json
import boto3
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Parsing noms SQS ---

class SqsQueueParser(ABC):
    @abstractmethod
    def parse(self, queue_name: str):
        pass

class StandardDashParser(SqsQueueParser):
    """Format : client-env-app-nom-complet"""
    def parse(self, queue_name: str):
        if not queue_name or queue_name == "Inconnu":
            return "inconnu", "inconnu", "inconnu"
            
        parts = queue_name.split("-")
        if len(parts) >= 3:
            client = parts[0]
            environnement = parts[1]
            app_name = "-".join(parts[2:])  # Gère les noms d'app avec tirets
            return client, app_name, environnement
        return "inconnu", "inconnu", "inconnu"

def lambda_handler(event, context):
    # Mode test LocalStack : court-circuite l'envoi SNS
    if os.environ.get("LOCALSTACK_TEST") == "true":
        logger.info(f"[TEST MODE] Message simulé : {json.dumps(event)}")
        return {"status": "test-sent", "event": event}
    
    # Configuration SNS avec fallback pour LocalStack
    sns_endpoint = os.environ.get("SNS_ENDPOINT") or "http://localhost:4566"
    sns_client = boto3.client("sns", endpoint_url=sns_endpoint)
    
    try:
        SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
    except KeyError:
        logger.error("Variable d'environnement SNS_TOPIC_ARN manquante")
        return {"status": "error", "message": "SNS_TOPIC_ARN not set"}
    
    logger.info(f"Événement reçu : {json.dumps(event)}")
    
    # --- Extraction sécurisée des infos de l'alarme ---
    detail = event.get("detail", {})
    alarm_name = detail.get("alarmName", "Inconnu")
    state = detail.get("state", {})
    new_state = state.get("value", "Inconnu")
    reason = state.get("reason", "Non spécifiée")
    
    # --- Récupération du QueueName avec gestion d'erreur ---
    queue_name = "Inconnu"
    try:
        metrics = detail.get("configuration", {}).get("metrics", [])
        for m in metrics:
            metric_stat = m.get("metricStat", {})
            metric = metric_stat.get("metric", {})
            dimensions = metric.get("dimensions", {})
            if "QueueName" in dimensions:
                queue_name = dimensions["QueueName"]
                break
    except Exception as e:
        logger.warning(f"Erreur lors de l'extraction depuis metrics: {e}")
    
    # Fallback via la description
    if queue_name == "Inconnu":
        try:
            description = detail.get("configuration", {}).get("description", "")
            if description and ("file" in description.lower() or "queue" in description.lower()):
                # Extraction plus robuste
                if ":" in description:
                    queue_name = description.split(":")[-1].strip()
                    logger.info(f"Queue name récupéré depuis description : {queue_name}")
        except Exception as e:
            logger.warning(f"Erreur fallback description: {e}")

    logger.info(f"Alarme: {alarm_name} | État: {new_state} | Queue: {queue_name}")

    # --- Parsing et Enrichissement ---
    parser = StandardDashParser()
    client, app_name, environnement = parser.parse(queue_name)

    # --- Construction du message ---
    subject = f"[{client.upper()}] - [{app_name.upper()}] - [{environnement.upper()}]"
    
    message_body = {
        "description": f"Seuil de messages dépassé dans la file SQS : {queue_name}",
        "type": "WARNING",
        "plateforme": client,
        "application": app_name,
        "environnement": environnement,
        "queue_name": queue_name,
        "details": reason,
        "timestamp": event.get("time"),
        "metric": "ApproximateNumberOfMessagesVisible"
    }

    try:
        target = "slack"
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=json.dumps(message_body),
            MessageAttributes={
                "destinataire": {"DataType": "String", "StringValue": target}
            },
        )
        logger.info("Message SNS publié avec succès")
        return {"status": "sent"}
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi SNS: {e}")
        return {"status": "error", "message": str(e)}
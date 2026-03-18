import os
import json
import boto3
import logging
import base64
import gzip
from abc import ABC, abstractmethod

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Abstraction du Parsing
class LogGroupParser(ABC):
    """Interface pour définir comment extraire les infos du nom du Log Group."""

    @abstractmethod
    def parse(self, log_name: str):
        """
        Extrait les métadonnées à partir du nom d'un groupe de logs.

        Args:
            log_name (str): Le nom complet du Log Group CloudWatch.

        Returns:
            tuple: Un tuple contenant les informations extraites (ex: service, environnement).

        Raises:
            NotImplementedError: Si la sous-classe ne définit pas cette méthode.
        """
        pass  # aucune implémentation par défaut.


class StandardPathParser(LogGroupParser):
    """Format: /entreprise/plateforme/app_name"""

    def parse(self, log_name: str):
        """Methode pour parser le nom du log group pour obtenir le nom de l'application et la plateforme pour usage dans les alerts

        Args:
            log_name (str): nom du log group

        Returns:
            str, str: nom de l'application et la plateforme
        """
        parts = log_name.strip("/").split("/")
        if len(parts) >= 3:
            client = parts[0]
            environnement = parts[1]
            app_name = parts[2]
            return client, app_name, environnement
        return "client-inconnue", "app-inconnue", "plateforme-inconnue"



def lambda_handler(event, context):

    sns_client = boto3.client("sns")
    SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]

    print(f"Événement reçu : {event}")

    # Décoder base64
    compressed_payload = base64.b64decode(event['awslogs']['data'])
    # Décompresser GZIP
    uncompressed_payload = gzip.decompress(compressed_payload)
    # Parser le JSON
    log_data = json.loads(uncompressed_payload)

    log_group_name = log_data['logGroup']

    message_content = log_data['logEvents'][0]['message']
    message_upper = message_content.upper()
    
    type_alert=""
    if "FATAL" in message_upper or "CRITICAL" in message_upper:
        type_alert = "FATAL"
    elif "ERROR" in message_upper:
        type_alert = "ERROR"
    elif "WARNING" in message_upper:
        type_alert = "WARNING"
    else:
        type_alert = "INFO"

    if not type_alert:
        logger.info("Pas de type d'alert trouvé")

    logger.info(
        f"type d\'alert: {type_alert} LogGroup: {log_group_name}"
    )

    parser_standard = StandardPathParser()
    client, app_name, environnement = parser_standard.parse(log_group_name)

    # Construction du message à envoyer vers sns
    subject = f"[{client.upper()}] - [{app_name.upper()}] - [{environnement.upper()}]"
    message_body = {
        "description": f"Erreur détecté dans le log group \"{log_group_name}\".",
        "type": type_alert,
        "plateforme": client,
        "application": app_name,
        "environnement": environnement,
        "log_group": log_group_name,
        "details": message_content,
    }

    target = "slack"
    sns_client.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject,
        Message=json.dumps(message_body),
        MessageAttributes={"destinataire": {"DataType": "String", "StringValue": target}},
    )
        

    return {"status": "sent"}

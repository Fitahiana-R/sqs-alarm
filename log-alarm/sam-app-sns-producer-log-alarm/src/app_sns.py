import os
import json
import boto3
import logging
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
    # Extraction des infos de l'alarme
    detail = event.get("detail", {})
    alarm_name = detail.get("alarmName")
    new_state = detail.get("state", {}).get("value")
    reason = detail.get("state", {}).get("reason")

    metrics = event["detail"]["configuration"]["metrics"]
    log_group_name = "Inconnu"

    for m in metrics:
        if "metricStat" in m:
            dimensions = m["metricStat"]["metric"].get("dimensions", {})
            if "LogGroupName" in dimensions:
                log_group_name = dimensions["LogGroupName"]
                break

    config = event["detail"]["configuration"]
    if log_group_name == "Inconnu":
        description = config.get("description", "Inconnu")
        if "group:" in description:
            log_group_name = description.split("group:")[1].strip()
            print(
                f"Log group name récupéré depuis description : {log_group_name}"
            )


    logger.info(
        f"Alarme: {alarm_name} | État: {new_state} | LogGroup: {log_group_name}"
    )

    parser_standard = StandardPathParser()
    client, app_name, environnement = parser_standard.parse(log_group_name)

    # Construction du message à envoyer vers sns
    subject = f"[{client.upper()}] - [{app_name.upper()}] - [{environnement.upper()}]"
    message_body = {
        "description": f"Aucun log reçu sur le groupe de logs \"{log_group_name}\".",
        "type": "FATAL",
        "plateforme": client,
        "application": app_name,
        "environnement": environnement,
        "log_group": log_group_name,
        "details": reason,
        "timestamp": event.get("time"),
    }


    target = "slack"
    sns_client.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject,
        Message=json.dumps(message_body),
        MessageAttributes={"destinataire": {"DataType": "String", "StringValue": target}},
    )
        

    return {"status": "sent"}

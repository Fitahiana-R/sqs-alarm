from unittest.mock import patch, MagicMock, Mock

from src.app_sns import StandardPathParser

def test_parser():
    log_group_nom = "/client/plateforme/app"

    parser = StandardPathParser()

    aps, plat = parser.parse(log_group_nom)
    assert aps, plat == ["app", "plateforme"]
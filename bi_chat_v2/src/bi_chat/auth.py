from __future__ import annotations
from typing import Optional, Tuple, Dict, Any
import base64
import json
import requests
from bi_chat.config import Settings


def connecter_keycloak(
    login: str,
    password: str,
    settings: Settings,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        url = (
            f"{settings.keycloak_url}/realms/"
            f"{settings.keycloak_realm}/protocol/openid-connect/token"
        )
        data = {
            "grant_type": "password",
            "client_id": settings.keycloak_client_id,
            "client_secret": settings.keycloak_client_secret,
            "username": login,
            "password": password,
        }
        response = requests.post(url, data=data, timeout=10)

        if response.status_code == 401:
            return None, "Login ou mot de passe incorrect."
        if response.status_code != 200:
            return None, f"Erreur Keycloak {response.status_code}"

        access_token = response.json()["access_token"]
        payload = access_token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        token_info = json.loads(base64.b64decode(payload).decode("utf-8"))

        realm_roles = token_info.get("realm_access", {}).get("roles", [])
        roles_metier = {"finance", "rh", "marketing", "admin"}
        role_trouve = next((r for r in realm_roles if r in roles_metier), None)

        if role_trouve is None:
            return None, "Aucun rôle métier assigné dans Keycloak."

        nom = token_info.get("name") or token_info.get("preferred_username") or login

        return {"login": login, "nom": nom, "role": role_trouve, "token": access_token}, None

    except requests.exceptions.ConnectionError:
        return None, "Impossible de joindre Keycloak. Vérifiez que Docker est lancé."
    except Exception as e:
        return None, f"Erreur : {str(e)}"
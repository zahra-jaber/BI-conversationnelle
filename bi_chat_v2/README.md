# 💬 BI Chat — Interface BI Conversationnelle (Projet 5)

Interrogez vos données en français. L'agent traduit vos questions en SQL,
les exécute sur PostgreSQL et vous répond avec des graphiques.

## Architecture

```
Utilisateur (français)
        ↓
Keycloak (authentification + rôle)
        ↓
Streamlit (interface chat)
        ↓
LangChain + Ollama (question → SQL)
        ↓
Validation SQL (sqlglot)
        ↓
Cache sémantique (SQLite + embeddings)
        ↓
PostgreSQL (schémas ecommerce + rh)
        ↓
Plotly (graphiques automatiques)
```

## Prérequis

- Python 3.11+
- Docker + Docker Compose
- Ollama (https://ollama.com)
- Datasets : Olist (Kaggle) + IBM HR (Kaggle)

## Installation

### 1. Cloner et préparer

```bash
git clone <url>
cd bi_chat_v2
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

### 2. Configurer l'environnement

```bash
cp .env.example .env
# Éditez .env avec votre KEYCLOAK_CLIENT_SECRET
```

### 3. Lancer PostgreSQL + Keycloak

```bash
docker-compose up -d
```

### 4. Configurer Keycloak (http://localhost:8180)

1. Créer le Realm `bi-chat`
2. Créer les rôles : `finance`, `rh`, `marketing`, `admin`
3. Créer les utilisateurs et assigner leurs rôles
4. Créer le client `bi-chat-app` → copier le secret dans `.env`

### 5. Installer Ollama et les modèles

```bash
ollama pull llama3
ollama pull nomic-embed-text
```

### 6. Charger les données

```bash
# Télécharger Olist depuis Kaggle et IBM HR depuis Kaggle
python scripts/load_data.py --olist ./data/olist --ibmhr ./data/WA_Fn-UseC_-HR-Employee-Attrition.csv
```

### 7. Lancer l'application

```bash
streamlit run app.py
```

## Rôles et accès

| Rôle | Dataset | Tables accessibles |
|---|---|---|
| finance | Olist | orders, payments, items, products |
| marketing | Olist | customers, products, sellers, geo |
| rh | IBM HR | employees, departments, evaluations |
| admin | Tout | Toutes les tables |

## Sécurité — 3 niveaux

1. **Keycloak** : authentification login/mot de passe, rôle non modifiable
2. **Prompt filtering** : le LLM ne voit que les tables de son rôle
3. **PostgreSQL RLS** : droits SQL par rôle au niveau base de données

## Améliorations vs projet original

| Aspect | Avant | Après |
|---|---|---|
| Auth | Menu déroulant libre | Keycloak login/password |
| Rôle | Choisi par l'utilisateur | Assigné automatiquement |
| Données RH | Clients Olist (incohérent) | IBM HR Dataset |
| Réponse | Phrase générique | Réponse LLM naturelle |
| Graphiques | Bar/Line uniquement | Bar/Line/Pie/Scatter |
| Schémas | public uniquement | ecommerce + rh séparés |

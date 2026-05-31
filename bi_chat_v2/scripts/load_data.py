"""
Script de chargement des datasets dans PostgreSQL.
Usage:
    python scripts/load_data.py --olist /chemin/vers/olist --ibmhr /chemin/vers/WA_Fn-UseC_-HR-Employee-Attrition.csv
"""
import argparse
import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_URL = (
    f"postgresql+psycopg://{os.getenv('PG_USER', 'bi_user')}:"
    f"{os.getenv('PG_PASSWORD', 'bi_password')}@"
    f"{os.getenv('PG_HOST', 'localhost')}:"
    f"{os.getenv('PG_PORT', '5432')}/"
    f"{os.getenv('PG_DATABASE', 'bi_chat')}"
)

OLIST_FILES = {
    "olist_customers_dataset": "olist_customers_dataset.csv",
    "olist_orders_dataset": "olist_orders_dataset.csv",
    "olist_order_items_dataset": "olist_order_items_dataset.csv",
    "olist_order_payments_dataset": "olist_order_payments_dataset.csv",
    "olist_products_dataset": "olist_products_dataset.csv",
    "olist_sellers_dataset": "olist_sellers_dataset.csv",
    "olist_geolocation_dataset": "olist_geolocation_dataset.csv",
    "product_category_name_translation": "product_category_name_translation.csv",
}


def load_olist(olist_dir: str, engine):
    print("\n📦 Chargement du dataset Olist (ecommerce)...")
    for table, filename in OLIST_FILES.items():
        filepath = os.path.join(olist_dir, filename)
        if not os.path.exists(filepath):
            print(f"  ⚠️  Fichier manquant : {filename}")
            continue
        df = pd.read_csv(filepath)
        df.to_sql(table, engine, schema="ecommerce", if_exists="replace", index=False)
        print(f"  ✅ {table} — {len(df)} lignes chargées")


def load_ibmhr(csv_path: str, engine):
    print("\n👥 Chargement du dataset IBM HR (rh)...")
    if not os.path.exists(csv_path):
        print(f"  ⚠️  Fichier manquant : {csv_path}")
        return

    df = pd.read_csv(csv_path)

    # Nettoyer les noms de colonnes
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    # Mapper les colonnes IBM HR vers notre schéma
    column_map = {
        "age": "age",
        "attrition": "attrition",
        "businesstravel": "business_travel",
        "dailyrate": "daily_rate",
        "department": "department",
        "distancefromhome": "distance_from_home",
        "education": "education",
        "educationfield": "education_field",
        "environmentsatisfaction": "environment_satisfaction",
        "gender": "gender",
        "hourlyrate": "hourly_rate",
        "jobinvolvement": "job_involvement",
        "joblevel": "job_level",
        "jobrole": "job_role",
        "jobsatisfaction": "job_satisfaction",
        "maritalstatus": "marital_status",
        "monthlyincome": "monthly_income",
        "monthlyrate": "monthly_rate",
        "numcompaniesworked": "num_companies_worked",
        "over18": "over18",
        "overtime": "over_time",
        "percentsalaryhike": "percent_salary_hike",
        "performancerating": "performance_rating",
        "relationshipsatisfaction": "relationship_satisfaction",
        "standardhours": "standard_hours",
        "stockoptionlevel": "stock_option_level",
        "totalworkingyears": "total_working_years",
        "trainingtimeslastyear": "training_times_last_year",
        "worklifebalance": "work_life_balance",
        "yearsatcompany": "years_at_company",
        "yearsincurrentrole": "years_in_current_role",
        "yearssincelastpromotion": "years_since_last_promotion",
        "yearswithcurrmanager": "years_with_curr_manager",
    }

    df = df.rename(columns=column_map)
    cols = [c for c in column_map.values() if c in df.columns]
    df = df[cols]

    df.to_sql("employees", engine, schema="rh", if_exists="replace", index=True, index_label="employee_id")
    print(f"  ✅ rh.employees — {len(df)} lignes chargées")

    # Créer la table departments depuis les données
    depts = df[["department"]].drop_duplicates().reset_index(drop=True)
    depts.columns = ["department_name"]
    depts["manager_name"] = "N/A"
    depts.to_sql("departments", engine, schema="rh", if_exists="replace", index=True, index_label="department_id")
    print(f"  ✅ rh.departments — {len(depts)} lignes chargées")

    print("  ✅ rh.evaluations — table vide (à remplir manuellement)")


def main():
    parser = argparse.ArgumentParser(description="Chargement des datasets BI Chat")
    parser.add_argument("--olist", help="Dossier contenant les CSV Olist", default=None)
    parser.add_argument("--ibmhr", help="Chemin vers le CSV IBM HR Attrition", default=None)
    args = parser.parse_args()

    engine = create_engine(DB_URL)
    print(f"🔌 Connexion à PostgreSQL : {DB_URL}")

    if args.olist:
        load_olist(args.olist, engine)
    if args.ibmhr:
        load_ibmhr(args.ibmhr, engine)

    if not args.olist and not args.ibmhr:
        print("❌ Spécifiez --olist et/ou --ibmhr")
        print("Exemple : python scripts/load_data.py --olist ./data/olist --ibmhr ./data/WA_Fn-UseC_-HR-Employee-Attrition.csv")


if __name__ == "__main__":
    main()

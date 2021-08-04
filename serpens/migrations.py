from serpens import database, envvars


def migrate(event, context):
    print("Migrating database...")
    database.migrate(envvars.get("DATABASE_URL"), "./")
    print("Migration successful")

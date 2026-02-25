import os
import sys
import uuid
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.config.settings import settings


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL não está definido no ambiente")
    return database_url


def upsert_instagram_account(conn, account_data: dict) -> None:
    """
    Insere ou atualiza um registro na tabela instagram_accounts.
    """
    query = """
    INSERT INTO instagram_accounts (
        id,
        owner_id,
        phone_number,
        access_token,
        api_id,
        app_secret,
        verify_token
    ) VALUES (
        %(id)s,
        %(owner_id)s,
        %(phone_number)s,
        %(access_token)s,
        %(api_id)s,
        %(app_secret)s,
        %(verify_token)s
    )
    ON CONFLICT (owner_id)
    DO UPDATE SET
        phone_number = EXCLUDED.phone_number,
        access_token = EXCLUDED.access_token,
        api_id = EXCLUDED.api_id,
        app_secret = EXCLUDED.app_secret,
        verify_token = EXCLUDED.verify_token,
        updated_at = NOW();
    """
    
    with conn.cursor() as cur:
        try:
            # Garante que o ID exista (se não fornecido, gera um novo UUID)
            if "id" not in account_data:
                account_data["id"] = str(uuid.uuid4())
            
            cur.execute(query, account_data)
            conn.commit()
            print(f"✅ Conta Instagram {account_data['owner_id']} inserida/atualizada com sucesso.")
        except Exception as e:
            conn.rollback()
            print(f"❌ Erro ao inserir conta Instagram: {e}")
            raise


def main() -> None:
    load_dotenv()

    # Carrega valores de settings.instagram
    instagram_settings = settings.instagram

    access_token = instagram_settings.access_token
    app_id = instagram_settings.app_id
    app_secret = instagram_settings.app_secret
    verify_token = instagram_settings.verify_token
    
    # Valida dados obrigatórios
    if not access_token:
        print("⚠️ INSTAGRAM_ACCESS_TOKEN não definido. Pulando seed.")
        return

    owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"  # ID fixo para exemplo/desenvolvimento
    
    # Dados de exemplo para seed
    # Em produção, isso viria de variáveis de ambiente ou input seguro
    phone_number = os.getenv("SEED_PHONE_NUMBER", "+5511999999999")

    account_data = {
        "id": str(uuid.uuid4()),  # Gera um ID novo (será ignorado se já existir conflito, mas o ON CONFLICT atualiza)
        # Nota: Se quisermos manter o ID original no update, precisaríamos buscar antes.
        # Mas como o ID é PK e owner_id é UNIQUE, o ON CONFLICT atualiza os outros campos.
        # O ID original do banco será mantido pois não está no DO UPDATE SET.
        
        "owner_id": owner_id,
        "phone_number": phone_number,
        "access_token": access_token,
        "api_id": app_id,
        "app_secret": app_secret,
        "verify_token": verify_token
    }

    try:
        database_url = get_database_url()
        conn = psycopg2.connect(database_url)
        print("🔌 Conectado ao banco de dados.")
        
        upsert_instagram_account(conn, account_data)
        
        conn.close()
        print("👋 Conexão encerrada.")

    except Exception as e:
        print(f"🚨 Erro fatal no seed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

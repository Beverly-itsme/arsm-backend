import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Em desenvolvimento local usa SQLite (não precisa de instalar MySQL).
    # Em produção (PythonAnywhere), define a variável de ambiente DATABASE_URL
    # com a ligação MySQL, ex:
    # mysql+pymysql://utilizador:password@host/nome_da_bd
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///arsm.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "muda-esta-chave-em-producao")
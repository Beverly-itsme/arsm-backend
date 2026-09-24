"""
Script para criar a conta de administrador.
Corre isto UMA VEZ, depois de teres as tabelas criadas:

    python criar_admin.py
"""
import getpass
from werkzeug.security import generate_password_hash

from app import app
from models import db, Administrador


def criar_admin():
    with app.app_context():
        username = input("Nome de utilizador do admin: ").strip()

        existente = Administrador.query.filter_by(username=username).first()
        if existente:
            print(f"Já existe um administrador com o username '{username}'.")
            return

        password = getpass.getpass("Palavra-passe: ")
        confirmacao = getpass.getpass("Confirma a palavra-passe: ")

        if password != confirmacao:
            print("As palavras-passe não coincidem. Tenta outra vez.")
            return

        if len(password) < 6:
            print("A palavra-passe deve ter pelo menos 6 caracteres.")
            return

        admin = Administrador(
            username=username,
            password_hash=generate_password_hash(password),
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Administrador '{username}' criado com sucesso!")


if __name__ == "__main__":
    criar_admin()
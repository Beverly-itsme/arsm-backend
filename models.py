import uuid as uuid_lib
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Utilizador(db.Model):
    """Representa um dispositivo/UUID anónimo — nunca uma pessoa identificada."""
    __tablename__ = "utilizador"

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False,
                      default=lambda: str(uuid_lib.uuid4()))
    faixa_etaria = db.Column(db.String(20), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    avaliacoes = db.relationship("Avaliacao", backref="utilizador", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "faixa_etaria": self.faixa_etaria,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }


class Avaliacao(db.Model):
    """Uma sessão completa de autoavaliação (PHQ-9 + GAD-7)."""
    __tablename__ = "avaliacao"

    id = db.Column(db.Integer, primary_key=True)
    utilizador_id = db.Column(db.Integer, db.ForeignKey("utilizador.id"), nullable=False)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)

    pontuacao_phq9 = db.Column(db.Integer, nullable=True)
    pontuacao_gad7 = db.Column(db.Integer, nullable=True)
    categoria_risco_phq9 = db.Column(db.String(30), nullable=True)
    categoria_risco_gad7 = db.Column(db.String(30), nullable=True)
    risco_urgente = db.Column(db.Boolean, default=False)

    respostas = db.relationship("RespostaItem", backref="avaliacao", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "utilizador_id": self.utilizador_id,
            "data_hora": self.data_hora.isoformat() if self.data_hora else None,
            "pontuacao_phq9": self.pontuacao_phq9,
            "pontuacao_gad7": self.pontuacao_gad7,
            "categoria_risco_phq9": self.categoria_risco_phq9,
            "categoria_risco_gad7": self.categoria_risco_gad7,
            "risco_urgente": self.risco_urgente,
        }


class RespostaItem(db.Model):
    """Cada resposta individual a uma pergunta do PHQ-9 ou GAD-7."""
    __tablename__ = "resposta_item"

    id = db.Column(db.Integer, primary_key=True)
    avaliacao_id = db.Column(db.Integer, db.ForeignKey("avaliacao.id"), nullable=False)
    tipo_questionario = db.Column(db.String(10), nullable=False)  # "PHQ9" ou "GAD7"
    numero_pergunta = db.Column(db.Integer, nullable=False)
    valor_resposta = db.Column(db.Integer, nullable=False)  # 0 a 3


class FeedbackUsabilidade(db.Model):
    """Feedback opcional recolhido durante os testes de usabilidade."""
    __tablename__ = "feedback_usabilidade"

    id = db.Column(db.Integer, primary_key=True)
    avaliacao_id = db.Column(db.Integer, db.ForeignKey("avaliacao.id"), nullable=True)
    facilidade_uso = db.Column(db.Integer, nullable=True)  # escala 1-5
    comentario = db.Column(db.Text, nullable=True)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)


class Administrador(db.Model):
    """Única conta de acesso à área de administração."""
    __tablename__ = "administrador"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
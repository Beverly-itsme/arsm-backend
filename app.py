from functools import wraps

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flasgger import Swagger
from werkzeug.security import check_password_hash

from config import Config
from models import db, Utilizador, Avaliacao, RespostaItem, Administrador
from scoring import processar_avaliacao_completa

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
CORS(app)  # permite que a app web (noutro domínio) fale com esta API
swagger = Swagger(app, template={
    "info": {
        "title": "API ARSM",
        "description": "API do sistema de rastreio de saúde mental (Depressão e Ansiedade)",
        "version": "1.0.0",
    }
})

with app.app_context():
    db.create_all()  # cria as tabelas se ainda não existirem


# ---------------------------------------------------------------------------
# Sprint 1 — Utilizador (UUID anónimo)
# ---------------------------------------------------------------------------

@app.route("/api/utilizador", methods=["POST"])
def criar_ou_obter_utilizador():
    """
    Cria um novo utilizador anónimo, ou devolve o existente se o UUID
    já tiver sido enviado antes (para reconhecer o mesmo dispositivo).
    ---
    tags:
      - Utilizador
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            uuid:
              type: string
              description: UUID já guardado no dispositivo (opcional na primeira vez)
            faixa_etaria:
              type: string
              example: "18-24"
    responses:
      200:
        description: Utilizador criado ou encontrado
    """
    dados = request.get_json() or {}
    uuid_recebido = dados.get("uuid")
    faixa_etaria = dados.get("faixa_etaria")

    utilizador = None
    if uuid_recebido:
        utilizador = Utilizador.query.filter_by(uuid=uuid_recebido).first()

    if utilizador is None:
        utilizador = Utilizador(uuid=uuid_recebido, faixa_etaria=faixa_etaria)
        db.session.add(utilizador)
        db.session.commit()
    elif faixa_etaria and not utilizador.faixa_etaria:
        utilizador.faixa_etaria = faixa_etaria
        db.session.commit()

    return jsonify(utilizador.to_dict()), 200


@app.route("/api/utilizador/<uuid>/historico", methods=["GET"])
def obter_historico(uuid):
    """
    Devolve o histórico de avaliações de um utilizador (RF15/RF16).
    ---
    tags:
      - Utilizador
    parameters:
      - in: path
        name: uuid
        type: string
        required: true
    responses:
      200:
        description: Lista de avaliações anteriores
      404:
        description: Utilizador não encontrado
    """
    utilizador = Utilizador.query.filter_by(uuid=uuid).first()
    if not utilizador:
        return jsonify({"erro": "Utilizador não encontrado"}), 404

    avaliacoes = Avaliacao.query.filter_by(utilizador_id=utilizador.id)\
        .order_by(Avaliacao.data_hora.asc()).all()

    return jsonify([a.to_dict() for a in avaliacoes]), 200


# ---------------------------------------------------------------------------
# Sprint 2 — Avaliação (scoring PHQ-9 + GAD-7)
# ---------------------------------------------------------------------------

@app.route("/api/avaliacao", methods=["POST"])
def submeter_avaliacao():
    """
    Submete uma avaliação completa (PHQ-9 + GAD-7) e devolve o resultado.
    ---
    tags:
      - Avaliação
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [uuid, respostas_phq9, respostas_gad7]
          properties:
            uuid:
              type: string
            respostas_phq9:
              type: array
              items:
                type: integer
              example: [1, 1, 0, 2, 1, 0, 1, 0, 0]
            respostas_gad7:
              type: array
              items:
                type: integer
              example: [1, 1, 2, 0, 1, 0, 1]
    responses:
      200:
        description: Resultado da avaliação (pontuação, categoria de risco, risco urgente)
      400:
        description: Dados inválidos
      404:
        description: Utilizador não encontrado
    """
    dados = request.get_json() or {}
    uuid_recebido = dados.get("uuid")
    respostas_phq9 = dados.get("respostas_phq9")
    respostas_gad7 = dados.get("respostas_gad7")

    if not uuid_recebido:
        return jsonify({"erro": "uuid é obrigatório"}), 400

    utilizador = Utilizador.query.filter_by(uuid=uuid_recebido).first()
    if not utilizador:
        return jsonify({"erro": "Utilizador não encontrado"}), 404

    try:
        resultado = processar_avaliacao_completa(respostas_phq9, respostas_gad7)
    except (ValueError, TypeError, IndexError) as e:
        return jsonify({"erro": str(e)}), 400

    avaliacao = Avaliacao(
        utilizador_id=utilizador.id,
        pontuacao_phq9=resultado["pontuacao_phq9"],
        pontuacao_gad7=resultado["pontuacao_gad7"],
        categoria_risco_phq9=resultado["categoria_risco_phq9"],
        categoria_risco_gad7=resultado["categoria_risco_gad7"],
        risco_urgente=resultado["risco_urgente"],
    )
    db.session.add(avaliacao)
    db.session.flush()  # para já termos avaliacao.id

    for i, valor in enumerate(respostas_phq9, start=1):
        db.session.add(RespostaItem(
            avaliacao_id=avaliacao.id, tipo_questionario="PHQ9",
            numero_pergunta=i, valor_resposta=valor,
        ))
    for i, valor in enumerate(respostas_gad7, start=1):
        db.session.add(RespostaItem(
            avaliacao_id=avaliacao.id, tipo_questionario="GAD7",
            numero_pergunta=i, valor_resposta=valor,
        ))

    db.session.commit()

    return jsonify(avaliacao.to_dict()), 200


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/api/saude", methods=["GET"])
def health_check():
    """
    Verifica se a API está a funcionar.
    ---
    tags:
      - Sistema
    responses:
      200:
        description: API operacional
    """
    return jsonify({"estado": "operacional"}), 200




# ---------------------------------------------------------------------------
# Sprint 6 — Área de administração
# ---------------------------------------------------------------------------

def requer_admin(f):
    """Decorador: bloqueia o acesso a quem não fez login como admin (RF17)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return jsonify({"erro": "Acesso não autorizado. Faz login primeiro."}), 401
        return f(*args, **kwargs)
    return wrapper


@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    """
    Login do administrador.
    ---
    tags:
      - Admin
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [username, password]
          properties:
            username:
              type: string
            password:
              type: string
    responses:
      200:
        description: Login bem-sucedido
      401:
        description: Credenciais inválidas
    """
    dados = request.get_json() or {}
    username = dados.get("username")
    password = dados.get("password")

    admin = Administrador.query.filter_by(username=username).first()
    if not admin or not check_password_hash(admin.password_hash, password):
        return jsonify({"erro": "Utilizador ou palavra-passe incorretos."}), 401

    session["admin_id"] = admin.id
    return jsonify({"mensagem": "Login efetuado com sucesso."}), 200


@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    """
    Termina a sessão do administrador.
    ---
    tags:
      - Admin
    responses:
      200:
        description: Sessão terminada
    """
    session.pop("admin_id", None)
    return jsonify({"mensagem": "Sessão terminada."}), 200


@app.route("/api/admin/estatisticas", methods=["GET"])
@requer_admin
def admin_estatisticas():
    """
    Devolve estatísticas agregadas e anonimizadas (RF18).
    Nunca devolve respostas individuais associadas a uma pessoa (RF19).
    ---
    tags:
      - Admin
    responses:
      200:
        description: Estatísticas agregadas
      401:
        description: Não autenticado
    """
    total_utilizadores = Utilizador.query.count()
    total_avaliacoes = Avaliacao.query.count()
    total_risco_urgente = Avaliacao.query.filter_by(risco_urgente=True).count()

    distribuicao_phq9 = {}
    for categoria in ["mínimo", "leve", "moderado", "moderadamente severo", "severo"]:
        distribuicao_phq9[categoria] = Avaliacao.query.filter_by(
            categoria_risco_phq9=categoria
        ).count()

    distribuicao_gad7 = {}
    for categoria in ["mínimo", "leve", "moderado", "severo"]:
        distribuicao_gad7[categoria] = Avaliacao.query.filter_by(
            categoria_risco_gad7=categoria
        ).count()

    avaliacoes = Avaliacao.query.all()
    if avaliacoes:
        media_phq9 = sum(a.pontuacao_phq9 for a in avaliacoes) / len(avaliacoes)
        media_gad7 = sum(a.pontuacao_gad7 for a in avaliacoes) / len(avaliacoes)
    else:
        media_phq9 = media_gad7 = 0

    distribuicao_idade = {}
    utilizadores = Utilizador.query.all()
    for u in utilizadores:
        faixa = u.faixa_etaria or "não especificado"
        distribuicao_idade[faixa] = distribuicao_idade.get(faixa, 0) + 1

    return jsonify({
        "total_utilizadores": total_utilizadores,
        "total_avaliacoes": total_avaliacoes,
        "total_risco_urgente": total_risco_urgente,
        "media_pontuacao_phq9": round(media_phq9, 1),
        "media_pontuacao_gad7": round(media_gad7, 1),
        "distribuicao_risco_phq9": distribuicao_phq9,
        "distribuicao_risco_gad7": distribuicao_gad7,
        "distribuicao_faixa_etaria": distribuicao_idade,
    }), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
from flask import Flask, request, jsonify
from flask_cors import CORS
from flasgger import Swagger

from config import Config
from models import db, Utilizador, Avaliacao, RespostaItem
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
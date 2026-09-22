"""
Lógica de scoring do PHQ-9 e GAD-7.
Implementa as Regras de Negócio RN01 a RN05 definidas no Capítulo II.
"""


def calcular_pontuacao_phq9(respostas):
    """
    respostas: lista de 9 inteiros (0-3), na ordem das perguntas 1 a 9.
    RN01: soma das 9 respostas, entre 0 e 27.
    """
    if len(respostas) != 9:
        raise ValueError("O PHQ-9 tem exatamente 9 perguntas.")
    for r in respostas:
        if r not in (0, 1, 2, 3):
            raise ValueError("Cada resposta do PHQ-9 deve ser 0, 1, 2 ou 3.")
    return sum(respostas)


def categorizar_risco_phq9(pontuacao):
    """RN03: bandas de risco do PHQ-9."""
    if pontuacao <= 4:
        return "mínimo"
    elif pontuacao <= 9:
        return "leve"
    elif pontuacao <= 14:
        return "moderado"
    elif pontuacao <= 19:
        return "moderadamente severo"
    else:
        return "severo"


def calcular_pontuacao_gad7(respostas):
    """
    respostas: lista de 7 inteiros (0-3), na ordem das perguntas 1 a 7.
    RN02: soma das 7 respostas, entre 0 e 21.
    """
    if len(respostas) != 7:
        raise ValueError("O GAD-7 tem exatamente 7 perguntas.")
    for r in respostas:
        if r not in (0, 1, 2, 3):
            raise ValueError("Cada resposta do GAD-7 deve ser 0, 1, 2 ou 3.")
    return sum(respostas)


def categorizar_risco_gad7(pontuacao):
    """RN04: bandas de risco do GAD-7."""
    if pontuacao <= 4:
        return "mínimo"
    elif pontuacao <= 9:
        return "leve"
    elif pontuacao <= 14:
        return "moderado"
    else:
        return "severo"


def verificar_risco_urgente(respostas_phq9):
    """
    RN05: o item 9 do PHQ-9 (índice 8, pensamentos de autoagressão) > 0
    aciona sempre o encaminhamento urgente, independentemente do total.
    """
    item_9 = respostas_phq9[8]
    return item_9 > 0


def processar_avaliacao_completa(respostas_phq9, respostas_gad7):
    """
    Função principal: recebe as duas listas de respostas e devolve
    tudo o que é preciso guardar na tabela `avaliacao`.
    """
    pontuacao_phq9 = calcular_pontuacao_phq9(respostas_phq9)
    pontuacao_gad7 = calcular_pontuacao_gad7(respostas_gad7)

    return {
        "pontuacao_phq9": pontuacao_phq9,
        "pontuacao_gad7": pontuacao_gad7,
        "categoria_risco_phq9": categorizar_risco_phq9(pontuacao_phq9),
        "categoria_risco_gad7": categorizar_risco_gad7(pontuacao_gad7),
        "risco_urgente": verificar_risco_urgente(respostas_phq9),
    }
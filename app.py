from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import csv
import os
import uuid

app = Flask(__name__)
app.secret_key = "troque_esta_chave_em_producao"


PASTA_ORCAMENTOS = "orcamentos"
os.makedirs(PASTA_ORCAMENTOS, exist_ok=True)

CONTRATO_VALOR = 2000.0
BASE = {
    "apartamento": 700.0,
    "casa": 900.0,
    "estudio": 1200.0
}

def calcular_orcamento(tipo_imovel: str, quartos: int, vagas: int, tem_criancas: bool, parcelas_contrato: int):

    tipo = tipo_imovel.lower()
    if tipo not in BASE:
        raise ValueError("Tipo de imóvel inválido.")


    aluguel = float(BASE[tipo])


    if tipo == "apartamento":
        if quartos == 2:
            aluguel += 200.0
        elif quartos > 2:

            aluguel += 200.0 + 200.0 * (quartos - 2)
    elif tipo == "casa":
        if quartos == 2:
            aluguel += 250.0
        elif quartos > 2:
            aluguel += 250.0 + 250.0 * (quartos - 2)

    if tipo in ("apartamento", "casa"):
        if vagas > 0:

            aluguel += 300.0 * vagas
    else:  # estúdio
        if vagas > 0:

            if vagas <= 2:
                aluguel += 250.0
            else:
                aluguel += 250.0 + 60.0 * (vagas - 2)


    desconto = 0.0
    if tipo == "apartamento" and not tem_criancas:
        desconto = round(0.05 * aluguel, 2)
        aluguel = round(aluguel - desconto, 2)
    else:
        aluguel = round(aluguel, 2)

    if parcelas_contrato < 1:
        parcelas_contrato = 1
    if parcelas_contrato > 5:
        parcelas_contrato = 5
    parcela_contrato_valor = round(CONTRATO_VALOR / parcelas_contrato, 2)

    months = []
    for m in range(1, 13):
        contrato_parcela = parcela_contrato_valor if m <= parcelas_contrato else 0.0
        total = round(aluguel + contrato_parcela, 2)
        months.append({
            "mes": m,
            "aluguel": f"{aluguel:.2f}",
            "parcela_contrato": f"{contrato_parcela:.2f}",
            "total": f"{total:.2f}"
        })

    summary = {
        "tipo_imovel": tipo,
        "quartos": quartos if tipo != "estudio" else None,
        "vagas": vagas,
        "tem_criancas": tem_criancas,
        "aluguel_base_calculado": f"{aluguel:.2f}",
        "desconto_aplicado": f"{desconto:.2f}",
        "contrato_valor_total": f"{CONTRATO_VALOR:.2f}",
        "parcelas_contrato": parcelas_contrato,
        "valor_parcela_contrato": f"{parcela_contrato_valor:.2f}",
        "total_anual": f"{sum(float(m['total']) for m in months):.2f}"
    }

    return summary, months

def salvar_csv(months: list, nome_cliente: str, tipo_imovel: str):
   
    safe_name = "".join(c for c in nome_cliente if c.isalnum() or c in "._- ").strip().replace(" ", "_")
    filename = f"orcamento_{safe_name}_{tipo_imovel}_{uuid.uuid4().hex[:8]}.csv"
    caminho = os.path.join(PASTA_ORCAMENTOS, filename)

    with open(caminho, mode="w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f, delimiter=';')
        escritor.writerow(["Mês", "Aluguel (R$)", "Parcela Contrato (R$)", "Total Mensal (R$)"])
        for row in months:
            escritor.writerow([row["mes"], row["aluguel"], row["parcela_contrato"], row["total"]])
        escritor.writerow([])
        escritor.writerow(["Total Anual", "", "", f"{sum(float(r['total']) for r in months):.2f}"])

    return caminho


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/gerar_orcamento", methods=["POST"])
def gerar_orcamento_route():
    try:
        nome_cliente = request.form.get("nome_cliente", "Cliente").strip()
        tipo_imovel = request.form.get("tipo_imovel", "apartamento")
        quartos = int(request.form.get("quartos", 1))
        vagas = int(request.form.get("vagas", 0))
        tem_criancas = request.form.get("tem_criancas", "sim") == "sim"
        parcelas_contrato = int(request.form.get("parcelas_contrato", 1))

        summary, months = calcular_orcamento(tipo_imovel, quartos, vagas, tem_criancas, parcelas_contrato)
        caminho_csv = salvar_csv(months, nome_cliente, tipo_imovel)
        nome_arquivo = os.path.basename(caminho_csv)

        return render_template("resultado.html",
                               nome_cliente=nome_cliente,
                               summary=summary,
                               months=months,
                               csv_filename=nome_arquivo)
    except Exception as e:
        flash(f"Erro ao gerar orçamento: {e}")
        return redirect(url_for("index"))


@app.route("/download/<csv_filename>", methods=["GET"])
def download_csv(csv_filename):
    caminho = os.path.join(PASTA_ORCAMENTOS, csv_filename)
    if not os.path.exists(caminho):
        flash("Arquivo não encontrado.")
        return redirect(url_for("index"))
    return send_file(caminho, as_attachment=True, download_name=csv_filename)

if __name__ == "__main__":
    app.run(debug=True)

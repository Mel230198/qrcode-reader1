from flask import Flask, request, render_template, jsonify
import os
import logging
import requests
from werkzeug.utils import secure_filename
from utils import allowed_file, ler_qrcode_de_pdf, ler_qrcode_de_imagem

app = Flask(__name__)

# Configurações
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp'}
API_DESTINO_URL = 'https://gestop.pt/acesso-gestop/webhook.php'

# Criação da pasta de upload
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configuração do logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def processar_arquivo(arquivo):
    """Processa o arquivo enviado e retorna o conteúdo do QR Code."""
    extensao = arquivo.filename.rsplit('.', 1)[1].lower()

    if extensao == 'pdf':
        return ler_qrcode_de_pdf(arquivo.read())
    else:
        nome_seguro = secure_filename(arquivo.filename)
        caminho = os.path.join(UPLOAD_FOLDER, nome_seguro)
        arquivo.save(caminho)
        try:
            return ler_qrcode_de_imagem(caminho)
        finally:
            os.remove(caminho)


def enviar_para_api(dados):
    """Salva localmente o conteúdo do QR e envia via POST JSON para a API externa."""
    try:
        valor = dados[0] if isinstance(dados, list) and dados else str(dados)

        # Salva localmente para debug
        with open('qrcode_recebido.txt', 'a', encoding='utf-8') as f:
            f.write(f"{valor}\n")

        # Envia para a URL remota via POST
        payload = {'dados': valor}
        response = requests.post(API_DESTINO_URL, json=payload)

        logger.info(f"[ENVIO] Dados: {valor}")
        logger.info(f"[RESPOSTA] Status: {response.status_code} - Texto: {response.text}")
    except Exception as e:
        logger.exception(f"Erro ao enviar dados para API externa: {str(e)}")


@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = []

    if request.method == 'POST':
        arquivo = request.files.get('arquivo')

        if not arquivo or arquivo.filename == '':
            resultado = ["Nenhum arquivo enviado."]
        elif not allowed_file(arquivo.filename, ALLOWED_EXTENSIONS):
            resultado = ["Formato não suportado. Use PDF, JPG, PNG, BMP, TIFF ou WEBP."]
        else:
            try:
                resultado = processar_arquivo(arquivo)
                logger.debug(f"Conteúdo extraído do QR Code: {resultado}")
                if resultado:
                    enviar_para_api(resultado)
            except Exception as e:
                logger.exception("Erro durante o processamento do QR Code")
                resultado = [f"Erro durante o processamento: {str(e)}"]

    return render_template('index.html', resultado=resultado)


@app.route('/receber-qrcode', methods=['POST'])
def receber_qrcode():
    """Endpoint de teste para receber QR Codes via POST JSON."""
    dados = request.get_json()
    logger.info(f"QR Code recebido via /receber-qrcode: {dados}")
    return jsonify({'status': 'ok', 'mensagem': 'QR Code recebido com sucesso'}), 200


if __name__ == '__main__':
    app.run(debug=True)

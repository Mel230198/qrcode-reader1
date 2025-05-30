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
API_DESTINO_URL = 'https://gestop.pt/acesso-gestop/webhook.php'  # Altere para o destino real

# Criação da pasta de upload
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def processar_arquivo(arquivo):
    """Processa o arquivo e retorna os dados lidos do QRCode."""
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
    """Envia os dados lidos do QR Code para uma API externa."""
    try:
        response = requests.post(API_DESTINO_URL, json={'dados': dados})
        logger.info(f"Enviado para API externa. Status: {response.status_code} - Resposta: {response.text}")
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
                if resultado:
                    enviar_para_api(resultado)
            except Exception as e:
                logger.exception("Erro durante o processamento")
                resultado = [f"Erro durante o processamento: {str(e)}"]

    return render_template('index.html', resultado=resultado)


@app.route('/receber-qrcode', methods=['POST'])
def receber_qrcode():
    dados = request.get_json()
    logger.info(f"QR Code recebido: {dados}")
    return jsonify({'status': 'ok', 'mensagem': 'QR Code recebido com sucesso'}), 200


if __name__ == '__main__':
    app.run(debug=True)

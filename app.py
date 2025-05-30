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

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def processar_arquivo(arquivo):
    """Processa o arquivo enviado e retorna o conteúdo do QR Code."""
    extensao = arquivo.filename.rsplit('.', 1)[1].lower()

    if extensao == 'pdf':
        conteudo = ler_qrcode_de_pdf(arquivo.read())
        logger.debug(f"QR Code extraído do PDF: {conteudo}")
        return conteudo
    else:
        nome_seguro = secure_filename(arquivo.filename)
        caminho = os.path.join(UPLOAD_FOLDER, nome_seguro)
        arquivo.save(caminho)
        try:
            conteudo = ler_qrcode_de_imagem(caminho)
            logger.debug(f"QR Code extraído da imagem: {conteudo}")
            return conteudo
        finally:
            os.remove(caminho)


def enviar_para_api(dados):
    """Envia via POST JSON para a API externa o conteúdo do QR Code."""
    try:
        if isinstance(dados, list) and dados:
            valor = dados[0]
        else:
            valor = str(dados)

        # Salva localmente para debug
        with open('qrcode_recebido.txt', 'a', encoding='utf-8') as f:
            f.write(f"{valor}\n")

        payload = {'dados': valor}
        logger.debug(f"Enviando para {API_DESTINO_URL} o payload: {payload}")

        response = requests.post(API_DESTINO_URL, json=payload, timeout=10)
        response.raise_for_status()

        logger.info(f"[RESPOSTA] Status: {response.status_code} - Texto: {response.text}")
        return True
    except requests.exceptions.Timeout:
        logger.error("Timeout ao enviar dados para API externa")
    except requests.exceptions.ConnectionError:
        logger.error("Erro de conexão ao enviar dados para API externa")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Erro HTTP: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.exception(f"Erro inesperado: {e}")
    return False


@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = []

    if request.method == 'POST':
        arquivo = request.files.get('arquivo')

        if not arquivo or arquivo.filename == '':
            resultado = ["Nenhum arquivo enviado."]
            logger.warning("Nenhum arquivo foi enviado na requisição POST.")
        elif not allowed_file(arquivo.filename, ALLOWED_EXTENSIONS):
            resultado = ["Formato não suportado. Use PDF, JPG, PNG, BMP, TIFF ou WEBP."]
            logger.warning(f"Arquivo com formato não suportado: {arquivo.filename}")
        else:
            try:
                resultado = processar_arquivo(arquivo)
                logger.debug(f"Conteúdo extraído do QR Code: {resultado}")
                if resultado:
                    sucesso = enviar_para_api(resultado)
                    if not sucesso:
                        resultado = ["Falha ao enviar dados para a API externa."]
                else:
                    resultado = ["QR Code não encontrado ou inválido."]
            except Exception as e:
                logger.exception("Erro durante o processamento do QR Code")
                resultado = [f"Erro durante o processamento: {str(e)}"]

    return render_template('index.html', resultado=resultado)


@app.route('/receber-qrcode', methods=['POST'])
def receber_qrcode():
    """Endpoint para receber QR Codes via POST JSON."""
    dados = request.get_json()
    logger.info(f"QR Code recebido via /receber-qrcode: {dados}")
    return jsonify({'status': 'ok', 'mensagem': 'QR Code recebido com sucesso'}), 200


if __name__ == '__main__':
    app.run(debug=True)


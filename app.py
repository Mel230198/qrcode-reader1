from flask import Flask, request, render_template, jsonify
import os
import logging
import requests
from werkzeug.utils import secure_filename
from utils import allowed_file, ler_qrcode_de_pdf, ler_qrcode_de_imagem

# === Configuração Inicial ===
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp'}
API_DESTINO_URL = 'https://gestop.pt/acesso-gestop/webhook.php'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === Logger ===
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# === Funções de Processamento ===

def processar_arquivo(arquivo):
    """Lê o QR Code de um arquivo PDF ou imagem."""
    extensao = arquivo.filename.rsplit('.', 1)[-1].lower()
    logger.debug(f"Processando arquivo com extensão: {extensao}")

    if extensao == 'pdf':
        conteudo = ler_qrcode_de_pdf(arquivo.read())
    else:
        nome_seguro = secure_filename(arquivo.filename)
        caminho = os.path.join(UPLOAD_FOLDER, nome_seguro)
        arquivo.save(caminho)
        try:
            conteudo = ler_qrcode_de_imagem(caminho)
        finally:
            os.remove(caminho)

    logger.debug(f"QR Code extraído: {conteudo}")
    return conteudo


def enviar_para_api(dados):
    """Envia os dados do QR Code como JSON para a API externa."""
    try:
        valor = dados[0] if isinstance(dados, list) and dados else str(dados)

        # Salva localmente para debug
        with open('qrcode_recebido.txt', 'a', encoding='utf-8') as f:
            f.write(f"{valor}\n")

        payload = {'dados': valor}
        logger.debug(f"Enviando payload para {API_DESTINO_URL}: {payload}")

        response = requests.post(API_DESTINO_URL, json=payload, timeout=10)
        response.raise_for_status()

        logger.info(f"[RESPOSTA] Status: {response.status_code} - Texto: {response.text}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição para API externa: {e}")
    except Exception as e:
        logger.exception("Erro inesperado ao enviar para a API externa")

    return False


# === Rotas ===

@app.route('/', methods=['GET', 'POST'])
def index():
    """Página principal para envio de arquivos contendo QR Code."""
    resultado = []

    if request.method == 'POST':
        arquivo = request.files.get('arquivo')

        if not arquivo or arquivo.filename == '':
            resultado = ["Nenhum arquivo enviado."]
            logger.warning("Nenhum arquivo foi enviado.")
        elif not allowed_file(arquivo.filename, ALLOWED_EXTENSIONS):
            resultado = ["Formato não suportado. Use PDF, JPG, PNG, BMP, TIFF ou WEBP."]
            logger.warning(f"Formato inválido: {arquivo.filename}")
        else:
            try:
                resultado = processar_arquivo(arquivo)

                if not resultado:
                    resultado = ["QR Code não encontrado ou inválido."]
                    logger.warning("QR Code vazio ou não detectado.")
                elif not enviar_para_api(resultado):
                    resultado = ["Falha ao enviar dados para a API externa."]
            except Exception as e:
                logger.exception("Erro ao processar o QR Code.")
                resultado = [f"Erro durante o processamento: {str(e)}"]

    return render_template('index.html', resultado=resultado)


@app.route('/receber-qrcode', methods=['POST'])
def receber_qrcode():
    """Endpoint para receber QR Codes via JSON POST."""
    dados = request.get_json()
    logger.info(f"QR Code recebido via /receber-qrcode: {dados}")
    return jsonify({'status': 'ok', 'mensagem': 'QR Code recebido com sucesso'}), 200


@app.route('/testar-envio', methods=['GET'])
def testar_envio():
    """Envia um dado fixo para testar integração com a API externa."""
    valor_teste = "teste-envio-manual"
    logger.info("Iniciando teste de envio com dado fixo.")
    sucesso = enviar_para_api(valor_teste)

    if sucesso:
        return "✅ Envio de teste realizado com sucesso."
    else:
        return "❌ Falha ao enviar dados de teste para a API externa.", 500


# === Execução ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

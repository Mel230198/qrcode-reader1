from flask import Flask, request, render_template, jsonify
import os
import logging
import requests
from werkzeug.utils import secure_filename
from utils import allowed_file, ler_qrcode_de_pdf, ler_qrcode_de_imagem

app = Flask(__name__)

# === Configurações ===
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp'}
API_DESTINO_URL = 'https://gestop.pt/acesso-gestop/webhook.php'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === Logger ===
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# === Funções Auxiliares ===

def processar_arquivo(arquivo):
    """Extrai o conteúdo do QR Code de um PDF ou imagem."""
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

    logger.debug(f"Conteúdo do QR Code: {conteudo}")
    return conteudo


def enviar_para_api(dados):
    """Envia os dados extraídos para a API externa."""
    try:
        valor = dados[0] if isinstance(dados, list) and dados else str(dados)

        # Salva localmente para debug
        with open('qrcode_recebido.txt', 'a', encoding='utf-8') as f:
            f.write(f"{valor}\n")

        payload = {'dados': valor}
        logger.debug(f"Enviando para {API_DESTINO_URL}: {payload}")

        response = requests.post(API_DESTINO_URL, json=payload, timeout=10)
        response.raise_for_status()

        logger.info(f"Enviado com sucesso: {response.status_code} - {response.text}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao enviar para API externa: {e}")
    except Exception as e:
        logger.exception("Erro inesperado ao enviar para a API externa")

    return False


# === Interface Web ===

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = []

    if request.method == 'POST':
        arquivo = request.files.get('arquivo')

        if not arquivo or arquivo.filename == '':
            resultado = ["Nenhum arquivo enviado."]
            logger.warning("Nenhum arquivo enviado.")
        elif not allowed_file(arquivo.filename, ALLOWED_EXTENSIONS):
            resultado = ["Formato não suportado. Use PDF, JPG, PNG, BMP, TIFF ou WEBP."]
            logger.warning(f"Formato inválido: {arquivo.filename}")
        else:
            try:
                resultado = processar_arquivo(arquivo)

                if not resultado:
                    resultado = ["QR Code não encontrado ou inválido."]
                elif not enviar_para_api(resultado):
                    resultado = ["Falha ao enviar dados para a API externa."]
            except Exception as e:
                logger.exception("Erro ao processar QR Code.")
                resultado = [f"Erro interno: {str(e)}"]

    return render_template('index.html', resultado=resultado)


# === API REST: QR Code via Upload ===

@app.route('/api/ler-qrcode', methods=['POST'])
def api_ler_qrcode():
    """API para receber imagem/PDF e retornar o conteúdo do QR Code."""
    arquivo = request.files.get('arquivo')

    if not arquivo or arquivo.filename == '':
        logger.warning("API: Nenhum arquivo enviado.")
        return jsonify({'erro': 'Nenhum arquivo enviado.'}), 400

    if not allowed_file(arquivo.filename, ALLOWED_EXTENSIONS):
        logger.warning(f"API: Formato não suportado: {arquivo.filename}")
        return jsonify({'erro': 'Formato não suportado.'}), 400

    try:
        conteudo = processar_arquivo(arquivo)

        if not conteudo:
            logger.info("API: QR Code não encontrado.")
            return jsonify({'erro': 'QR Code não encontrado.'}), 404

        return jsonify({'conteudo': conteudo}), 200

    except Exception as e:
        logger.exception("API: Erro ao processar QR Code.")
        return jsonify({'erro': f"Erro interno: {str(e)}"}), 500


# === API: Teste manual ===

@app.route('/testar-envio', methods=['GET'])
def testar_envio():
    """Endpoint para testar envio fixo à API externa."""
    valor_teste = "teste-envio-manual"
    logger.info("Iniciando teste de envio com valor fixo.")

    if enviar_para_api(valor_teste):
        return "✅ Envio de teste realizado com sucesso."
    return "❌ Falha ao enviar dados de teste.", 500


# === API: Receber dados JSON manualmente ===

@app.route('/receber-qrcode', methods=['POST'])
def receber_qrcode():
    """Recebe dados JSON manualmente para teste local."""
    dados = request.get_json()
    logger.info(f"Recebido via /receber-qrcode: {dados}")
    return jsonify({'status': 'ok', 'mensagem': 'Recebido com sucesso'}), 200


# === Execução ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

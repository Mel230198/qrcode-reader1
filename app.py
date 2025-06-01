from flask import Flask, request, render_template, jsonify
import os
import logging
import requests
import json
from werkzeug.utils import secure_filename
from utils import allowed_file, ler_qrcode_de_pdf, ler_qrcode_de_imagem

# === Configuração Inicial ===
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp'}
API_DESTINO_URL = 'https://gestop.pt/acesso-gestop/webhook.php'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === Logger ===
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# === Funções de Processamento ===

def processar_arquivo_por_caminho(caminho_arquivo):
    try:
        if not os.path.exists(caminho_arquivo):
            logger.error(f"Arquivo não encontrado: {caminho_arquivo}")
            return None

        extensao = caminho_arquivo.rsplit('.', 1)[-1].lower()
        if not allowed_file(caminho_arquivo, ALLOWED_EXTENSIONS):
            logger.error(f"Extensão não permitida: {extensao}")
            return None

        logger.debug(f"Processando arquivo: {caminho_arquivo} (extensão: {extensao})")

        if extensao == 'pdf':
            with open(caminho_arquivo, 'rb') as f:
                conteudo = ler_qrcode_de_pdf(f.read())
        else:
            conteudo = ler_qrcode_de_imagem(caminho_arquivo)

        logger.debug(f"QR Code extraído: {conteudo}")
        return conteudo

    except Exception as e:
        logger.exception(f"Erro ao processar arquivo: {caminho_arquivo}")
        return None


def processar_arquivo_upload(arquivo):
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
    try:
        valor = dados[0] if isinstance(dados, list) else str(dados)

        if not valor or valor.strip() == "":
            logger.error("Dados vazios ou inválidos para envio")
            return False

        try:
            with open('qrcode_recebido.txt', 'a', encoding='utf-8') as f:
                f.write(f"{valor}\n")
        except Exception as e:
            logger.warning(f"Erro ao salvar arquivo de debug: {e}")

        payload = {'dados': valor}
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'QRCode-Reader/1.0'
        }

        response = requests.post(
            API_DESTINO_URL,
            json=payload,
            headers=headers,
            timeout=30,
            verify=True
        )

        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Conteúdo da Resposta: {response.text}")

        return 200 <= response.status_code < 300

    except Exception as e:
        logger.exception("Erro inesperado ao enviar para a API externa")
        return False


def testar_conectividade():
    try:
        response = requests.get(API_DESTINO_URL, timeout=10)
        logger.info(f"Teste de conectividade - Status: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Erro na conectividade: {e}")
        return False


# === Rotas ===

@app.route('/')
def index():
    return """
    <h1>🔍 QR Code Reader API</h1>
    <ul>
        <li><code>GET /processar?arquivo=nome-do-arquivo.pdf</code></li>
        <li><code>GET /testar-envio</code></li>
        <li><code>GET /debug-info</code></li>
        <li><code>POST /upload</code> (múltiplos arquivos suportados)</li>
    </ul>
    """


@app.route('/processar', methods=['GET'])
def processar_qrcode():
    caminho_relativo = request.args.get('arquivo')

    if not caminho_relativo or '..' in caminho_relativo or caminho_relativo.startswith('/'):
        return jsonify({
            'status': 'erro',
            'mensagem': 'Caminho inválido. Use apenas nomes de arquivos dentro da pasta uploads/.'
        }), 400

    caminho_arquivo = os.path.abspath(os.path.join(UPLOAD_FOLDER, caminho_relativo))

    logger.info(f"📁 Processando arquivo via caminho: {caminho_arquivo}")

    try:
        resultado = processar_arquivo_por_caminho(caminho_arquivo)

        if not resultado:
            return jsonify({
                'status': 'erro',
                'mensagem': 'QR Code não encontrado ou erro no arquivo',
                'arquivo': caminho_relativo
            }), 400

        enviado = enviar_para_api(resultado)

        return jsonify({
            'status': 'sucesso' if enviado else 'parcial',
            'mensagem': 'Processado e enviado com sucesso' if enviado else 'Processado, mas falha no envio',
            'arquivo': caminho_relativo,
            'qrcode_dados': resultado,
            'enviado_para_api': enviado
        }), 200

    except Exception as e:
        logger.exception(f"Erro ao processar: {caminho_relativo}")
        return jsonify({
            'status': 'erro',
            'mensagem': str(e),
            'arquivo': caminho_relativo
        }), 500


@app.route('/upload', methods=['GET', 'POST'])
def upload_arquivo():
    if request.method == 'GET':
        return render_template('upload.html') if os.path.exists('templates/upload.html') else """
        <form method="POST" enctype="multipart/form-data">
            <h2>Upload de Arquivos com QR Code</h2>
            <input type="file" name="arquivos" accept=".pdf,.jpg,.jpeg,.png,.bmp,.tiff,.webp" multiple required>
            <button type="submit">Processar</button>
        </form>
        """

    arquivos = request.files.getlist('arquivos')

    if not arquivos:
        return jsonify({'status': 'erro', 'mensagem': 'Nenhum arquivo enviado'}), 400

    resultados = []
    for arquivo in arquivos:
        if not arquivo or arquivo.filename == '':
            continue
        if not allowed_file(arquivo.filename, ALLOWED_EXTENSIONS):
            resultados.append({
                'arquivo': arquivo.filename,
                'status': 'erro',
                'mensagem': 'Formato não suportado'
            })
            continue

        try:
            conteudo = processar_arquivo_upload(arquivo)
            if not conteudo:
                resultados.append({
                    'arquivo': arquivo.filename,
                    'status': 'erro',
                    'mensagem': 'QR Code não encontrado'
                })
            elif enviar_para_api(conteudo):
                resultados.append({
                    'arquivo': arquivo.filename,
                    'status': 'sucesso',
                    'qrcode_dados': conteudo
                })
            else:
                resultados.append({
                    'arquivo': arquivo.filename,
                    'status': 'parcial',
                    'qrcode_dados': conteudo,
                    'mensagem': 'Falha ao enviar para a API'
                })
        except Exception as e:
            logger.exception("Erro no upload múltiplo")
            resultados.append({
                'arquivo': arquivo.filename,
                'status': 'erro',
                'mensagem': str(e)
            })

    return jsonify({'resultados': resultados}), 200


@app.route('/testar-envio', methods=['GET'])
def testar_envio():
    import time
    valor_teste = f"teste-envio-manual-{int(time.time())}"
    logger.info(f"🧪 Testando envio com: {valor_teste}")

    if not testar_conectividade():
        return jsonify({'status': 'erro', 'mensagem': 'API externa inacessível'}), 500

    sucesso = enviar_para_api(valor_teste)

    return jsonify({
        'status': 'sucesso' if sucesso else 'erro',
        'mensagem': 'Envio de teste realizado com sucesso' if sucesso else 'Falha no envio de teste',
        'valor_enviado': valor_teste
    }), 200 if sucesso else 500


@app.route('/debug-info', methods=['GET'])
def debug_info():
    return jsonify({
        'api_url': API_DESTINO_URL,
        'upload_folder': UPLOAD_FOLDER,
        'allowed_extensions': list(ALLOWED_EXTENSIONS),
        'python_version': os.sys.version,
        'flask_version': Flask.__version__,
        'endpoints': {
            'processar': '/processar?arquivo=nome-do-arquivo.pdf',
            'testar_envio': '/testar-envio',
            'upload': '/upload',
            'debug': '/debug-info'
        }
    })


# === Execução ===
if __name__ == '__main__':
    logger.info("🚀 Iniciando aplicação Flask...")
    logger.info(f"🌐 URL da API destino: {API_DESTINO_URL}")
    app.run(host='0.0.0.0', port=5000, debug=True)

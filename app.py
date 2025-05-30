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
    """Lê o QR Code de um arquivo usando o caminho fornecido."""
    try:
        # Verifica se o arquivo existe
        if not os.path.exists(caminho_arquivo):
            logger.error(f"Arquivo não encontrado: {caminho_arquivo}")
            return None
        
        # Verifica a extensão
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
    """Lê o QR Code de um arquivo enviado via upload (mantido para compatibilidade)."""
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
        # Processa os dados de entrada
        if isinstance(dados, list):
            valor = dados[0] if dados else ""
        else:
            valor = str(dados) if dados else ""
        
        # Verifica se há dados válidos
        if not valor or valor.strip() == "":
            logger.error("Dados vazios ou inválidos para envio")
            return False

        # Salva localmente para debug
        try:
            with open('qrcode_recebido.txt', 'a', encoding='utf-8') as f:
                f.write(f"{valor}\n")
        except Exception as e:
            logger.warning(f"Erro ao salvar arquivo de debug: {e}")

        # Prepara o payload
        payload = {'dados': valor}
        
        # Headers para garantir que seja interpretado como JSON
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'QRCode-Reader/1.0'
        }
        
        logger.info(f"=== ENVIANDO DADOS ===")
        logger.info(f"URL: {API_DESTINO_URL}")
        logger.info(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        logger.info(f"Headers: {headers}")

        # Faz a requisição
        response = requests.post(
            API_DESTINO_URL, 
            json=payload,
            headers=headers,
            timeout=30,
            verify=True
        )
        
        logger.info(f"=== RESPOSTA DA API ===")
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Headers de Resposta: {dict(response.headers)}")
        logger.info(f"Conteúdo da Resposta: {response.text}")
        
        # Verifica se a resposta foi bem-sucedida
        if response.status_code >= 200 and response.status_code < 300:
            logger.info("✅ Dados enviados com sucesso!")
            return True
        else:
            logger.error(f"❌ API retornou status de erro: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        logger.error("❌ Timeout na requisição - API demorou para responder")
    except requests.exceptions.ConnectionError:
        logger.error("❌ Erro de conexão - Verifique se a URL está acessível")
    except requests.exceptions.SSLError:
        logger.error("❌ Erro SSL - Problema com certificado")
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ Erro HTTP: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erro na requisição: {e}")
    except Exception as e:
        logger.exception("❌ Erro inesperado ao enviar para a API externa")

    return False


def testar_conectividade():
    """Testa se a URL da API está acessível."""
    try:
        logger.info("Testando conectividade com a API...")
        response = requests.get(API_DESTINO_URL, timeout=10)
        logger.info(f"Teste de conectividade - Status: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Erro na conectividade: {e}")
        return False


# === Rotas ===

@app.route('/')
def index():
    """Página principal com instruções de uso."""
    return """
    <h1>🔍 QR Code Reader API</h1>
    <h2>Como usar:</h2>
    <ul>
        <li><strong>Processar arquivo via caminho:</strong><br>
            <code>GET /processar?arquivo=/caminho/para/arquivo.pdf</code></li>
        <li><strong>Teste de envio:</strong><br>
            <code>GET /testar-envio</code></li>
        <li><strong>Informações de debug:</strong><br>
            <code>GET /debug-info</code></li>
        <li><strong>Upload manual (opcional):</strong><br>
            <code>POST /upload</code></li>
    </ul>
    <h2>Formatos suportados:</h2>
    <p>PDF, JPG, JPEG, PNG, BMP, TIFF, WEBP</p>
    """


@app.route('/processar', methods=['GET'])
def processar_qrcode():
    """Processa um arquivo QR Code usando o caminho fornecido na URL."""
    caminho_arquivo = request.args.get('arquivo')
    
    if not caminho_arquivo:
        return jsonify({
            'status': 'erro',
            'mensagem': 'Parâmetro "arquivo" é obrigatório. Exemplo: /processar?arquivo=/caminho/para/arquivo.pdf'
        }), 400
    
    logger.info(f"📁 Processando arquivo via caminho: {caminho_arquivo}")
    
    try:
        # Processa o arquivo
        resultado = processar_arquivo_por_caminho(caminho_arquivo)
        
        if not resultado:
            return jsonify({
                'status': 'erro',
                'mensagem': 'QR Code não encontrado, arquivo não existe ou formato inválido',
                'arquivo': caminho_arquivo
            }), 400
        
        logger.info(f"🎯 QR Code encontrado: {resultado}")
        
        # Envia para a API
        if enviar_para_api(resultado):
            return jsonify({
                'status': 'sucesso',
                'mensagem': 'QR Code processado e enviado com sucesso',
                'arquivo': caminho_arquivo,
                'qrcode_dados': resultado,
                'enviado_para_api': True
            }), 200
        else:
            return jsonify({
                'status': 'parcial',
                'mensagem': 'QR Code processado mas falha ao enviar para API',
                'arquivo': caminho_arquivo,
                'qrcode_dados': resultado,
                'enviado_para_api': False
            }), 200
            
    except Exception as e:
        logger.exception(f"Erro ao processar: {caminho_arquivo}")
        return jsonify({
            'status': 'erro',
            'mensagem': f'Erro durante o processamento: {str(e)}',
            'arquivo': caminho_arquivo
        }), 500


@app.route('/upload', methods=['GET', 'POST'])
def upload_arquivo():
    """Rota opcional para upload manual de arquivos."""
    if request.method == 'GET':
        return render_template('upload.html') if os.path.exists('templates/upload.html') else """
        <form method="POST" enctype="multipart/form-data">
            <h2>Upload de Arquivo com QR Code</h2>
            <input type="file" name="arquivo" accept=".pdf,.jpg,.jpeg,.png,.bmp,.tiff,.webp" required>
            <button type="submit">Processar QR Code</button>
        </form>
        """
    
    # POST - processa o upload
    arquivo = request.files.get('arquivo')
    
    if not arquivo or arquivo.filename == '':
        return jsonify({'status': 'erro', 'mensagem': 'Nenhum arquivo enviado'}), 400
    
    if not allowed_file(arquivo.filename, ALLOWED_EXTENSIONS):
        return jsonify({'status': 'erro', 'mensagem': 'Formato não suportado'}), 400
    
    try:
        resultado = processar_arquivo_upload(arquivo)
        
        if not resultado:
            return jsonify({'status': 'erro', 'mensagem': 'QR Code não encontrado'}), 400
        
        if enviar_para_api(resultado):
            return jsonify({
                'status': 'sucesso',
                'mensagem': 'Processado e enviado com sucesso',
                'qrcode_dados': resultado
            }), 200
        else:
            return jsonify({
                'status': 'parcial',
                'mensagem': 'Processado mas falha no envio',
                'qrcode_dados': resultado
            }), 200
            
    except Exception as e:
        logger.exception("Erro no upload")
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500


@app.route('/testar-envio', methods=['GET'])
def testar_envio():
    """Envia um dado fixo para testar integração com a API externa."""
    try:
        # Gera um valor único para teste
        import time
        valor_teste = f"teste-envio-manual-{int(time.time())}"
        logger.info(f"🧪 Iniciando teste de envio com dado: {valor_teste}")
        
        # Primeiro testa conectividade
        if not testar_conectividade():
            return jsonify({
                'status': 'erro',
                'mensagem': 'API não está acessível para teste de conectividade'
            }), 500
        
        sucesso = enviar_para_api(valor_teste)

        if sucesso:
            return jsonify({
                'status': 'sucesso',
                'mensagem': 'Envio de teste realizado com sucesso',
                'valor_enviado': valor_teste
            }), 200
        else:
            return jsonify({
                'status': 'erro',
                'mensagem': 'Falha ao enviar dados de teste para a API externa'
            }), 500
            
    except Exception as e:
        logger.exception("Erro no teste de envio")
        return jsonify({
            'status': 'erro',
            'mensagem': f'Erro durante teste: {str(e)}'
        }), 500


@app.route('/debug-info', methods=['GET'])
def debug_info():
    """Endpoint para informações de debug."""
    info = {
        'api_url': API_DESTINO_URL,
        'upload_folder': UPLOAD_FOLDER,
        'allowed_extensions': list(ALLOWED_EXTENSIONS),
        'python_version': os.sys.version,
        'flask_version': Flask.__version__,
        'endpoints': {
            'processar': '/processar?arquivo=/caminho/para/arquivo.pdf',
            'testar_envio': '/testar-envio',
            'upload': '/upload',
            'debug': '/debug-info'
        }
    }
    return jsonify(info)


# === Execução ===
if __name__ == '__main__':
    logger.info("🚀 Iniciando aplicação Flask...")
    logger.info(f"🌐 URL da API destino: {API_DESTINO_URL}")
    logger.info("📋 Endpoints disponíveis:")
    logger.info("   GET /processar?arquivo=/caminho/arquivo.pdf")
    logger.info("   GET /testar-envio")
    logger.info("   GET /debug-info")
    logger.info("   GET|POST /upload")
    app.run(host='0.0.0.0', port=5000, debug=True)

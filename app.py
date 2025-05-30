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
            timeout=30,  # Aumenta timeout
            verify=True   # Verifica SSL
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
                else:
                    logger.info(f"QR Code processado: {resultado}")
                    if enviar_para_api(resultado):
                        resultado.append("✅ Dados enviados com sucesso para a API!")
                    else:
                        resultado.append("❌ Falha ao enviar dados para a API externa.")
                        
            except Exception as e:
                logger.exception("Erro ao processar o QR Code.")
                resultado = [f"Erro durante o processamento: {str(e)}"]

    return render_template('index.html', resultado=resultado)


@app.route('/receber-qrcode', methods=['POST'])
def receber_qrcode():
    """Endpoint para receber QR Codes via JSON POST."""
    try:
        dados = request.get_json()
        logger.info(f"QR Code recebido via /receber-qrcode: {dados}")
        
        # Log completo da requisição
        logger.debug(f"Headers da requisição: {dict(request.headers)}")
        logger.debug(f"Content-Type: {request.content_type}")
        
        return jsonify({
            'status': 'ok', 
            'mensagem': 'QR Code recebido com sucesso',
            'dados_recebidos': dados
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao processar dados recebidos: {e}")
        return jsonify({
            'status': 'erro',
            'mensagem': f'Erro ao processar: {str(e)}'
        }), 400


@app.route('/testar-envio', methods=['GET'])
def testar_envio():
    """Envia um dado fixo para testar integração com a API externa."""
    valor_teste = "teste-envio-manual-" + str(requests.get('http://worldtimeapi.org/api/timezone/Etc/UTC').json()['unixtime'])
    logger.info(f"Iniciando teste de envio com dado: {valor_teste}")
    
    # Primeiro testa conectividade
    if not testar_conectividade():
        return "❌ API não está acessível para teste de conectividade.", 500
    
    sucesso = enviar_para_api(valor_teste)

    if sucesso:
        return f"✅ Envio de teste realizado com sucesso. Valor enviado: {valor_teste}"
    else:
        return "❌ Falha ao enviar dados de teste para a API externa.", 500


@app.route('/debug-info', methods=['GET'])
def debug_info():
    """Endpoint para informações de debug."""
    info = {
        'api_url': API_DESTINO_URL,
        'upload_folder': UPLOAD_FOLDER,
        'allowed_extensions': list(ALLOWED_EXTENSIONS),
        'python_version': os.sys.version,
        'flask_version': Flask.__version__
    }
    return jsonify(info)


# === Execução ===
if __name__ == '__main__':
    logger.info("Iniciando aplicação Flask...")
    logger.info(f"URL da API destino: {API_DESTINO_URL}")
    app.run(host='0.0.0.0', port=5000, debug=True)

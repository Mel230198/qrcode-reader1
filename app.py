from flask import Flask, request, render_template
import os
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from pdf2image import convert_from_bytes
from werkzeug.utils import secure_filename
from PIL import Image
import logging

# Configurar logging para debug
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Pasta para armazenar arquivos temporários
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocessar_imagem(imagem_gray):
    """Aplica várias técnicas de pré-processamento para melhorar a detecção de QR codes"""
    resultados = []
    
    # 1. Imagem original em escala de cinza
    qrcodes = decode(imagem_gray)
    if qrcodes:
        resultados.extend([q.data.decode('utf-8') for q in qrcodes])
    
    # 2. Aplicar threshold binário
    _, thresh = cv2.threshold(imagem_gray, 127, 255, cv2.THRESH_BINARY)
    qrcodes = decode(thresh)
    if qrcodes:
        resultados.extend([q.data.decode('utf-8') for q in qrcodes])
    
    # 3. Aplicar threshold adaptativo
    adaptive_thresh = cv2.adaptiveThreshold(
        imagem_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    qrcodes = decode(adaptive_thresh)
    if qrcodes:
        resultados.extend([q.data.decode('utf-8') for q in qrcodes])
    
    # 4. Aplicar desfoque gaussiano para reduzir ruído
    blurred = cv2.GaussianBlur(imagem_gray, (3, 3), 0)
    qrcodes = decode(blurred)
    if qrcodes:
        resultados.extend([q.data.decode('utf-8') for q in qrcodes])
    
    # 5. Equalização de histograma
    equalized = cv2.equalizeHist(imagem_gray)
    qrcodes = decode(equalized)
    if qrcodes:
        resultados.extend([q.data.decode('utf-8') for q in qrcodes])
    
    # Remove duplicatas mantendo a ordem
    return list(dict.fromkeys(resultados))

def ler_qrcode_cv2(imagem_cv):
    """Lê QR codes de uma imagem OpenCV com múltiplas tentativas de pré-processamento"""
    try:
        logger.debug(f"Processando imagem com dimensões: {imagem_cv.shape}")
        
        # Verificar se a imagem foi carregada corretamente
        if imagem_cv is None or imagem_cv.size == 0:
            return ["Erro: Imagem vazia ou não carregada"]
        
        # Converter para escala de cinza
        if len(imagem_cv.shape) == 3:
            imagem_gray = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2GRAY)
        else:
            imagem_gray = imagem_cv
        
        # Aplicar múltiplas técnicas de pré-processamento
        resultados = preprocessar_imagem(imagem_gray)
        
        if resultados:
            logger.debug(f"QR codes encontrados: {resultados}")
            return resultados
        else:
            return ["Nenhum QR Code detectado após múltiplas tentativas de processamento."]
            
    except Exception as e:
        logger.error(f"Erro ao processar imagem: {str(e)}")
        return [f"Erro ao processar imagem: {str(e)}"]

def ler_qrcode_de_imagem(caminho_imagem):
    """Lê QR codes de arquivo de imagem com fallback para PIL"""
    try:
        logger.debug(f"Tentando abrir imagem: {caminho_imagem}")
        
        # Primeiro, tentar com OpenCV
        imagem_cv = cv2.imread(caminho_imagem)
        
        if imagem_cv is None:
            logger.debug("OpenCV falhou, tentando com PIL...")
            # Fallback: usar PIL para abrir a imagem
            try:
                pil_image = Image.open(caminho_imagem)
                # Converter PIL para array numpy
                imagem_array = np.array(pil_image)
                
                # Converter RGB para BGR se necessário
                if len(imagem_array.shape) == 3 and imagem_array.shape[2] == 3:
                    imagem_cv = cv2.cvtColor(imagem_array, cv2.COLOR_RGB2BGR)
                elif len(imagem_array.shape) == 3 and imagem_array.shape[2] == 4:
                    # RGBA para BGR
                    imagem_cv = cv2.cvtColor(imagem_array, cv2.COLOR_RGBA2BGR)
                else:
                    imagem_cv = imagem_array
                    
                logger.debug(f"Imagem carregada com PIL: {imagem_cv.shape}")
                
            except Exception as pil_error:
                logger.error(f"Erro ao abrir com PIL: {str(pil_error)}")
                return [f"Erro ao abrir a imagem: {caminho_imagem} - {str(pil_error)}"]
        
        if imagem_cv is None:
            return [f"Erro: Não foi possível carregar a imagem {caminho_imagem}"]
            
        return ler_qrcode_cv2(imagem_cv)
        
    except Exception as e:
        logger.error(f"Erro geral ao processar imagem: {str(e)}")
        return [f"Erro ao processar imagem: {str(e)}"]

def ler_qrcode_de_pdf(conteudo_pdf):
    """Lê QR codes de arquivo PDF"""
    try:
        logger.debug("Convertendo PDF para imagens...")
        paginas = convert_from_bytes(conteudo_pdf, dpi=300)
        resultados = []
        
        for i, pagina in enumerate(paginas):
            logger.debug(f"Processando página {i+1} do PDF")
            # Converter PIL para array numpy e depois para OpenCV
            imagem_array = np.array(pagina)
            imagem_cv = cv2.cvtColor(imagem_array, cv2.COLOR_RGB2BGR)
            
            qrcodes_pagina = ler_qrcode_cv2(imagem_cv)
            # Filtrar mensagens de erro e adicionar apenas QR codes válidos
            qrcodes_validos = [qr for qr in qrcodes_pagina if not qr.startswith("Erro") and not qr.startswith("Nenhum")]
            resultados.extend(qrcodes_validos)
        
        return resultados if resultados else ["Nenhum QR Code detectado no PDF."]
        
    except Exception as e:
        logger.error(f"Erro ao processar PDF: {str(e)}")
        return [f"Erro ao processar PDF: {str(e)}"]

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = []
    
    if request.method == 'POST':
        arquivo = request.files.get('arquivo')
        
        if not arquivo or arquivo.filename == '':
            resultado = ["Nenhum arquivo enviado."]
        elif not allowed_file(arquivo.filename):
            resultado = ["Formato de arquivo não suportado. Formatos aceitos: PDF, JPG, JPEG, PNG, BMP, TIFF, WEBP"]
        else:
            try:
                nome_seguro = secure_filename(arquivo.filename)
                caminho_salvo = os.path.join(UPLOAD_FOLDER, nome_seguro)
                
                logger.debug(f"Salvando arquivo: {caminho_salvo}")
                arquivo.save(caminho_salvo)
                
                # Verificar se o arquivo foi salvo corretamente
                if not os.path.exists(caminho_salvo):
                    resultado = ["Erro ao salvar o arquivo."]
                else:
                    tamanho_arquivo = os.path.getsize(caminho_salvo)
                    logger.debug(f"Arquivo salvo com {tamanho_arquivo} bytes")
                    
                    extensao = nome_seguro.rsplit('.', 1)[1].lower()
                    
                    if extensao in ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp']:
                        resultado = ler_qrcode_de_imagem(caminho_salvo)
                    elif extensao == 'pdf':
                        with open(caminho_salvo, 'rb') as f:
                            conteudo = f.read()
                        resultado = ler_qrcode_de_pdf(conteudo)
                    
                    # Limpar arquivo temporário
                    try:
                        os.remove(caminho_salvo)
                    except Exception as e:
                        logger.warning(f"Não foi possível remover arquivo temporário: {e}")
                        
            except Exception as e:
                logger.error(f"Erro durante o processamento: {str(e)}")
                resultado = [f"Erro durante o processamento: {str(e)}"]
    
    return render_template('index.html', resultado=resultado)

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, request, render_template
import os
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from pdf2image import convert_from_bytes
from werkzeug.utils import secure_filename
from PIL import Image
import logging

# Configuração inicial
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp'}

# Configurar logs
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Utilitário: verificar extensão
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Leitura de QR Code com múltiplos métodos
def preprocessar_imagem(imagem_gray):
    resultados = []
    tecnicas = [
        imagem_gray,
        cv2.threshold(imagem_gray, 127, 255, cv2.THRESH_BINARY)[1],
        cv2.adaptiveThreshold(imagem_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
        cv2.GaussianBlur(imagem_gray, (3, 3), 0),
        cv2.equalizeHist(imagem_gray)
    ]
    for i, tecnica in enumerate(tecnicas):
        qrcodes = decode(tecnica)
        for qr in qrcodes:
            resultado = qr.data.decode('utf-8')
            if resultado not in resultados:
                resultados.append(resultado)
    return resultados

def ler_qrcode_cv2(imagem_cv):
    if imagem_cv is None or imagem_cv.size == 0:
        return ["Erro: Imagem vazia ou não carregada"]

    imagem_gray = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2GRAY) if len(imagem_cv.shape) == 3 else imagem_cv
    resultados = preprocessar_imagem(imagem_gray)
    return resultados if resultados else ["Nenhum QR Code detectado"]

def ler_qrcode_de_imagem(caminho_imagem):
    imagem_cv = cv2.imread(caminho_imagem)
    if imagem_cv is None:
        try:
            pil_image = Image.open(caminho_imagem)
            imagem_array = np.array(pil_image.convert("RGB"))
            imagem_cv = cv2.cvtColor(imagem_array, cv2.COLOR_RGB2BGR)
        except Exception as e:
            return [f"Erro ao abrir a imagem com PIL: {str(e)}"]

    return ler_qrcode_cv2(imagem_cv)

def ler_qrcode_de_pdf(conteudo_pdf):
    try:
        paginas = convert_from_bytes(conteudo_pdf, dpi=300)
        resultados = []
        for pagina in paginas:
            imagem_array = np.array(pagina)
            imagem_cv = cv2.cvtColor(imagem_array, cv2.COLOR_RGB2BGR)
            resultados += [qr for qr in ler_qrcode_cv2(imagem_cv) if not qr.startswith("Erro")]
        return resultados or ["Nenhum QR Code detectado no PDF."]
    except Exception as e:
        return [f"Erro ao processar PDF: {str(e)}"]

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = []

    if request.method == 'POST':
        arquivo = request.files.get('arquivo')

        if not arquivo or arquivo.filename == '':
            resultado = ["Nenhum arquivo enviado."]
        elif not allowed_file(arquivo.filename):
            resultado = ["Formato não suportado. Use PDF, JPG, PNG, BMP, TIFF ou WEBP."]
        else:
            try:
                nome_seguro = secure_filename(arquivo.filename)
                caminho = os.path.join(UPLOAD_FOLDER, nome_seguro)
                arquivo.save(caminho)

                extensao = nome_seguro.rsplit('.', 1)[1].lower()
                if extensao == 'pdf':
                    with open(caminho, 'rb') as f:
                        resultado = ler_qrcode_de_pdf(f.read())
                else:
                    resultado = ler_qrcode_de_imagem(caminho)

                os.remove(caminho)
            except Exception as e:
                logger.error(f"Erro: {e}")
                resultado = [f"Erro durante o processamento: {str(e)}"]

    return render_template('index.html', resultado=resultado)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

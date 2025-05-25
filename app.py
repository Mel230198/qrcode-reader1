from flask import Flask, request, render_template
import os
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from pdf2image import convert_from_bytes
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Pasta para armazenar arquivos temporários
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ler_qrcode_cv2(imagem_cv):
    try:
        qrcodes = decode(imagem_cv)
        if qrcodes:
            return [q.data.decode('utf-8') for q in qrcodes]
        return ["Nenhum QR Code detectado."]
    except Exception as e:
        return [f"Erro ao processar imagem: {str(e)}"]

def ler_qrcode_de_imagem(caminho_imagem):
    imagem_cv = cv2.imread(caminho_imagem)
    if imagem_cv is None:
        return [f"Erro ao abrir a imagem: {caminho_imagem}"]
    return ler_qrcode_cv2(imagem_cv)

def ler_qrcode_de_pdf(conteudo_pdf):
    try:
        paginas = convert_from_bytes(conteudo_pdf, dpi=300)
        resultados = []
        for pagina in paginas:
            imagem_cv = cv2.cvtColor(np.array(pagina), cv2.COLOR_RGB2BGR)
            resultados.extend(ler_qrcode_cv2(imagem_cv))
        return resultados if resultados else ["Nenhum QR Code detectado no PDF."]
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
            resultado = ["Formato de arquivo não suportado."]
        else:
            nome_seguro = secure_filename(arquivo.filename)
            caminho_salvo = os.path.join(UPLOAD_FOLDER, nome_seguro)
            arquivo.save(caminho_salvo)

            extensao = nome_seguro.rsplit('.', 1)[1].lower()

            if extensao in ['jpg', 'jpeg', 'png']:
                resultado = ler_qrcode_de_imagem(caminho_salvo)
            elif extensao == 'pdf':
                with open(caminho_salvo, 'rb') as f:
                    conteudo = f.read()
                resultado = ler_qrcode_de_pdf(conteudo)

            os.remove(caminho_salvo)

    return render_template('index.html', resultado=resultado)

if __name__ == '__main__':
    app.run(debug=True)

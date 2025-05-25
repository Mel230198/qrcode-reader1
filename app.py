from flask import Flask, request, render_template
import os
from pyzbar.pyzbar import decode
import cv2
from PIL import Image
from pdf2image import convert_from_bytes

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def ler_qrcode_de_imagem(caminho_imagem):
    imagem = cv2.imread(caminho_imagem)
    if imagem is None:
        return []
    qrcodes = decode(imagem)
    return [q.data.decode('utf-8') for q in qrcodes]

def ler_qrcode_de_pdf(conteudo_pdf):
    paginas = convert_from_bytes(conteudo_pdf, dpi=300)
    resultados = []
    for i, pagina in enumerate(paginas):
        caminho_temp = os.path.join(UPLOAD_FOLDER, f"pagina_{i}.png")
        pagina.save(caminho_temp, 'PNG')
        resultados += ler_qrcode_de_imagem(caminho_temp)
        os.remove(caminho_temp)
    return resultados

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = []
    if request.method == 'POST':
        arquivo = request.files['arquivo']
        if not arquivo:
            return render_template('index.html', resultado=["Arquivo não enviado."])
        caminho_salvo = os.path.join(UPLOAD_FOLDER, arquivo.filename)
        arquivo.save(caminho_salvo)

        if arquivo.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            resultado = ler_qrcode_de_imagem(caminho_salvo)
        elif arquivo.filename.lower().endswith('.pdf'):
            with open(caminho_salvo, 'rb') as f:
                conteudo = f.read()
            resultado = ler_qrcode_de_pdf(conteudo)
        else:
            resultado = ["Formato de arquivo não suportado."]

        os.remove(caminho_salvo)

    return render_template('index.html', resultado=resultado)

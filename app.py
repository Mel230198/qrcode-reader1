from flask import Flask, request, render_template
import os
from pyzbar.pyzbar import decode
from PIL import Image
from pdf2image import convert_from_bytes

app = Flask(__name__)

# Pasta para armazenar arquivos temporários
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def ler_qrcode_de_imagem(caminho_imagem):
    try:
        imagem = Image.open(caminho_imagem).convert('L')  # Converte para escala de cinza
        qrcodes = decode(imagem)
        return [q.data.decode('utf-8') for q in qrcodes]
    except Exception as e:
        return [f"Erro ao ler imagem: {str(e)}"]

def ler_qrcode_de_pdf(conteudo_pdf):
    try:
        paginas = convert_from_bytes(conteudo_pdf, dpi=300)
        resultados = []
        for i, pagina in enumerate(paginas):
            caminho_temp = os.path.join(UPLOAD_FOLDER, f"pagina_{i}.png")
            pagina.save(caminho_temp, 'PNG')
            resultados.extend(ler_qrcode_de_imagem(caminho_temp))
            os.remove(caminho_temp)
        return resultados
    except Exception as e:
        return [f"Erro ao processar PDF: {str(e)}"]

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = []
    if request.method == 'POST':
        arquivo = request.files.get('arquivo')
        if not arquivo or arquivo.filename == '':
            resultado = ["Nenhum arquivo enviado."]
        else:
            caminho_salvo = os.path.join(UPLOAD_FOLDER, arquivo.filename)
            arquivo.save(caminho_salvo)

            extensao = arquivo.filename.lower().split('.')[-1]
            if extensao in ['jpg', 'jpeg', 'png']:
                resultado = ler_qrcode_de_imagem(caminho_salvo)
            elif extensao == 'pdf':
                with open(caminho_salvo, 'rb') as f:
                    conteudo = f.read()
                resultado = ler_qrcode_de_pdf(conteudo)
            else:
                resultado = ["Formato de arquivo não suportado."]

            os.remove(caminho_salvo)

    return render_template('index.html', resultado=resultado)


from flask import Flask, request, render_template
import os
from werkzeug.utils import secure_filename
from pyzbar.pyzbar import decode
from pdf2image import convert_from_bytes
from PIL import Image

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ler_qrcode_imagem(caminho_imagem):
    """Lê QR Codes diretamente da imagem usando Pillow + pyzbar."""
    try:
        imagem = Image.open(caminho_imagem)
        print(f"Formato da imagem: {imagem.mode}")
        qrcodes = decode(imagem)
        if qrcodes:
            return [q.data.decode('utf-8') for q in qrcodes]
        else:
            return ["Nenhum QR Code detectado na imagem."]
    except Exception as e:
        return [f"Erro ao abrir/processar a imagem: {str(e)}"]

def ler_qrcode_pdf(conteudo_pdf):
    """Converte PDF em imagens e lê QR Codes de cada página."""
    try:
        paginas = convert_from_bytes(conteudo_pdf, dpi=300)
        resultados = []
        for idx, pagina in enumerate(paginas, 1):
            print(f"Lendo QR Code na página {idx} do PDF...")
            qrcodes = decode(pagina)
            if qrcodes:
                resultados.extend([q.data.decode('utf-8') for q in qrcodes])
        if resultados:
            return resultados
        else:
            return ["Nenhum QR Code detectado no PDF."]
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
            resultado = ["Formato de arquivo não suportado. Use PDF, JPG, JPEG ou PNG."]
        else:
            nome_seguro = secure_filename(arquivo.filename)
            caminho_salvo = os.path.join(UPLOAD_FOLDER, nome_seguro)
            arquivo.save(caminho_salvo)

            extensao = nome_seguro.rsplit('.', 1)[1].lower()

            if extensao == 'pdf':
                with open(caminho_salvo, 'rb') as f:
                    conteudo = f.read()
                resultado = ler_qrcode_pdf(conteudo)
            else:  # jpg, jpeg, png
                resultado = ler_qrcode_imagem(caminho_salvo)

            # Apaga o arquivo temporário após processar
            os.remove(caminho_salvo)

    return render_template('index.html', resultado=resultado)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

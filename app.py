from flask import Flask, request, render_template
import os
import logging
from werkzeug.utils import secure_filename
from utils import allowed_file, ler_qrcode_de_pdf, ler_qrcode_de_imagem

# Configuração inicial
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Extensões permitidas
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp'}

# Logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = []

    if request.method == 'POST':
        arquivo = request.files.get('arquivo')

        if not arquivo or arquivo.filename == '':
            resultado = ["Nenhum arquivo enviado."]
        elif not allowed_file(arquivo.filename, ALLOWED_EXTENSIONS):
            resultado = ["Formato não suportado. Use PDF, JPG, PNG, BMP, TIFF ou WEBP."]
        else:
            try:
                extensao = arquivo.filename.rsplit('.', 1)[1].lower()
                if extensao == 'pdf':
                    resultado = ler_qrcode_de_pdf(arquivo.read())
                else:
                    nome_seguro = secure_filename(arquivo.filename)
                    caminho = os.path.join(UPLOAD_FOLDER, nome_seguro)
                    arquivo.save(caminho)
                    resultado = ler_qrcode_de_imagem(caminho)
                    os.remove(caminho)
            except Exception as e:
                logger.exception("Erro durante o processamento")
                resultado = [f"Erro durante o processamento: {str(e)}"]

    return render_template('index.html', resultado=resultado)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

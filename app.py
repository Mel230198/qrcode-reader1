from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from utils import ler_qrcode_de_imagem, ler_qrcode_de_pdf, allowed_file

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'erro': 'Nenhum arquivo enviado.'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'erro': 'Nome de arquivo vazio.'}), 400

    if allowed_file(file.filename, app.config['ALLOWED_EXTENSIONS']):
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        file.save(file_path)

        try:
            if file_ext == 'pdf':
                with open(file_path, 'rb') as f:
                    conteudo_pdf = f.read()
                resultados = ler_qrcode_de_pdf(conteudo_pdf)
            else:
                resultados = ler_qrcode_de_imagem(file_path)
        finally:
            os.remove(file_path)

        return jsonify({'resultados': resultados})

    return jsonify({'erro': 'Extensão de arquivo não permitida.'}), 400

if __name__ == '__main__':
    app.run(debug=True)

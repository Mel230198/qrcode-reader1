import subprocess
import os
import cv2
import numpy as np
from pdf2image import convert_from_bytes
from PIL import Image
import logging

# Logger
logger = logging.getLogger("utils")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# Caminho do ZXing .jar
ZXING_JAR_PATH = os.path.join(os.path.dirname(__file__), 'libs', 'javase-3.5.2.jar')

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def redimensionar_imagem(imagem_cv, largura_max=2000):
    altura, largura = imagem_cv.shape[:2]
    if largura > largura_max:
        escala = largura_max / largura
        nova_dimensao = (int(largura * escala), int(altura * escala))
        return cv2.resize(imagem_cv, nova_dimensao, interpolation=cv2.INTER_AREA)
    return imagem_cv

def salvar_imagem_temporaria(imagem_cv):
    temp_path = 'temp_img.png'
    cv2.imwrite(temp_path, imagem_cv)
    return temp_path

def executar_zxing(caminho_arquivo):
    """
    Executa ZXing para ler QR Code ou código de barras.
    """
    try:
        comando = [
            'java', '-cp', ZXING_JAR_PATH,
            'com.google.zxing.client.j2se.CommandLineRunner',
            caminho_arquivo
        ]

        resultado = subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if resultado.returncode == 0:
            saida = resultado.stdout.strip()
            if saida:
                linhas = saida.splitlines()
                textos = [linha for linha in linhas if not linha.startswith('file:')]
                return textos if textos else ["Nenhum QR Code encontrado."]
            else:
                return ["Nenhum QR Code encontrado."]
        else:
            logger.error(f"Erro ZXing: {resultado.stderr}")
            return [f"Erro ZXing: {resultado.stderr.strip()}"]

    except Exception as e:
        logger.exception("Falha ao executar ZXing")
        return [f"Erro ao executar ZXing: {str(e)}"]

def ler_qrcode_de_imagem(caminho_imagem):
    try:
        imagem_cv = cv2.imread(caminho_imagem)

        if imagem_cv is None:
            imagem_pil = Image.open(caminho_imagem).convert("RGB")
            imagem_cv = cv2.cvtColor(np.array(imagem_pil), cv2.COLOR_RGB2BGR)

        if imagem_cv is None:
            return ["Erro ao carregar a imagem."]

        imagem_cv = redimensionar_imagem(imagem_cv)
        temp_path = salvar_imagem_temporaria(imagem_cv)

        resultado = executar_zxing(temp_path)

        os.remove(temp_path)
        return resultado

    except Exception as e:
        logger.exception("Erro ao processar imagem")
        return [f"Erro ao processar imagem: {str(e)}"]

def ler_qrcode_de_pdf(conteudo_pdf):
    try:
        paginas = convert_from_bytes(conteudo_pdf, dpi=300)
        resultados = set()

        for idx, pagina in enumerate(paginas):
            logger.info(f"Processando página {idx + 1}")
            imagem_cv = cv2.cvtColor(np.array(pagina), cv2.COLOR_RGB2BGR)
            imagem_cv = redimensionar_imagem(imagem_cv)
            temp_path = salvar_imagem_temporaria(imagem_cv)

            textos = executar_zxing(temp_path)
            resultados.update(textos)

            os.remove(temp_path)

        return list(resultados) or ["Nenhum QR Code encontrado no PDF."]

    except Exception as e:
        logger.exception("Erro ao processar PDF")
        return [f"Erro ao processar PDF: {str(e)}"]

import cv2
import numpy as np
import logging
from pyzbar.pyzbar import decode
from pdf2image import convert_from_bytes
from PIL import Image

# Configuração de log
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def aplicar_tecnicas_preprocessamento(imagem_gray):
    """
    Aplica várias técnicas de pré-processamento e tenta decodificar QR Codes.
    Retorna uma lista de textos encontrados e técnicas utilizadas.
    """
    resultados = []
    tecnicas_aplicadas = {
        "original": imagem_gray,
        "threshold_binario": cv2.threshold(imagem_gray, 127, 255, cv2.THRESH_BINARY)[1],
        "adaptive_threshold": cv2.adaptiveThreshold(imagem_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
        "gaussian_blur": cv2.GaussianBlur(imagem_gray, (3, 3), 0),
        "equalize_hist": cv2.equalizeHist(imagem_gray),
    }

    for nome, imagem_processada in tecnicas_aplicadas.items():
        qrcodes = decode(imagem_processada)
        for qr in qrcodes:
            texto = qr.data.decode('utf-8')
            if texto not in resultados:
                logger.info(f"QR Code detectado com técnica: {nome}")
                resultados.append(texto)

    return resultados

def ler_qrcode_de_imagem(caminho_imagem):
    """
    Tenta ler QR Codes de uma imagem (JPG, PNG, etc.).
    Utiliza várias técnicas de pré-processamento para aumentar a taxa de sucesso.
    """
    try:
        imagem_cv = cv2.imread(caminho_imagem)

        # Se OpenCV falhar, usar PIL
        if imagem_cv is None:
            pil_image = Image.open(caminho_imagem).convert("RGB")
            imagem_cv = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        if imagem_cv is None:
            return ["Erro ao carregar a imagem."]

        # Reduzir imagem grande para 2000px de largura máxima (mantendo proporção)
        max_largura = 2000
        if imagem_cv.shape[1] > max_largura:
            escala = max_largura / imagem_cv.shape[1]
            nova_dimensao = (int(imagem_cv.shape[1] * escala), int(imagem_cv.shape[0] * escala))
            imagem_cv = cv2.resize(imagem_cv, nova_dimensao, interpolation=cv2.INTER_AREA)

        imagem_gray = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2GRAY)
        resultados = aplicar_tecnicas_preprocessamento(imagem_gray)

        if not resultados:
            return ["Nenhum QR Code foi encontrado na imagem. Verifique se ela está nítida, bem iluminada e com o QR Code visível."]
        return resultados

    except Exception as e:
        logger.exception("Erro ao processar imagem")
        return [f"Erro ao processar imagem: {str(e)}"]

def ler_qrcode_de_pdf(conteudo_pdf):
    """
    Converte páginas do PDF em imagens e tenta extrair QR Codes de cada página.
    """
    try:
        paginas = convert_from_bytes(conteudo_pdf, dpi=300)
        resultados = []

        for idx, pagina in enumerate(paginas):
            logger.info(f"Processando página {idx + 1} do PDF")
            imagem_cv = cv2.cvtColor(np.array(pagina), cv2.COLOR_RGB2BGR)
            imagem_gray = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2GRAY)
            resultados.extend(aplicar_tecnicas_preprocessamento(imagem_gray))

        if not resultados:
            return ["Nenhum QR Code foi encontrado no PDF. Verifique se o QR Code está visível e bem impresso."]
        return list(set(resultados))  # Evita duplicatas

    except Exception as e:
        logger.exception("Erro ao processar PDF")
        return [f"Erro ao processar PDF: {str(e)}"]

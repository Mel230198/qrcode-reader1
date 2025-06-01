import cv2
import numpy as np
import logging
from pyzbar.pyzbar import decode
from pdf2image import convert_from_bytes
from PIL import Image

# Configuração de log
logger = logging.getLogger("utils")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def redimensionar_imagem(imagem_cv, largura_max=2000):
    if imagem_cv.shape[1] > largura_max:
        escala = largura_max / imagem_cv.shape[1]
        nova_dimensao = (int(imagem_cv.shape[1] * escala), int(imagem_cv.shape[0] * escala))
        imagem_cv = cv2.resize(imagem_cv, nova_dimensao, interpolation=cv2.INTER_AREA)
    return imagem_cv

def aplicar_tecnicas_preprocessamento(imagem_gray):
    """
    Aplica várias técnicas de pré-processamento e tenta decodificar QR Codes.
    Retorna uma lista de textos encontrados.
    """
    resultados = set()
    tecnicas_aplicadas = {
        "original": imagem_gray,
        "threshold_binario": cv2.threshold(imagem_gray, 127, 255, cv2.THRESH_BINARY)[1],
        "adaptive_threshold": cv2.adaptiveThreshold(imagem_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
        "gaussian_blur": cv2.GaussianBlur(imagem_gray, (3, 3), 0),
        "equalize_hist": cv2.equalizeHist(imagem_gray),
        "invertido": cv2.bitwise_not(imagem_gray),
    }

    for nome, imagem_processada in tecnicas_aplicadas.items():
        qrcodes = decode(imagem_processada)
        for qr in qrcodes:
            texto = qr.data.decode('utf-8')
            if texto not in resultados:
                logger.info(f"QR Code detectado com técnica: {nome}")
                resultados.add(texto)

    return list(resultados)

def detectar_qrcode_opencv(imagem_gray):
    """Fallback para tentar detectar QR Code usando OpenCV."""
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(imagem_gray)
    return data if data else None

def ler_qrcode_de_imagem(caminho_imagem):
    try:
        imagem_cv = cv2.imread(caminho_imagem)

        if imagem_cv is None:
            pil_image = Image.open(caminho_imagem).convert("RGB")
            imagem_cv = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        if imagem_cv is None:
            return ["Erro ao carregar a imagem."]

        imagem_cv = redimensionar_imagem(imagem_cv)
        imagem_gray = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2GRAY)
        resultados = aplicar_tecnicas_preprocessamento(imagem_gray)

        if not resultados:
            fallback = detectar_qrcode_opencv(imagem_gray)
            if fallback:
                resultados.append(fallback)

        if not resultados:
            return ["Nenhum QR Code foi encontrado na imagem. Verifique se ela está nítida, bem iluminada e com o QR Code visível."]
        return resultados

    except Exception as e:
        logger.exception("Erro ao processar imagem")
        return [f"Erro ao processar imagem: {str(e)}"]

def ler_qrcode_de_pdf(conteudo_pdf):
    try:
        paginas = convert_from_bytes(conteudo_pdf, dpi=300)
        resultados = set()

        for idx, pagina in enumerate(paginas):
            logger.info(f"Processando página {idx + 1} do PDF")
            imagem_cv = cv2.cvtColor(np.array(pagina), cv2.COLOR_RGB2BGR)
            imagem_cv = redimensionar_imagem(imagem_cv)
            imagem_gray = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2GRAY)
            resultados.update(aplicar_tecnicas_preprocessamento(imagem_gray))

            if not resultados:
                fallback = detectar_qrcode_opencv(imagem_gray)
                if fallback:
                    resultados.add(fallback)

        if not resultados:
            return ["Nenhum QR Code foi encontrado no PDF. Verifique se o QR Code está visível e bem impresso."]
        return list(resultados)

    except Exception as e:
        logger.exception("Erro ao processar PDF")
        return [f"Erro ao processar PDF: {str(e)}"]


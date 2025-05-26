
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from pdf2image import convert_from_bytes
from PIL import Image

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def preprocessar_imagem(imagem_gray):
    resultados = []
    tecnicas = [
        imagem_gray,
        cv2.threshold(imagem_gray, 127, 255, cv2.THRESH_BINARY)[1],
        cv2.adaptiveThreshold(imagem_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
        cv2.GaussianBlur(imagem_gray, (3, 3), 0),
        cv2.equalizeHist(imagem_gray)
    ]
    for tecnica in tecnicas:
        for qr in decode(tecnica):
            texto = qr.data.decode('utf-8')
            if texto not in resultados:
                resultados.append(texto)
    return resultados

def ler_qrcode_de_imagem(caminho_imagem):
    try:
        imagem_cv = cv2.imread(caminho_imagem)
        if imagem_cv is None:
            pil_image = Image.open(caminho_imagem).convert("RGB")
            imagem_cv = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        if imagem_cv is None:
            return ["Erro ao carregar a imagem."]

        imagem_gray = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2GRAY)
        resultados = preprocessar_imagem(imagem_gray)

        if not resultados:
            return ["Nenhum QR Code foi encontrado na imagem. Verifique se ela está nítida, bem iluminada e com o QR Code visível."]
        return resultados

    except Exception as e:
        return [f"Erro ao processar imagem: {str(e)}"]

def ler_qrcode_de_pdf(conteudo_pdf):
    try:
        paginas = convert_from_bytes(conteudo_pdf, dpi=300)
        resultados = []

        for pagina in paginas:
            imagem_cv = cv2.cvtColor(np.array(pagina), cv2.COLOR_RGB2BGR)
            imagem_gray = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2GRAY)
            resultados.extend(preprocessar_imagem(imagem_gray))

        if not resultados:
            return ["Nenhum QR Code foi encontrado no PDF. Verifique se o QR Code está visível e bem impresso."]
        return resultados

    except Exception as e:
        return [f"Erro ao processar PDF: {str(e)}"]

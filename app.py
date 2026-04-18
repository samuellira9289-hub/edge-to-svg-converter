import os
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import io
import base64

app = Flask(__name__)

# Configurações
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Criar pasta de uploads se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def image_to_base64(image_array):
    """Converter imagem numpy para base64"""
    _, buffer = cv2.imencode('.png', image_array)
    img_base64 = base64.b64encode(buffer).decode()
    return f"data:image/png;base64,{img_base64}"


def apply_noise_removal(gray_image, method='bilateral', kernel_size=5):
    """
    Aplica filtro de limpeza (remoção de ruído) à imagem em escala de cinza.
    
    Parâmetros:
    - gray_image: imagem em escala de cinza
    - method: tipo de filtro ('bilateral', 'morphological', 'median')
    - kernel_size: tamanho do kernel (deve ser ímpar)
    
    Retorna: imagem com ruído reduzido
    """
    if kernel_size % 2 == 0:
        kernel_size += 1
    
    if method == 'bilateral':
        # Bilateral filter: preserva bordas enquanto remove ruído
        # Parâmetros: (imagem, diâmetro, sigma_color, sigma_space)
        cleaned = cv2.bilateralFilter(gray_image, kernel_size, 75, 75)
    elif method == 'morphological':
        # Operações morfológicas: abertura (erosão seguida de dilatação)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        cleaned = cv2.morphologyEx(gray_image, cv2.MORPH_OPEN, kernel, iterations=1)
    elif method == 'median':
        # Median filter: eficaz para ruído sal-e-pimenta
        cleaned = cv2.medianBlur(gray_image, kernel_size)
    else:
        cleaned = gray_image
    
    return cleaned


def apply_auto_contrast(gray_image, method='clahe', clip_limit=2.0, tile_size=8):
    """
    Melhora automaticamente o contraste da imagem.
    
    Parâmetros:
    - gray_image: imagem em escala de cinza
    - method: tipo de contraste ('clahe', 'histogram_eq', 'auto_levels')
    - clip_limit: limite de clipping para CLAHE (padrão: 2.0)
    - tile_size: tamanho da grade para CLAHE (padrão: 8)
    
    Retorna: imagem com contraste melhorado
    """
    if method == 'clahe':
        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        # Melhora contraste local sem amplificar ruído
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
        enhanced = clahe.apply(gray_image)
    elif method == 'histogram_eq':
        # Equalização global do histograma
        enhanced = cv2.equalizeHist(gray_image)
    elif method == 'auto_levels':
        # Normalização automática (stretch dos valores)
        enhanced = cv2.normalize(gray_image, None, 0, 255, cv2.NORM_MINMAX)
    else:
        enhanced = gray_image
    
    return enhanced


def calculate_auto_threshold(gray_image, method='otsu'):
    """
    Calcula automaticamente o valor de threshold para a imagem.
    
    Parâmetros:
    - gray_image: imagem em escala de cinza
    - method: tipo de método ('otsu', 'triangle', 'adaptive')
    
    Retorna: valor de threshold calculado automaticamente
    """
    if method == 'otsu':
        # Método de Otsu: encontra o melhor threshold minimizando variância intra-classe
        threshold, _ = cv2.threshold(gray_image, 0, 255, cv2.THRESH_OTSU)
        return threshold
    elif method == 'triangle':
        # Método Triangle: bom para imagens bimodais
        threshold, _ = cv2.threshold(gray_image, 0, 255, cv2.THRESH_TRIANGLE)
        return threshold
    else:
        # Padrão: retorna 127 (meio do intervalo)
        return 127


def enhance_edge_detection(gray_image, use_preprocessing=True, denoise_strength=5):
    """
    Melhora a detecção de bordas com pré-processamento otimizado.
    
    Parâmetros:
    - gray_image: imagem em escala de cinza
    - use_preprocessing: aplicar pré-processamento
    - denoise_strength: força do denoising (1-10)
    
    Retorna: imagem pré-processada otimizada para detecção de bordas
    """
    if not use_preprocessing:
        return gray_image
    
    # 1. Remover ruído com bilateral filter (preserva bordas)
    denoised = cv2.bilateralFilter(gray_image, 9, denoise_strength, denoise_strength)
    
    # 2. Melhorar contraste com CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # 3. Aplicar slight blur para suavizar ruído residual
    smoothed = cv2.GaussianBlur(enhanced, (3, 3), 0)
    
    return smoothed


def process_image(image_path, threshold1=50, threshold2=150, blur_size=5, iterations=1,
                  auto_threshold=False, auto_contrast=True, noise_removal=True):
    """
    Processa a imagem para detecção de bordas otimizada com melhorias.
    
    Parâmetros:
    - image_path: caminho da imagem
    - threshold1: threshold inferior do Canny
    - threshold2: threshold superior do Canny
    - blur_size: tamanho do kernel de desfoque
    - iterations: iterações de operações morfológicas
    - auto_threshold: usar threshold automático (Otsu)
    - auto_contrast: melhorar contraste automaticamente
    - noise_removal: remover ruído da imagem
    
    Retorna: (imagem de bordas, imagem original)
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Não foi possível ler a imagem")
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Remover ruído (bilateral filter + morphological opening)
    if noise_removal:
        gray = apply_noise_removal(gray, method='bilateral', kernel_size=5)
    
    # 2. Melhorar contraste
    if auto_contrast:
        gray = apply_auto_contrast(gray, method='clahe', clip_limit=2.0, tile_size=8)
    
    # 3. Pré-processamento aprimorado para detecção de bordas
    gray = enhance_edge_detection(gray, use_preprocessing=True, denoise_strength=5)
    
    # 4. Calcular threshold automático se solicitado
    if auto_threshold:
        threshold1 = calculate_auto_threshold(gray, method='otsu')
        # Usar razão padrão para threshold2
        threshold2 = min(255, threshold1 * 3)
    
    # 5. Aplicar desfoque Gaussiano se configurado
    if blur_size > 0:
        if blur_size % 2 == 0:
            blur_size += 1
        gray = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
    
    # 6. Detecção de bordas com Canny
    edges = cv2.Canny(gray, threshold1, threshold2)
    
    # 7. Operações morfológicas para unir bordas próximas
    if iterations > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=iterations)
        edges = cv2.erode(edges, kernel, iterations=iterations)
    
    return edges, img


def edges_to_svg(edges_image, min_area=20, epsilon_factor=0.005):
    """
    Converte imagem de bordas para SVG otimizado para corte a laser.
    - Filtra contornos por área (remove ruído)
    - Suaviza contornos com aproximação poligonal controlada
    - Gera path SVG limpo
    """
    height, width = edges_image.shape
    
    # Encontrar contornos com hierarquia para manter furos (RETR_TREE)
    contours, hierarchy = cv2.findContours(edges_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<!-- Gerado por Otimizador de Corte a Laser -->',
        '<style>path { stroke: black; fill: none; stroke-width: 1; vector-effect: non-scaling-stroke; }</style>'
    ]
    
    if contours:
        for i, contour in enumerate(contours):
            # 1. Remover ruído por área mínima
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
            
            # 2. Suavização e Otimização de Pontos (Douglas-Peucker)
            epsilon = epsilon_factor * cv2.arcLength(contour, True)
            simplified = cv2.approxPolyDP(contour, epsilon, True)
            
            if len(simplified) < 2:
                continue
                
            # 3. Gerar Path Data
            path_parts = []
            for j, point in enumerate(simplified):
                x, y = point[0]
                cmd = "M" if j == 0 else "L"
                path_parts.append(f"{cmd}{x} {y}")
            
            path_data = " ".join(path_parts) + " Z"
            svg_lines.append(f'  <path d="{path_data}" />')
    
    svg_lines.append('</svg>')
    return '\n'.join(svg_lines)


def edges_to_plt(edges_image, min_area=20, epsilon_factor=0.005, dpi=300, paper_width_mm=210, paper_height_mm=297):
    """
    Converte imagem de bordas para PLT (HPGL - Hewlett-Packard Graphics Language).
    
    Parâmetros:
    - edges_image: imagem binária com bordas detectadas
    - min_area: área mínima do contorno para ser considerado
    - epsilon_factor: fator de simplificação de contornos (Douglas-Peucker)
    - dpi: resolução em pontos por polegada (padrão: 300 DPI)
    - paper_width_mm: largura do papel em milímetros (padrão: A4 210mm)
    - paper_height_mm: altura do papel em milímetros (padrão: A4 297mm)
    
    Retorna: string com comandos HPGL
    """
    height, width = edges_image.shape
    
    # Encontrar contornos
    contours, hierarchy = cv2.findContours(edges_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # Conversão de pixels para unidades HPGL (0.025 mm por unidade)
    mm_to_hpgl_unit = 40  # 1 mm ≈ 40 unidades HPGL
    
    # Calcular escala de pixels para mm
    pixels_to_mm_x = paper_width_mm / width
    pixels_to_mm_y = paper_height_mm / height
    
    # Usar a menor escala para manter proporção
    pixels_to_mm = min(pixels_to_mm_x, pixels_to_mm_y)
    
    # Converter para unidades HPGL
    pixels_to_hpgl = pixels_to_mm * mm_to_hpgl_unit
    
    # Inicializar comandos HPGL
    hpgl_commands = []
    
    # Cabeçalho HPGL
    hpgl_commands.append("IN;SP1;")  # Initialize, Select Pen 1
    hpgl_commands.append(f"SC0,{width},0,{height};")  # Scale (pixels)
    
    if contours:
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
            
            epsilon = epsilon_factor * cv2.arcLength(contour, True)
            simplified = cv2.approxPolyDP(contour, epsilon, True)
            
            if len(simplified) < 2:
                continue
            
            # Mover para o primeiro ponto e desenhar
            x, y = simplified[0][0]
            hpgl_commands.append(f"PU;PA{x},{height-y};PD;")  # Pen Up, Plot Absolute, Pen Down
            
            for point in simplified[1:]:
                x, y = point[0]
                hpgl_commands.append(f"PA{x},{height-y};")
            
            hpgl_commands.append("PU;") # Pen Up after drawing contour
            
    hpgl_commands.append("PG;") # Page Eject
    return '\n'.join(hpgl_commands)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Tipo de arquivo não permitido'}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Parâmetros de processamento da imagem
        threshold1 = int(request.form.get('threshold1', 50))
        threshold2 = int(request.form.get('threshold2', 150))
        blur_size = int(request.form.get('blur_size', 5))
        iterations = int(request.form.get('iterations', 1))
        min_area = int(request.form.get('min_area', 20))
        epsilon_factor = float(request.form.get('epsilon_factor', 0.005))
        output_format = request.form.get('output_format', 'svg')
        auto_threshold = request.form.get('auto_threshold') == 'true'
        auto_contrast = request.form.get('auto_contrast') == 'true'
        noise_removal = request.form.get('noise_removal') == 'true'
        
        edges, original_img = process_image(filepath, threshold1, threshold2, blur_size, iterations,
                                            auto_threshold, auto_contrast, noise_removal)
        
        if output_format == 'svg':
            svg_output = edges_to_svg(edges, min_area, epsilon_factor)
            response = io.BytesIO(svg_output.encode('utf-8'))
            return send_file(response, mimetype='image/svg+xml', as_attachment=True, download_name=f'{os.path.splitext(filename)[0]}.svg')
        elif output_format == 'plt':
            plt_output = edges_to_plt(edges, min_area, epsilon_factor)
            response = io.BytesIO(plt_output.encode('utf-8'))
            return send_file(response, mimetype='application/octet-stream', as_attachment=True, download_name=f'{os.path.splitext(filename)[0]}.plt')
        else:
            # Retornar imagem de bordas como PNG para visualização
            _, buffer = cv2.imencode('.png', edges)
            img_base64 = base64.b64encode(buffer).decode()
            return jsonify({'image_base64': f'data:image/png;base64,{img_base64}'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

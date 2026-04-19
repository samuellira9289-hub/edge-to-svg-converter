import os
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import io
import base64
from PIL import Image

app = Flask(__name__)

# Configurações
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
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


def get_image_info(filepath):
    """Extrair DPI e dimensões reais da imagem"""
    with Image.open(filepath) as img:
        width_px, height_px = img.size
        dpi = img.info.get('dpi', (300, 300))
        # Se DPI for uma tupla, pegamos o primeiro valor (geralmente X=Y)
        if isinstance(dpi, tuple):
            dpi_val = dpi[0]
        else:
            dpi_val = dpi
            
        # Se DPI for 0 ou inválido, assumir 300 como padrão profissional de scanner
        if not dpi_val or dpi_val < 1:
            dpi_val = 300
            
        width_mm = (width_px / dpi_val) * 25.4
        height_mm = (height_px / dpi_val) * 25.4
        
        return {
            'width_px': width_px,
            'height_px': height_px,
            'dpi': dpi_val,
            'width_mm': round(width_mm, 2),
            'height_mm': round(height_mm, 2)
        }


def apply_noise_removal(gray_image, method='bilateral', kernel_size=5):
    if kernel_size % 2 == 0:
        kernel_size += 1
    if method == 'bilateral':
        cleaned = cv2.bilateralFilter(gray_image, kernel_size, 75, 75)
    elif method == 'morphological':
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        cleaned = cv2.morphologyEx(gray_image, cv2.MORPH_OPEN, kernel, iterations=1)
    elif method == 'median':
        cleaned = cv2.medianBlur(gray_image, kernel_size)
    else:
        cleaned = gray_image
    return cleaned


def apply_auto_contrast(gray_image, method='clahe', clip_limit=2.0, tile_size=8):
    if method == 'clahe':
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
        enhanced = clahe.apply(gray_image)
    elif method == 'histogram_eq':
        enhanced = cv2.equalizeHist(gray_image)
    elif method == 'auto_levels':
        enhanced = cv2.normalize(gray_image, None, 0, 255, cv2.NORM_MINMAX)
    else:
        enhanced = gray_image
    return enhanced


def calculate_auto_threshold(gray_image, method='otsu'):
    if method == 'otsu':
        threshold, _ = cv2.threshold(gray_image, 0, 255, cv2.THRESH_OTSU)
        return threshold
    elif method == 'triangle':
        threshold, _ = cv2.threshold(gray_image, 0, 255, cv2.THRESH_TRIANGLE)
        return threshold
    else:
        return 127


def process_image(image_path, threshold1=50, threshold2=150, blur_size=5, iterations=1,
                  auto_threshold=False, auto_contrast=True, noise_removal=True):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Não foi possível ler a imagem")
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    if noise_removal:
        gray = apply_noise_removal(gray, method='bilateral', kernel_size=5)
    
    if auto_contrast:
        gray = apply_auto_contrast(gray, method='clahe', clip_limit=2.0, tile_size=8)
    
    if auto_threshold:
        threshold1 = calculate_auto_threshold(gray, method='otsu')
        threshold2 = min(255, threshold1 * 3)
    
    if blur_size > 0:
        if blur_size % 2 == 0:
            blur_size += 1
        gray = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
    
    edges = cv2.Canny(gray, threshold1, threshold2)
    
    if iterations > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=iterations)
        edges = cv2.erode(edges, kernel, iterations=iterations)
    
    return edges, img


def edges_to_svg(edges_image, min_area=20, epsilon_factor=0.005, target_width_mm=None, target_height_mm=None):
    """Converte bordas para SVG com dimensões físicas reais em mm"""
    height_px, width_px = edges_image.shape
    
    # Se dimensões não forem fornecidas, usar 1px = 1mm (fallback)
    if not target_width_mm: target_width_mm = width_px
    if not target_height_mm: target_height_mm = height_px
    
    # Fator de escala de pixel para mm
    scale_x = target_width_mm / width_px
    scale_y = target_height_mm / height_px
    
    contours, _ = cv2.findContours(edges_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # SVG usa mm como unidade para precisão laser
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{target_width_mm}mm" height="{target_height_mm}mm" viewBox="0 0 {target_width_mm} {target_height_mm}">',
        '<!-- Gerado por Otimizador de Corte a Laser Profissional -->',
        '<style>path { stroke: black; fill: none; stroke-width: 0.1mm; vector-effect: non-scaling-stroke; }</style>'
    ]
    
    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue
            
        epsilon = epsilon_factor * cv2.arcLength(contour, True)
        simplified = cv2.approxPolyDP(contour, epsilon, True)
        
        if len(simplified) < 2:
            continue
            
        path_parts = []
        for j, point in enumerate(simplified):
            x, y = point[0]
            # Converter pixel para mm
            x_mm = round(x * scale_x, 4)
            y_mm = round(y * scale_y, 4)
            cmd = "M" if j == 0 else "L"
            path_parts.append(f"{cmd}{x_mm} {y_mm}")
        
        path_data = " ".join(path_parts) + " Z"
        svg_lines.append(f'  <path d="{path_data}" />')
    
    svg_lines.append('</svg>')
    return '\n'.join(svg_lines)


def edges_to_plt(edges_image, min_area=20, epsilon_factor=0.005, target_width_mm=None, target_height_mm=None):
    """Converte bordas para PLT (HPGL) com escala real"""
    height_px, width_px = edges_image.shape
    
    if not target_width_mm: target_width_mm = width_px
    if not target_height_mm: target_height_mm = height_px
    
    # Unidade HPGL: 0.025mm por unidade (40 unidades = 1mm)
    hpgl_unit_per_mm = 40
    
    scale_x = (target_width_mm / width_px) * hpgl_unit_per_mm
    scale_y = (target_height_mm / height_px) * hpgl_unit_per_mm
    
    # Inverter Y para PLT (coordenadas cartesianas, origem canto inferior esquerdo)
    # Mas muitas lasers preferem origem superior, vamos seguir o padrão HPGL de Y invertido em relação a pixels
    max_y_hpgl = int(target_height_mm * hpgl_unit_per_mm)
    
    contours, _ = cv2.findContours(edges_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    hpgl = ["IN;", "SP1;"]
    
    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue
            
        epsilon = epsilon_factor * cv2.arcLength(contour, True)
        simplified = cv2.approxPolyDP(contour, epsilon, True)
        
        if len(simplified) < 2:
            continue
            
        for j, point in enumerate(simplified):
            x, y = point[0]
            x_hpgl = int(x * scale_x)
            y_hpgl = max_y_hpgl - int(y * scale_y) # Inverter Y
            
            cmd = "PU" if j == 0 else "PD"
            hpgl.append(f"{cmd}{x_hpgl},{y_hpgl};")
            
        hpgl.append("PU;") # Levantar caneta ao fim do contorno
        
    hpgl.append("SP0;") # Desselecionar caneta
    return "\n".join(hpgl)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_image():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Arquivo não selecionado'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Tipo de arquivo não permitido'}), 400
        
        filename = secure_filename(file.filename)
        timestamp = str(int(__import__('time').time() * 1000))
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extrair informações de escala
        info = get_image_info(filepath)
        
        # Gerar preview
        img = cv2.imread(filepath)
        preview_base64 = image_to_base64(img)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'preview': preview_base64,
            'info': info
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/detect-edges', methods=['POST'])
def detect_edges_endpoint():
    try:
        data = request.get_json()
        filename = data.get('filename')
        t1 = int(data.get('threshold1', 50))
        t2 = int(data.get('threshold2', 150))
        blur = int(data.get('blur', 5))
        morph = int(data.get('morph', 1))
        auto_threshold = data.get('auto_threshold', False)
        auto_contrast = data.get('auto_contrast', True)
        noise_removal = data.get('noise_removal', True)
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'Arquivo não encontrado'}), 404
        
        edges, _ = process_image(
            filepath, t1, t2, blur, morph,
            auto_threshold=auto_threshold,
            auto_contrast=auto_contrast,
            noise_removal=noise_removal
        )
        edges_base64 = image_to_base64(edges)
        
        return jsonify({
            'success': True,
            'edges': edges_base64,
            'width': edges.shape[1],
            'height': edges.shape[0]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/convert', methods=['POST'])
def convert_endpoint():
    """Endpoint unificado para conversão com escala"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        fmt = data.get('format', 'svg') # 'svg' ou 'plt'
        
        # Parâmetros de processamento
        t1 = int(data.get('threshold1', 50))
        t2 = int(data.get('threshold2', 150))
        blur = int(data.get('blur', 5))
        morph = int(data.get('morph', 1))
        min_area = float(data.get('min_area', 20))
        epsilon = float(data.get('epsilon', 0.005))
        auto_threshold = data.get('auto_threshold', False)
        auto_contrast = data.get('auto_contrast', True)
        noise_removal = data.get('noise_removal', True)
        
        # Parâmetros de escala
        target_w = float(data.get('width_mm'))
        target_h = float(data.get('height_mm'))
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        edges, _ = process_image(
            filepath, t1, t2, blur, morph,
            auto_threshold=auto_threshold,
            auto_contrast=auto_contrast,
            noise_removal=noise_removal
        )
        
        if fmt == 'svg':
            content = edges_to_svg(edges, min_area, epsilon, target_w, target_h)
            mimetype = 'image/svg+xml'
            ext = 'svg'
        else:
            content = edges_to_plt(edges, min_area, epsilon, target_w, target_h)
            mimetype = 'application/x-hpgl'
            ext = 'plt'
            
        return jsonify({
            'success': True,
            'content': content,
            'format': fmt,
            'filename': f"laser_cut_{int(__import__('time').time())}.{ext}"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download', methods=['POST'])
def download_file():
    try:
        data = request.get_json()
        content = data.get('content')
        filename = data.get('filename', 'output.svg')
        
        if not content:
            return jsonify({'error': 'Conteúdo não fornecido'}), 400
        
        return send_file(
            io.BytesIO(content.encode('utf-8')),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

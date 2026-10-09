import sys
import os
import webbrowser
import base64
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                               QComboBox, QCheckBox, QSpinBox, QMessageBox, 
                               QListWidget, QListWidgetItem, QProgressBar, QGroupBox, 
                               QSlider, QDialog)
from PySide6.QtGui import QPixmap, QIcon, QImage, QColor, QPen, QPainter, QCursor, QShortcut, QKeySequence, QGuiApplication
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtSvg import QSvgRenderer
from PIL import Image, ImageEnhance, ImageOps

# Registro dinámico de plugins de Pillow para HEIC y AVIF
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

try:
    import pillow_avif
except ImportError:
    pass

# Verificación segura de rembg
REMBG_INSTALADO = False
try:
    import importlib.util
    if importlib.util.find_spec("rembg") is not None:
        REMBG_INSTALADO = True
except Exception:
    REMBG_INSTALADO = False


EXTENSIONES_SOPORTADAS_CARGA = (
    '.png', '.jpg', '.jpeg', '.webp', '.avif', '.bmp', '.tiff', '.tif', 
    '.ico', '.icns', '.cur', '.svg', '.heic', '.heif', '.gif', '.tga', 
    '.dds', '.eps', '.pbm', '.pgm', '.ppm'
)


def es_modo_oscuro():
    """Detecta si el sistema operativo está configurado en modo oscuro."""
    palette = QGuiApplication.palette()
    bg_color = palette.color(palette.ColorRole.Window)
    return bg_color.lightness() < 128


def recolorear_icono_nitido(ruta_icono, color_hex):
    """Carga un ícono en su máxima resolución original y lo recolorea sin perder nitidez."""
    if not os.path.exists(ruta_icono):
        return QIcon()

    pixmap_original = QPixmap(ruta_icono)
    if pixmap_original.isNull():
        return QIcon()

    imagen_recoloreada = QImage(pixmap_original.size(), QImage.Format.Format_ARGB32)
    imagen_recoloreada.fill(Qt.GlobalColor.transparent)

    painter = QPainter(imagen_recoloreada)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    
    painter.drawPixmap(0, 0, pixmap_original)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(imagen_recoloreada.rect(), QColor(color_hex))
    painter.end()

    icon = QIcon()
    pixmap_final = QPixmap.fromImage(imagen_recoloreada)
    icon.addPixmap(pixmap_final, QIcon.Mode.Normal, QIcon.State.Off)
    return icon


def obtener_icono_desde_carpeta_icons(nombre_archivo, fuerza_color=None):
    """Busca y carga un ícono adecuando su color al tema activo, compatible con PyInstaller (_MEIPASS)."""
    if hasattr(sys, '_MEIPASS'):
        ruta_script = sys._MEIPASS
    else:
        ruta_script = os.path.dirname(os.path.abspath(__file__))

    ruta_final = os.path.join(ruta_script, "icons", nombre_archivo)

    if os.path.exists(ruta_final):
        if fuerza_color:
            return recolorear_icono_nitido(ruta_final, fuerza_color)
        
        color_target = "#FFFFFF" if es_modo_oscuro() else "#1C1C1C"
        return recolorear_icono_nitido(ruta_final, color_target)
        
    return QIcon()


def cargar_svg_a_pil(ruta_svg, tamano_render=1024):
    """Renderiza un archivo SVG vectorial a un PIL Image transparente en alta resolución."""
    renderer = QSvgRenderer(ruta_svg)
    if not renderer.isValid():
        raise ValueError("El archivo SVG no es válido.")

    qimg = QImage(tamano_render, tamano_render, QImage.Format.Format_ARGB32)
    qimg.fill(Qt.GlobalColor.transparent)

    painter = QPainter(qimg)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()

    bits = qimg.bits()
    img_pil = Image.frombuffer("RGBA", (tamano_render, tamano_render), bits, "raw", "BGRA", 0, 1)
    return img_pil.copy()


def remover_fondo_blanco_sencillo(img_rgba, umbral=235):
    """Convierte los píxeles predominantemente blancos o claros en transparentes."""
    img = img_rgba.copy()
    data = img.getdata()
    nuevos_pixeles = []
    for p in data:
        if p[0] >= umbral and p[1] >= umbral and p[2] >= umbral:
            nuevos_pixeles.append((255, 255, 255, 0))
        else:
            nuevos_pixeles.append(p)
    img.putdata(nuevos_pixeles)
    return img


def crear_icono_app(tamano=256):
    """Icono principal generado en memoria para la ventana."""
    imagen = QImage(tamano, tamano, QImage.Format.Format_ARGB32)
    imagen.fill(Qt.GlobalColor.transparent)

    painter = QPainter(imagen)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#0078D4"))
    margin = int(tamano * 0.05)
    diametro = tamano - (margin * 2)
    painter.drawEllipse(margin, margin, diametro, diametro)

    painter.setPen(QPen(QColor("#FFFFFF"), int(tamano * 0.08), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawLine(int(tamano * 0.32), int(tamano * 0.68), int(tamano * 0.62), int(tamano * 0.38))

    painter.setBrush(QColor("#FFFFFF"))
    painter.drawEllipse(int(tamano * 0.58), int(tamano * 0.26), int(tamano * 0.18), int(tamano * 0.18))
    
    painter.setBrush(QColor("#00E5FF"))
    painter.drawEllipse(int(tamano * 0.3), int(tamano * 0.3), int(tamano * 0.12), int(tamano * 0.12))

    painter.end()
    return QIcon(QPixmap.fromImage(imagen)), QPixmap.fromImage(imagen)


class DialogoAyuda(QDialog):
    """Ventana emergente que despliega el manual y guía de uso de IconForge."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guía de uso — IconForge")
        self.resize(540, 500)
        
        es_oscuro = es_modo_oscuro()
        bg_dialog = "#1A1A1A" if es_oscuro else "#F5F5F5"
        txt_dialog = "#FFFFFF" if es_oscuro else "#1A1A1A"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg_dialog}; }}
            QLabel {{ color: {txt_dialog}; font-family: 'Segoe UI', Arial; }}
            QPushButton {{ 
                background-color: #0078D4; color: white; border: none;
                border-radius: 6px; padding: 8px 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #106EBE; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        lbl_titulo = QLabel("Guía de Funciones — IconForge")
        lbl_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078D4;")
        layout.addWidget(lbl_titulo)

        sub_txt = "#CCCCCC" if es_oscuro else "#444444"
        lbl_contenido = QLabel()
        lbl_contenido.setWordWrap(True)
        lbl_contenido.setOpenExternalLinks(True)
        lbl_contenido.setText(f"""
        <p style='color: {txt_dialog}; font-size: 13px;'>
        Herramienta avanzada para la conversión, redimensionado y optimización de imágenes en lote.
        </p>

        <h4 style='color: #0078D4; margin-bottom: 2px;'>1. Carga y Selección</h4>
        <ul style='color: {sub_txt}; font-size: 12px; margin-top: 2px;'>
            <li><b>Soporte Estándar:</b> PNG, JPG, WEBP, AVIF, HEIC (iPhone), SVG, TIFF, BMP, ICO, ICNS, TGA, etc.</li>
            <li><b>Portapapeles:</b> Presiona Ctrl + V para pegar capturas de pantalla o imágenes.</li>
        </ul>

        <h4 style='color: #0078D4; margin-bottom: 2px;'>2. Transformaciones y Filtros</h4>
        <ul style='color: {sub_txt}; font-size: 12px; margin-top: 2px;'>
            <li><b>Rotación y Espejo:</b> Rotación libre de 90°/180° y volteo horizontal/vertical.</li>
            <li><b>Luz y Color:</b> Ajusta Brillo, Contraste y Saturación.</li>
        </ul>

        <h4 style='color: #0078D4; margin-bottom: 2px;'>3. Exportación y Presets</h4>
        <ul style='color: {sub_txt}; font-size: 12px; margin-top: 2px;'>
            <li><b>Sistemas Operativos:</b> Exporta a ICO (Windows) o ICNS (macOS).</li>
            <li><b>Web y Redes:</b> Formatos ligeros como WEBP, AVIF y presets para PWA o Favicon.</li>
        </ul>
        """)
        layout.addWidget(lbl_contenido)

        layout.addStretch()

        btn_cerrar = QPushButton("Entendido")
        btn_cerrar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar, alignment=Qt.AlignmentFlag.AlignRight)


class ProcesadorLoteWorker(QThread):
    progreso = Signal(int, int, str)
    finalizado = Signal(str)
    error = Signal(str)

    def __init__(self, lista_items_datos, carpeta_destino, formato, modo_fondo, mejorar_calidad, 
                 ancho, alto, ico_multicapa):
        super().__init__()
        self.lista_items_datos = lista_items_datos
        self.carpeta_destino = carpeta_destino
        self.formato = formato.upper()
        self.modo_fondo = modo_fondo
        self.mejorar_calidad = mejorar_calidad
        self.ancho = ancho
        self.alto = alto
        self.ico_multicapa = ico_multicapa

    def run(self):
        try:
            remove_func = None
            if self.modo_fondo == "Inteligente (IA rembg)":
                try:
                    from rembg import remove
                    remove_func = remove
                except Exception as ex:
                    print(f"Error cargando rembg: {ex}")

            total = len(self.lista_items_datos)
            for idx, item in enumerate(self.lista_items_datos, start=1):
                nombre = item['nombre']
                img_pil = item['img_pil']
                opciones_edicion = item['opciones']

                self.progreso.emit(idx, total, f"Procesando {idx}/{total}: {nombre}")

                img = img_pil.convert("RGBA")

                # Transformaciones
                rot = opciones_edicion.get('rotacion', 0)
                if rot != 0:
                    img = img.rotate(-rot, expand=True)

                if opciones_edicion.get('flip_h', False):
                    img = ImageOps.mirror(img)

                if opciones_edicion.get('flip_v', False):
                    img = ImageOps.flip(img)

                # Luz y Color
                factor_brillo = opciones_edicion.get('brillo', 1.0)
                if factor_brillo != 1.0:
                    img = ImageEnhance.Brightness(img).enhance(factor_brillo)

                factor_contraste = opciones_edicion.get('contraste', 1.0)
                if factor_contraste != 1.0:
                    img = ImageEnhance.Contrast(img).enhance(factor_contraste)

                factor_saturacion = opciones_edicion.get('saturacion', 1.0)
                if factor_saturacion != 1.0:
                    img = ImageEnhance.Color(img).enhance(factor_saturacion)

                # Tratamiento de Fondo
                if self.modo_fondo == "Blanco (Sencillo)":
                    img = remover_fondo_blanco_sencillo(img)
                elif self.modo_fondo == "Inteligente (IA rembg)" and remove_func:
                    img = remove_func(img)

                # Nitidez
                if self.mejorar_calidad:
                    enhancer_sharp = ImageEnhance.Sharpness(img)
                    img = enhancer_sharp.enhance(1.8)

                # Redimensionado
                try:
                    filtro_resampling = Image.Resampling.LANCZOS
                except AttributeError:
                    filtro_resampling = getattr(Image, 'LANCZOS', Image.BICUBIC)

                img_redimensionada = img.resize((self.ancho, self.alto), filtro_resampling)

                # Guardado
                nombre_base, _ = os.path.splitext(nombre)
                extension = self.formato.lower()
                ruta_salida = os.path.join(self.carpeta_destino, f"{nombre_base}_forge.{extension}")

                if self.formato == "ICO":
                    if self.ico_multicapa:
                        tamanos_ico = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
                    else:
                        tamanos_ico = [(self.ancho, self.alto)]
                    img.save(ruta_salida, format="ICO", sizes=tamanos_ico)

                elif self.formato == "ICNS":
                    img_redimensionada.save(ruta_salida, format="ICNS")

                elif self.formato in ["JPG", "JPEG", "PDF", "BMP"]:
                    fondo_blanco = Image.new("RGB", img_redimensionada.size, (255, 255, 255))
                    if img_redimensionada.mode == "RGBA":
                        fondo_blanco.paste(img_redimensionada, mask=img_redimensionada.split()[3])
                    else:
                        fondo_blanco.paste(img_redimensionada)

                    if self.formato in ["JPG", "JPEG"]:
                        fondo_blanco.save(ruta_salida, format="JPEG", quality=95)
                    elif self.formato == "PDF":
                        fondo_blanco.save(ruta_salida, format="PDF", resolution=100.0)
                    elif self.formato == "BMP":
                        fondo_blanco.save(ruta_salida, format="BMP")

                elif self.formato == "TIFF":
                    img_redimensionada.save(ruta_salida, format="TIFF", compression="tiff_lzw")

                elif self.formato == "WEBP":
                    img_redimensionada.save(ruta_salida, format="WEBP", quality=95)

                elif self.formato == "AVIF":
                    img_redimensionada.save(ruta_salida, format="AVIF", quality=90)

                elif self.formato == "TGA":
                    img_redimensionada.save(ruta_salida, format="TGA")

                else:
                    img_redimensionada.save(ruta_salida, format=self.formato)

            self.finalizado.emit(self.carpeta_destino)
        except Exception as e:
            self.error.emit(str(e))


class IconForgeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IconForge — Conversor Multiformato Profesional")
        self.resize(960, 720)
        self.lista_imagenes = []
        self.aspect_ratio_original = 1.0
        self.bloqueando_signals = False

        self.app_icon, self.icon_pixmap = crear_icono_app()
        self.setWindowIcon(self.app_icon)
        
        self.setAcceptDrops(True)
        self.inicializar_ui()
        self.configurar_shortcuts()

    def aplicar_tema(self):
        if es_modo_oscuro():
            self.setStyleSheet("""
                QMainWindow { background-color: #121212; }
                QWidget { background-color: #121212; color: #E0E0E0; }
                QLabel { color: #E0E0E0; font-family: 'Segoe UI', Arial; font-size: 12px; background: transparent; }
                QGroupBox {
                    color: #FFFFFF; font-weight: bold; border: 1px solid #333333;
                    border-radius: 6px; margin-top: 6px; padding-top: 10px; background-color: #181818;
                }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; background-color: #181818; }
                QPushButton { 
                    background-color: #1F1F1F; color: white; border: 1px solid #333333;
                    border-radius: 6px; padding: 8px 12px; font-weight: bold; font-size: 12px;
                }
                QPushButton:hover { background-color: #2D2D2D; border-color: #0078D4; }
                QPushButton:pressed { background-color: #111111; }
                QComboBox, QSpinBox {
                    background-color: #1F1F1F; color: white; border: 1px solid #333333;
                    border-radius: 4px; padding: 3px; min-width: 60px;
                }
                QCheckBox { color: #E0E0E0; font-size: 12px; background: transparent; }
                QListWidget {
                    background-color: #1A1A1A; color: #FFFFFF; border: 1px solid #333333;
                    border-radius: 6px; padding: 4px;
                }
                QProgressBar {
                    border: 1px solid #333333; border-radius: 4px; text-align: center; color: white;
                    background-color: #1A1A1A;
                }
                QProgressBar::chunk { background-color: #0078D4; width: 10px; }
                #ContenedorVista { 
                    background-color: #1A1A1A; border: 1px dashed #3A3A3A; border-radius: 8px; 
                }
                #HeaderTitulo { font-size: 18px; font-weight: bold; color: #FFFFFF; background: transparent; }
                #BtnCafe { background-color: transparent; border: none; color: #FFB900; font-weight: bold; }
                #BtnCafe:hover { color: #FFE066; text-decoration: underline; }
                
                #BtnIconoSolamente { padding: 4px; min-width: 36px; min-height: 36px; }
                #BtnNavegacion {
                    background-color: rgba(31, 31, 31, 0.8); border: 1px solid #444444;
                    border-radius: 15px; padding: 4px; min-width: 32px; min-height: 32px;
                }
                #BtnNavegacion:hover { background-color: #0078D4; border-color: #0078D4; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow { background-color: #F3F3F3; }
                QWidget { background-color: #F3F3F3; color: #1C1C1C; }
                QLabel { color: #1C1C1C; font-family: 'Segoe UI', Arial; font-size: 12px; background: transparent; }
                QGroupBox {
                    color: #000000; font-weight: bold; border: 1px solid #CCCCCC;
                    border-radius: 6px; margin-top: 6px; padding-top: 10px; background-color: #FFFFFF;
                }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; background-color: #FFFFFF; }
                QPushButton { 
                    background-color: #E1E1E1; color: #1C1C1C; border: 1px solid #CCCCCC;
                    border-radius: 6px; padding: 8px 12px; font-weight: bold; font-size: 12px;
                }
                QPushButton:hover { background-color: #D5D5D5; border-color: #0078D4; }
                QPushButton:pressed { background-color: #CCCCCC; }
                QComboBox, QSpinBox {
                    background-color: #FFFFFF; color: #1C1C1C; border: 1px solid #CCCCCC;
                    border-radius: 4px; padding: 3px; min-width: 60px;
                }
                QCheckBox { color: #1C1C1C; font-size: 12px; background: transparent; }
                QListWidget {
                    background-color: #FFFFFF; color: #1C1C1C; border: 1px solid #CCCCCC;
                    border-radius: 6px; padding: 4px;
                }
                QProgressBar {
                    border: 1px solid #CCCCCC; border-radius: 4px; text-align: center; color: black;
                    background-color: #E6E6E6;
                }
                QProgressBar::chunk { background-color: #0078D4; width: 10px; }
                #ContenedorVista { 
                    background-color: #FFFFFF; border: 1px dashed #B0B0B0; border-radius: 8px; 
                }
                #HeaderTitulo { font-size: 18px; font-weight: bold; color: #0078D4; background: transparent; }
                #BtnCafe { background-color: transparent; border: none; color: #D48800; font-weight: bold; }
                #BtnCafe:hover { color: #B37200; text-decoration: underline; }
                
                #BtnIconoSolamente { padding: 4px; min-width: 36px; min-height: 36px; }
                #BtnNavegacion {
                    background-color: rgba(230, 230, 230, 0.9); border: 1px solid #CCCCCC;
                    border-radius: 15px; padding: 4px; min-width: 32px; min-height: 32px;
                }
                #BtnNavegacion:hover { background-color: #0078D4; border-color: #0078D4; }
            """)

    def inicializar_ui(self):
        self.aplicar_tema()

        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        
        layout_raiz = QVBoxLayout(widget_central)
        layout_raiz.setContentsMargins(15, 15, 15, 10)
        layout_raiz.setSpacing(10)

        layout_contenido = QHBoxLayout()
        layout_contenido.setSpacing(15)

        # PANEL IZQUIERDO
        panel_izquierdo = QWidget()
        layout_izq = QVBoxLayout(panel_izquierdo)
        layout_izq.setContentsMargins(0, 0, 0, 0)

        self.area_vista = QWidget()
        self.area_vista.setObjectName("ContenedorVista")
        layout_vista_wrapper = QVBoxLayout(self.area_vista)
        
        layout_preview_nav = QHBoxLayout()
        
        self.btn_nav_anterior = QPushButton()
        self.btn_nav_anterior.setObjectName("BtnNavegacion")
        self.btn_nav_anterior.setIcon(obtener_icono_desde_carpeta_icons("anterior.ico"))
        self.btn_nav_anterior.setIconSize(QSize(20, 20))
        self.btn_nav_anterior.setToolTip("Imagen anterior")
        self.btn_nav_anterior.clicked.connect(self.imagen_anterior)
        
        self.lbl_preview = QLabel("Arrastra imágenes o carpetas aquí,\nusa los botones de la derecha\no presiona Ctrl + V para pegar")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet("color: #757575; font-size: 13px; background: transparent;")
        
        self.btn_nav_siguiente = QPushButton()
        self.btn_nav_siguiente.setObjectName("BtnNavegacion")
        self.btn_nav_siguiente.setIcon(obtener_icono_desde_carpeta_icons("siguiente.ico"))
        self.btn_nav_siguiente.setIconSize(QSize(20, 20))
        self.btn_nav_siguiente.setToolTip("Imagen siguiente")
        self.btn_nav_siguiente.clicked.connect(self.imagen_siguiente)

        layout_preview_nav.addWidget(self.btn_nav_anterior)
        layout_preview_nav.addWidget(self.lbl_preview, stretch=1)
        layout_preview_nav.addWidget(self.btn_nav_siguiente)

        layout_vista_wrapper.addLayout(layout_preview_nav)
        layout_izq.addWidget(self.area_vista, stretch=3)

        layout_izq.addWidget(QLabel("<b>Selecciona qué imágenes guardar (Checkbox):</b>"))
        self.lista_widget = QListWidget()
        self.lista_widget.itemClicked.connect(self.seleccionar_item_lista)
        layout_izq.addWidget(self.lista_widget, stretch=1)

        layout_gestion_lista = QHBoxLayout()
        
        self.btn_marcar_todo = QPushButton(" Todo")
        self.btn_marcar_todo.setIcon(obtener_icono_desde_carpeta_icons("marcar-todo.ico"))
        self.btn_marcar_todo.setToolTip("Marcar todas las imágenes para guardar")
        self.btn_marcar_todo.clicked.connect(lambda: self.cambiar_estado_todas_las_casillas(True))

        self.btn_desmarcar_todo = QPushButton(" Ninguno")
        self.btn_desmarcar_todo.setIcon(obtener_icono_desde_carpeta_icons("desmarcar-todo.ico"))
        self.btn_desmarcar_todo.setToolTip("Desmarcar todas las imágenes")
        self.btn_desmarcar_todo.clicked.connect(lambda: self.cambiar_estado_todas_las_casillas(False))

        self.btn_quitar_uno = QPushButton(" Quitar")
        self.btn_quitar_uno.setIcon(obtener_icono_desde_carpeta_icons("quitar.ico"))
        self.btn_quitar_uno.setToolTip("Elimina la imagen seleccionada de la lista")
        self.btn_quitar_uno.clicked.connect(self.eliminar_seleccionado)

        self.btn_limpiar = QPushButton(" Limpiar")
        self.btn_limpiar.setIcon(obtener_icono_desde_carpeta_icons("limpiar.ico"))
        self.btn_limpiar.setToolTip("Limpiar toda la lista")
        self.btn_limpiar.clicked.connect(self.limpiar_lista)
        
        layout_gestion_lista.addWidget(self.btn_marcar_todo)
        layout_gestion_lista.addWidget(self.btn_desmarcar_todo)
        layout_gestion_lista.addWidget(self.btn_quitar_uno)
        layout_gestion_lista.addWidget(self.btn_limpiar)
        layout_izq.addLayout(layout_gestion_lista)

        layout_contenido.addWidget(panel_izquierdo, stretch=3)

        # PANEL DERECHO
        panel_controles = QWidget()
        layout_controles = QVBoxLayout(panel_controles)
        layout_controles.setSpacing(8)
        layout_controles.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header
        layout_header = QHBoxLayout()
        lbl_logo_ui = QLabel()
        lbl_logo_ui.setPixmap(self.icon_pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        lbl_titulo = QLabel("IconForge")
        lbl_titulo.setObjectName("HeaderTitulo")
        
        layout_header.addWidget(lbl_logo_ui)
        layout_header.addWidget(lbl_titulo)
        layout_header.addStretch()
        layout_controles.addLayout(layout_header)

        # Cargar
        layout_botones_cargar = QHBoxLayout()
        self.btn_cargar = QPushButton(" Archivos")
        self.btn_cargar.setIcon(obtener_icono_desde_carpeta_icons("archivo.ico"))
        self.btn_cargar.clicked.connect(self.abrir_imagenes)
        
        self.btn_carpeta = QPushButton(" Carpeta")
        self.btn_carpeta.setIcon(obtener_icono_desde_carpeta_icons("carpeta.ico"))
        self.btn_carpeta.clicked.connect(self.abrir_carpeta)

        self.btn_pegar = QPushButton(" Pegar")
        self.btn_pegar.setIcon(obtener_icono_desde_carpeta_icons("pegar.ico"))
        self.btn_pegar.clicked.connect(self.pegar_desde_portapapeles)
        
        layout_botones_cargar.addWidget(self.btn_cargar)
        layout_botones_cargar.addWidget(self.btn_carpeta)
        layout_botones_cargar.addWidget(self.btn_pegar)
        layout_controles.addLayout(layout_botones_cargar)

        # Edición
        grp_edicion = QGroupBox("Rotación y Ajustes")
        layout_edicion = QVBoxLayout(grp_edicion)
        
        layout_transform = QHBoxLayout()
        
        self.btn_gira_derecha = QPushButton()
        self.btn_gira_derecha.setObjectName("BtnIconoSolamente")
        self.btn_gira_derecha.setIcon(obtener_icono_desde_carpeta_icons("gira-a-la-derecha.ico"))
        self.btn_gira_derecha.setIconSize(QSize(28, 28))
        self.btn_gira_derecha.setToolTip("Girar a la derecha")
        self.btn_gira_derecha.clicked.connect(self.gira_a_la_derecha)
        
        self.btn_gira_izquierda = QPushButton()
        self.btn_gira_izquierda.setObjectName("BtnIconoSolamente")
        self.btn_gira_izquierda.setIcon(obtener_icono_desde_carpeta_icons("girar-a-la-izquierda.ico"))
        self.btn_gira_izquierda.setIconSize(QSize(28, 28))
        self.btn_gira_izquierda.setToolTip("Girar a la izquierda")
        self.btn_gira_izquierda.clicked.connect(self.gira_a_la_izquierda)
        
        self.btn_rotar_180 = QPushButton()
        self.btn_rotar_180.setObjectName("BtnIconoSolamente")
        self.btn_rotar_180.setIcon(obtener_icono_desde_carpeta_icons("Rotar.ico"))
        self.btn_rotar_180.setIconSize(QSize(28, 28))
        self.btn_rotar_180.setToolTip("Girar 180°")
        self.btn_rotar_180.clicked.connect(self.gira_180)

        self.btn_flip_h = QPushButton()
        self.btn_flip_h.setObjectName("BtnIconoSolamente")
        self.btn_flip_h.setIcon(obtener_icono_desde_carpeta_icons("volteo-horizontal.ico"))
        self.btn_flip_h.setIconSize(QSize(28, 28))
        self.btn_flip_h.setToolTip("Volteo Horizontal")
        self.btn_flip_h.clicked.connect(self.toggle_flip_h)

        self.btn_flip_v = QPushButton()
        self.btn_flip_v.setObjectName("BtnIconoSolamente")
        self.btn_flip_v.setIcon(obtener_icono_desde_carpeta_icons("volteo-vertical.ico"))
        self.btn_flip_v.setIconSize(QSize(28, 28))
        self.btn_flip_v.setToolTip("Volteo Vertical")
        self.btn_flip_v.clicked.connect(self.toggle_flip_v)

        layout_transform.addWidget(self.btn_gira_derecha)
        layout_transform.addWidget(self.btn_gira_izquierda)
        layout_transform.addWidget(self.btn_rotar_180)
        layout_transform.addWidget(self.btn_flip_h)
        layout_transform.addWidget(self.btn_flip_v)
        layout_edicion.addLayout(layout_transform)

        layout_sliders = QVBoxLayout()
        
        l_brillo = QHBoxLayout()
        l_brillo.addWidget(QLabel("Brillo:"))
        self.slider_brillo = QSlider(Qt.Orientation.Horizontal)
        self.slider_brillo.setRange(50, 150)
        self.slider_brillo.setValue(100)
        self.slider_brillo.valueChanged.connect(self.on_slider_modificado)
        l_brillo.addWidget(self.slider_brillo)
        layout_sliders.addLayout(l_brillo)

        l_contraste = QHBoxLayout()
        l_contraste.addWidget(QLabel("Contraste:"))
        self.slider_contraste = QSlider(Qt.Orientation.Horizontal)
        self.slider_contraste.setRange(50, 150)
        self.slider_contraste.setValue(100)
        self.slider_contraste.valueChanged.connect(self.on_slider_modificado)
        l_contraste.addWidget(self.slider_contraste)
        layout_sliders.addLayout(l_contraste)

        l_saturacion = QHBoxLayout()
        l_saturacion.addWidget(QLabel("Saturación:"))
        self.slider_saturacion = QSlider(Qt.Orientation.Horizontal)
        self.slider_saturacion.setRange(0, 200)
        self.slider_saturacion.setValue(100)
        self.slider_saturacion.valueChanged.connect(self.on_slider_modificado)
        l_saturacion.addWidget(self.slider_saturacion)
        layout_sliders.addLayout(l_saturacion)

        layout_edicion.addLayout(layout_sliders)

        self.btn_restablecer_ajustes = QPushButton(" Restablecer Ajustes")
        self.btn_restablecer_ajustes.setToolTip("Devuelve rotación, brillo, contraste y saturación a sus valores iniciales")
        self.btn_restablecer_ajustes.clicked.connect(self.restablecer_ajustes)
        layout_edicion.addWidget(self.btn_restablecer_ajustes)

        layout_controles.addWidget(grp_edicion)

        # Formatos
        grp_formato = QGroupBox("Formato y Fondo")
        layout_formato = QVBoxLayout(grp_formato)

        l_fmt = QHBoxLayout()
        l_fmt.addWidget(QLabel("Formato:"))
        self.combo_formato = QComboBox()
        self.combo_formato.addItems(["PNG", "ICO", "WEBP", "AVIF", "JPG", "PDF", "ICNS", "TIFF", "BMP", "TGA"])
        self.combo_formato.currentTextChanged.connect(self.on_formato_changed)
        l_fmt.addWidget(self.combo_formato)
        layout_formato.addLayout(l_fmt)

        self.chk_ico_multicapa = QCheckBox("ICO Multi-tamaño (16px a 256px embebidos)")
        self.chk_ico_multicapa.setChecked(True)
        self.chk_ico_multicapa.setVisible(False)
        layout_formato.addWidget(self.chk_ico_multicapa)

        l_fnd = QHBoxLayout()
        l_fnd.addWidget(QLabel("Fondo:"))
        self.combo_fondo = QComboBox()
        opciones_fondo = ["Ninguno", "Blanco (Sencillo)"]
        if REMBG_INSTALADO:
            opciones_fondo.append("Inteligente (IA rembg)")
        else:
            opciones_fondo.append("IA rembg (No detectada)")
        self.combo_fondo.addItems(opciones_fondo)
        self.combo_fondo.currentTextChanged.connect(self.on_fondo_changed)
        l_fnd.addWidget(self.combo_fondo)
        layout_formato.addLayout(l_fnd)

        self.chk_calidad = QCheckBox("Mejorar nitidez")
        self.chk_calidad.setChecked(True)
        layout_formato.addWidget(self.chk_calidad)

        layout_controles.addWidget(grp_formato)

        # Dimensiones / Presets DEV
        grp_dimensiones = QGroupBox("Tamaño de Salida (Presets DEV)")
        layout_dim_box = QVBoxLayout(grp_dimensiones)

        self.combo_presets = QComboBox()
        self.combo_presets.addItems([
            "Personalizado",
            "Favicon web (16x16)",
            "Favicon HD (32x32)",
            "App Escritorio (64x64)",
            "Apple Touch Icon (180x180)",
            "Android PWA Standard (192x192)",
            "Alta resolución (256x256)",
            "Store/PWA Large (512x512)",
            "Social Open Graph (1200x630)"
        ])
        self.combo_presets.currentIndexChanged.connect(self.aplicar_preset_tamano)
        layout_dim_box.addWidget(self.combo_presets)

        layout_dimensiones = QHBoxLayout()
        self.spin_ancho = QSpinBox()
        self.spin_ancho.setRange(1, 8192)
        self.spin_ancho.setValue(512)
        self.spin_ancho.valueChanged.connect(self.on_ancho_cambiado)

        self.spin_alto = QSpinBox()
        self.spin_alto.setRange(1, 8192)
        self.spin_alto.setValue(512)
        self.spin_alto.valueChanged.connect(self.on_alto_cambiado)

        self.chk_bloquear_aspecto = QCheckBox("🔒 Proporción")
        self.chk_bloquear_aspecto.setChecked(True)

        layout_dimensiones.addWidget(QLabel("A:"))
        layout_dimensiones.addWidget(self.spin_ancho)
        layout_dimensiones.addWidget(QLabel("H:"))
        layout_dimensiones.addWidget(self.spin_alto)
        layout_dimensiones.addWidget(self.chk_bloquear_aspecto)
        layout_dim_box.addLayout(layout_dimensiones)

        layout_controles.addWidget(grp_dimensiones)

        # Progreso y Procesar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout_controles.addWidget(self.progress_bar)

        self.lbl_estado = QLabel("")
        self.lbl_estado.setStyleSheet("color: #00E5FF; font-size: 11px;")
        layout_controles.addWidget(self.lbl_estado)

        self.btn_procesar = QPushButton(" Guardar Marcadas / Procesar Lote")
        self.btn_procesar.setIcon(obtener_icono_desde_carpeta_icons("guardar.ico", fuerza_color="#FFFFFF"))
        self.btn_procesar.setIconSize(QSize(20, 20))
        self.btn_procesar.setStyleSheet("""
            QPushButton { background-color: #0078D4; color: white; border: none; font-size: 14px; padding: 10px; }
            QPushButton:hover { background-color: #106EBE; }
        """)
        self.btn_procesar.clicked.connect(self.procesar_imagenes)
        layout_controles.addWidget(self.btn_procesar)

        layout_contenido.addWidget(panel_controles, stretch=2)
        layout_raiz.addLayout(layout_contenido)

        # Footer
        layout_footer = QHBoxLayout()
        
        self.btn_ayuda = QPushButton(" ¿Cómo funciona?")
        self.btn_ayuda.setIcon(obtener_icono_desde_carpeta_icons("ayuda.ico"))
        self.btn_ayuda.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_ayuda.setStyleSheet("""
            QPushButton { 
                background-color: transparent; border: none; color: #888888; font-weight: bold; 
            }
            QPushButton:hover { color: #0078D4; text-decoration: underline; }
        """)
        self.btn_ayuda.clicked.connect(self.mostrar_ayuda)
        layout_footer.addWidget(self.btn_ayuda)

        layout_footer.addStretch()

        self.btn_cafe = QPushButton(" ¡Invítame un café!")
        self.btn_cafe.setIcon(obtener_icono_desde_carpeta_icons("cafe.ico", fuerza_color="#FFB900"))
        self.btn_cafe.setObjectName("BtnCafe")
        self.btn_cafe.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_cafe.clicked.connect(self.abrir_paypal)
        layout_footer.addWidget(self.btn_cafe)

        layout_raiz.addLayout(layout_footer)

    def configurar_shortcuts(self):
        self.shortcut_pegar = QShortcut(QKeySequence("Ctrl+V"), self)
        self.shortcut_pegar.activated.connect(self.pegar_desde_portapapeles)

        self.shortcut_supr = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        self.shortcut_supr.activated.connect(self.eliminar_seleccionado)

    def mostrar_ayuda(self):
        dialogo = DialogoAyuda(self)
        dialogo.exec()

    def abrir_paypal(self):
        url_cifrada = "aHR0cHM6Ly93d3cucGF5cGFsLm1lL0RldlNhbHZhZG9y"
        url_destinos = base64.b64decode(url_cifrada).decode('utf-8')
        webbrowser.open(url_destinos)

    def on_formato_changed(self, texto):
        self.chk_ico_multicapa.setVisible(texto.upper() == "ICO")

    def on_fondo_changed(self, texto):
        row = self.lista_widget.currentRow()
        if row >= 0:
            self.actualizar_vista(row)

    # NAVEGACIÓN Y TRANSFORMACIONES
    def imagen_anterior(self):
        if not self.lista_imagenes:
            return
        row = self.lista_widget.currentRow()
        nueva_fila = (row - 1) % len(self.lista_imagenes) if row >= 0 else len(self.lista_imagenes) - 1
        self.lista_widget.setCurrentRow(nueva_fila)
        self.actualizar_vista(nueva_fila)

    def imagen_siguiente(self):
        if not self.lista_imagenes:
            return
        row = self.lista_widget.currentRow()
        nueva_fila = (row + 1) % len(self.lista_imagenes) if row >= 0 else 0
        self.lista_widget.setCurrentRow(nueva_fila)
        self.actualizar_vista(nueva_fila)

    def gira_a_la_derecha(self):
        row = self.lista_widget.currentRow()
        if 0 <= row < len(self.lista_imagenes):
            item = self.lista_imagenes[row]
            item['rotacion'] = (item['rotacion'] + 90) % 360
            self.actualizar_vista(row)

    def gira_a_la_izquierda(self):
        row = self.lista_widget.currentRow()
        if 0 <= row < len(self.lista_imagenes):
            item = self.lista_imagenes[row]
            item['rotacion'] = (item['rotacion'] - 90) % 360
            self.actualizar_vista(row)

    def gira_180(self):
        row = self.lista_widget.currentRow()
        if 0 <= row < len(self.lista_imagenes):
            item = self.lista_imagenes[row]
            item['rotacion'] = (item['rotacion'] + 180) % 360
            self.actualizar_vista(row)

    def toggle_flip_h(self):
        row = self.lista_widget.currentRow()
        if 0 <= row < len(self.lista_imagenes):
            item = self.lista_imagenes[row]
            item['flip_h'] = not item.get('flip_h', False)
            self.actualizar_vista(row)

    def toggle_flip_v(self):
        row = self.lista_widget.currentRow()
        if 0 <= row < len(self.lista_imagenes):
            item = self.lista_imagenes[row]
            item['flip_v'] = not item.get('flip_v', False)
            self.actualizar_vista(row)

    def restablecer_ajustes(self):
        row = self.lista_widget.currentRow()
        if 0 <= row < len(self.lista_imagenes):
            item = self.lista_imagenes[row]
            item['rotacion'] = 0
            item['flip_h'] = False
            item['flip_v'] = False
            item['brillo'] = 100
            item['contraste'] = 100
            item['saturacion'] = 100
            self.actualizar_vista(row)

    def on_slider_modificado(self):
        row = self.lista_widget.currentRow()
        if 0 <= row < len(self.lista_imagenes) and not self.bloqueando_signals:
            item = self.lista_imagenes[row]
            item['brillo'] = self.slider_brillo.value()
            item['contraste'] = self.slider_contraste.value()
            item['saturacion'] = self.slider_saturacion.value()
            self.actualizar_vista(row)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return

        self.limpiar_lista()

        for url in urls:
            ruta = url.toLocalFile()
            if os.path.isdir(ruta):
                self.cargar_carpeta_ruta(ruta, reemplazando=False)
            elif ruta.lower().endswith(EXTENSIONES_SOPORTADAS_CARGA):
                self.agregar_imagen_por_ruta(ruta)

    def abrir_imagenes(self):
        filtro_extensiones = "Imágenes (" + " ".join([f"*{ext}" for ext in EXTENSIONES_SOPORTADAS_CARGA]) + ")"
        rutas, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar Imágenes", "", filtro_extensiones
        )
        if rutas:
            self.limpiar_lista()
            for ruta in rutas:
                self.agregar_imagen_por_ruta(ruta)

    def abrir_carpeta(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta con Imágenes")
        if carpeta:
            self.cargar_carpeta_ruta(carpeta, reemplazando=True)

    def cargar_carpeta_ruta(self, carpeta, reemplazando=True):
        if reemplazando:
            self.limpiar_lista()

        archivos = [os.path.join(carpeta, f) for f in os.listdir(carpeta) if f.lower().endswith(EXTENSIONES_SOPORTADAS_CARGA)]
        for ruta in archivos:
            self.agregar_imagen_por_ruta(ruta)

    def agregar_imagen_por_ruta(self, ruta):
        try:
            nombre = os.path.basename(ruta)
            
            if ruta.lower().endswith('.svg'):
                img_pil = cargar_svg_a_pil(ruta, tamano_render=1024)
            else:
                img_pil = Image.open(ruta)

            img_temp_rgba = img_pil.copy().convert("RGBA")
            data = img_temp_rgba.tobytes("raw", "RGBA")
            qimg = QImage(data, img_temp_rgba.width, img_temp_rgba.height, QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimg)
            
            item_data = {
                'nombre': nombre,
                'img_pil': img_pil,
                'pixmap': pixmap,
                'rotacion': 0,
                'flip_h': False,
                'flip_v': False,
                'brillo': 100,
                'contraste': 100,
                'saturacion': 100
            }
            
            self.lista_imagenes.append(item_data)
            
            list_item = QListWidgetItem(nombre)
            list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            list_item.setCheckState(Qt.CheckState.Checked)
            self.lista_widget.addItem(list_item)

            if len(self.lista_imagenes) == 1:
                self.lista_widget.setCurrentRow(0)
                self.actualizar_vista(0)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar {ruta}:\n{str(e)}")

    def pegar_desde_portapapeles(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            qimage = clipboard.image()
            if not qimage.isNull():
                buffer = qimage.bits()
                img_pil = Image.frombuffer("RGBA", (qimage.width(), qimage.height()), buffer, "raw", "BGRA", 0, 1)
                pixmap = QPixmap.fromImage(qimage)
                
                self.limpiar_lista()
                
                nombre = "captura_portapapeles.png"
                item_data = {
                    'nombre': nombre,
                    'img_pil': img_pil,
                    'pixmap': pixmap,
                    'rotacion': 0,
                    'flip_h': False,
                    'flip_v': False,
                    'brillo': 100,
                    'contraste': 100,
                    'saturacion': 100
                }
                
                self.lista_imagenes.append(item_data)
                
                list_item = QListWidgetItem(nombre)
                list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                list_item.setCheckState(Qt.CheckState.Checked)
                self.lista_widget.addItem(list_item)
                
                self.lista_widget.setCurrentRow(0)
                self.actualizar_vista(0)
        else:
            QMessageBox.information(self, "Portapapeles", "No se encontró ninguna imagen en el portapapeles.")

    def cambiar_estado_todas_las_casillas(self, marcar):
        estado = Qt.CheckState.Checked if marcar else Qt.CheckState.Unchecked
        for idx in range(self.lista_widget.count()):
            item = self.lista_widget.item(idx)
            item.setCheckState(estado)

    def eliminar_seleccionado(self):
        row = self.lista_widget.currentRow()
        if 0 <= row < len(self.lista_imagenes):
            self.lista_imagenes.pop(row)
            self.lista_widget.takeItem(row)
            if not self.lista_imagenes:
                self.limpiar_lista()
            else:
                nueva_fila = min(row, len(self.lista_imagenes) - 1)
                self.lista_widget.setCurrentRow(nueva_fila)
                self.actualizar_vista(nueva_fila)

    def limpiar_lista(self):
        self.lista_imagenes.clear()
        self.lista_widget.clear()
        self.lbl_preview.setPixmap(QPixmap())
        self.lbl_preview.setText("Arrastra imágenes o carpetas aquí,\nusa los botones de la derecha\no presiona Ctrl + V para pegar")

    def seleccionar_item_lista(self, item):
        row = self.lista_widget.row(item)
        self.actualizar_vista(row)

    def actualizar_vista(self, indice):
        if 0 <= indice < len(self.lista_imagenes):
            item = self.lista_imagenes[indice]
            
            ancho = item['pixmap'].width()
            alto = item['pixmap'].height()
            self.aspect_ratio_original = ancho / alto if alto > 0 else 1.0

            self.bloqueando_signals = True
            self.slider_brillo.setValue(item['brillo'])
            self.slider_contraste.setValue(item['contraste'])
            self.slider_saturacion.setValue(item['saturacion'])

            if self.combo_presets.currentIndex() == 0:
                self.spin_ancho.setValue(ancho)
                self.spin_alto.setValue(alto)
            self.bloqueando_signals = False

            img_temp = item['img_pil'].copy().convert("RGBA")

            if item.get('rotacion', 0) != 0:
                img_temp = img_temp.rotate(-item['rotacion'], expand=True)
            if item.get('flip_h', False):
                img_temp = ImageOps.mirror(img_temp)
            if item.get('flip_v', False):
                img_temp = ImageOps.flip(img_temp)

            f_brillo = item['brillo'] / 100.0
            f_contraste = item['contraste'] / 100.0
            f_sat = item['saturacion'] / 100.0

            if f_brillo != 1.0:
                img_temp = ImageEnhance.Brightness(img_temp).enhance(f_brillo)
            if f_contraste != 1.0:
                img_temp = ImageEnhance.Contrast(img_temp).enhance(f_contraste)
            if f_sat != 1.0:
                img_temp = ImageEnhance.Color(img_temp).enhance(f_sat)

            modo_fondo = self.combo_fondo.currentText()
            if modo_fondo == "Blanco (Sencillo)":
                img_temp = remover_fondo_blanco_sencillo(img_temp)
            elif modo_fondo == "Inteligente (IA rembg)" and REMBG_INSTALADO:
                try:
                    from rembg import remove
                    img_temp = remove(img_temp)
                except Exception:
                    pass

            data = img_temp.tobytes("raw", "RGBA")
            qimg = QImage(data, img_temp.width, img_temp.height, QImage.Format.Format_RGBA8888)
            pixmap_trans = QPixmap.fromImage(qimg)

            pixmap_escalado = pixmap_trans.scaled(320, 320, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_preview.setPixmap(pixmap_escalado)
            self.lbl_preview.setStyleSheet("background: transparent;")

    def on_ancho_cambiado(self, nuevo_ancho):
        if self.bloqueando_signals:
            return
        if self.chk_bloquear_aspecto.isChecked() and self.aspect_ratio_original > 0:
            self.bloqueando_signals = True
            nuevo_alto = max(1, int(nuevo_ancho / self.aspect_ratio_original))
            self.spin_alto.setValue(nuevo_alto)
            self.bloqueando_signals = False

    def on_alto_cambiado(self, nuevo_alto):
        if self.bloqueando_signals:
            return
        if self.chk_bloquear_aspecto.isChecked() and self.aspect_ratio_original > 0:
            self.bloqueando_signals = True
            nuevo_ancho = max(1, int(nuevo_alto * self.aspect_ratio_original))
            self.spin_ancho.setValue(nuevo_ancho)
            self.bloqueando_signals = False

    def aplicar_preset_tamano(self, indice):
        presets = {
            1: (16, 16),
            2: (32, 32),
            3: (64, 64),
            4: (180, 180),
            5: (192, 192),
            6: (256, 256),
            7: (512, 512),
            8: (1200, 630)
        }
        if indice in presets:
            ancho, alto = presets[indice]
            self.chk_bloquear_aspecto.setChecked(False)
            self.spin_ancho.setValue(ancho)
            self.spin_alto.setValue(alto)
            self.spin_ancho.setEnabled(False)
            self.spin_alto.setEnabled(False)
        else:
            self.chk_bloquear_aspecto.setChecked(True)
            self.spin_ancho.setEnabled(True)
            self.spin_alto.setEnabled(True)

    def procesar_imagenes(self):
        if not self.lista_imagenes:
            QMessageBox.warning(self, "Sin imágenes", "Añade al menos una imagen antes de procesar.")
            return

        lista_items_datos = []
        for idx, item in enumerate(self.lista_imagenes):
            widget_item = self.lista_widget.item(idx)
            if widget_item and widget_item.checkState() == Qt.CheckState.Checked:
                lista_items_datos.append({
                    'nombre': item['nombre'],
                    'img_pil': item['img_pil'],
                    'opciones': {
                        'rotacion': item['rotacion'],
                        'flip_h': item.get('flip_h', False),
                        'flip_v': item.get('flip_v', False),
                        'brillo': item['brillo'] / 100.0,
                        'contraste': item['contraste'] / 100.0,
                        'saturacion': item['saturacion'] / 100.0
                    }
                })

        if not lista_items_datos:
            QMessageBox.warning(self, "Sin selección", "No has marcado ninguna imagen para guardar.\nUsa las casillas (check) para seleccionar cuáles deseas procesar.")
            return

        modo_fondo = self.combo_fondo.currentText()
        if "No detectada" in modo_fondo:
            QMessageBox.warning(self, "IA no disponible", "La función rembg de IA no está disponible en este entorno de Python.\n\nPuedes usar las opciones de fondo transparente o blanco sencillo.")
            return

        carpeta_destino = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta para guardar resultados")
        if not carpeta_destino:
            return

        self.btn_procesar.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.worker = ProcesadorLoteWorker(
            lista_items_datos=lista_items_datos,
            carpeta_destino=carpeta_destino,
            formato=self.combo_formato.currentText(),
            modo_fondo=modo_fondo,
            mejorar_calidad=self.chk_calidad.isChecked(),
            ancho=self.spin_ancho.value(),
            alto=self.spin_alto.value(),
            ico_multicapa=self.chk_ico_multicapa.isChecked()
        )
        self.worker.progreso.connect(self.on_progreso_lote)
        self.worker.finalizado.connect(self.on_lote_finalizado)
        self.worker.error.connect(self.on_lote_error)
        self.worker.start()

    def on_progreso_lote(self, actual, total, mensaje):
        porcentaje = int((actual / total) * 100)
        self.progress_bar.setValue(porcentaje)
        self.lbl_estado.setText(mensaje)

    def on_lote_finalizado(self, carpeta):
        self.btn_procesar.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_estado.setText("")
        QMessageBox.information(self, "¡Proceso Completado!", f"Se procesaron los archivos seleccionados en:\n{carpeta}")

    def on_lote_error(self, error_msg):
        self.btn_procesar.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_estado.setText("")
        QMessageBox.critical(self, "Error", f"Ocurrió un problema durante el procesamiento:\n{error_msg}")

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        ex = IconForgeApp()
        ex.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error al iniciar la app: {e}")
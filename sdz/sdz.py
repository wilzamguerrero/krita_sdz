from krita import Extension, Krita, InfoObject, Selection
from PyQt5.QtWidgets import QMessageBox, QMenu
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QRect

class SDZPasteExtension(Extension):

    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        # Crear el menú principal "SDZ Paste"
        main_action = window.createAction("sdz", "SDZ", "tools/scripts")
        
        # Crear un QMenu para contener las acciones
        menu = QMenu("SDZ", window.qwindow())
        main_action.setMenu(menu)

        # Crear las acciones y añadirlas al menú
        actions = [
        
            ("sdz_find_selection", "find_selection", self.find_selection),
            ("sdz_trim_canvas", "trim_canvas", self.trim_canvas),
            ("sdz_512x512v", "512x512v", self.create_512x512v),
            ("sdz_512x512", "512x512", self.create_512x512),
            ("sdz_512x768v", "512x768v", self.create_512x768v),
            ("sdz_512x768", "512x768", self.create_512x768),
            ("sdz_768x512", "768x512", self.create_768x512),
            ("sdz_paste_and_align", "Paste and Align", self.paste_and_align),
            ("sdz_create_fill_layer", "Create Fill Layer from Selection", self.create_fill_layer_from_selection),
            ("sdz_align_image", "Align Image", self.align_image)
            
        ]

        for action_id, action_text, action_function in actions:
            action = window.createAction(action_id, action_text, "")  # Categoría vacía
            action.triggered.connect(action_function)
            menu.addAction(action)

    def paste_and_align(self):
        krita_instance = Krita.instance()
        doc = krita_instance.activeDocument()

        if not doc or not doc.selection():
            QMessageBox.warning(None, "Error", "No existe una selección creada.")
            return

        color_info = InfoObject()
        color_info.setProperty("color", QColor(0, 239, 250))

        selection = doc.selection()

        fill_layer = doc.createFillLayer("tempselection", "color", color_info, selection)
        doc.rootNode().addChildNode(fill_layer, None)

        doc.refreshProjection()

        initial_layers = doc.topLevelNodes()

        krita_instance.action('edit_paste').trigger()

        krita_instance.activeDocument().waitForDone()

        new_layers = doc.topLevelNodes()

        new_layer = None
        for layer in new_layers:
            if layer not in initial_layers:
                new_layer = layer
                break

        if new_layer:
            new_name = self.get_next_available_name(doc, "tempimage")
            new_layer.setName(new_name)
        else:
            QMessageBox.warning(None, "Error", "No se pudo identificar la capa pegada")
            return

        active_layer = new_layer
        if active_layer is None:
            QMessageBox.warning(None, "Error", f"No se encontró la capa '{new_name}'")
            return

        layer_bounds = active_layer.bounds()
        layer_pos = active_layer.position()

        x_offset = layer_pos.x() - layer_bounds.x()
        y_offset = layer_pos.y() - layer_bounds.y()

        active_layer.move(x_offset, y_offset)

        doc.refreshProjection()

        tempimage_layer = active_layer
        tempselection_layer = doc.nodeByName("tempselection")

        if tempimage_layer is None or tempselection_layer is None:
            QMessageBox.warning(None, "Error", f"No se encontraron las capas '{new_name}' o 'tempselection'")
            return

        tempselection_bounds = tempselection_layer.bounds()
        tempimage_bounds = tempimage_layer.bounds()

        new_layer = doc.createNode(f"{new_name}_new", "paintlayer")
        doc.rootNode().addChildNode(new_layer, tempimage_layer)

        tempimage_data = tempimage_layer.pixelData(0,0, tempimage_bounds.width(), tempimage_bounds.height())

        scale_x = tempselection_bounds.width() / tempimage_bounds.width()
        scale_y = tempselection_bounds.height() / tempimage_bounds.height()

        for y in range(tempselection_bounds.height()):
            for x in range(tempselection_bounds.width()):
                src_x = int(x / scale_x)
                src_y = int(y / scale_y)
                if src_x < tempimage_bounds.width() and src_y < tempimage_bounds.height():
                    pixel_index = (src_y * tempimage_bounds.width() + src_x) * 4
                    pixel_data = tempimage_data[pixel_index:pixel_index+4]
                    new_layer.setPixelData(pixel_data, x, y, 1, 1)

        new_layer.move(tempselection_bounds.x(), tempselection_bounds.y())

        doc.rootNode().removeChildNode(tempimage_layer)

        new_layer.setName(new_name)

        doc.rootNode().removeChildNode(tempselection_layer)
        Krita.instance().activeDocument().setSelection(None)
        doc.refreshProjection()


    def create_fill_layer_from_selection(self):
        krita = Krita.instance()
        doc = krita.activeDocument()
        if not doc or not doc.selection():
            QMessageBox.warning(None, "Error", "No existe una selección creada.")
            return
        
        color_info = InfoObject()
        color_info.setProperty("color", QColor(0, 239, 250))  # Color cian
        selection = doc.selection()
        fill_layer = doc.createFillLayer("tempselectionb", "color", color_info, selection)
        fill_layer.setOpacity(127)
        doc.rootNode().addChildNode(fill_layer, None)
        Krita.instance().activeDocument().setSelection(None)
        doc.refreshProjection()
        

    def align_image(self):
        self.align_layer_top_left()
        self.adjust_selected_to_tempselection()
        

    def align_layer_top_left(self):
        doc = Krita.instance().activeDocument()
        if doc is None:
            QMessageBox.warning(None, "Error", "No hay un documento activo")
            return

        active_layer = doc.activeNode()
        if active_layer is None:
            QMessageBox.warning(None, "Error", "No hay una capa seleccionada")
            return

        layer_bounds = active_layer.bounds()
        layer_pos = active_layer.position()

        x_offset = layer_pos.x() - layer_bounds.x()
        y_offset = layer_pos.y() - layer_bounds.y()

        active_layer.move(x_offset, y_offset)
        doc.refreshProjection()

    def adjust_selected_to_tempselection(self):
        doc = Krita.instance().activeDocument()
        if doc is None:
            QMessageBox.warning(None, "Error", "No hay un documento activo")
            return

        selected_layer = doc.activeNode()
        if selected_layer is None:
            QMessageBox.warning(None, "Error", "No hay una capa seleccionada")
            return

        # Buscar la capa tempselectionb visible
        tempselection_layer = None
        for layer in doc.rootNode().childNodes():
            if layer.name() == "tempselectionb" and layer.visible():
                tempselection_layer = layer
                break

        if tempselection_layer is None:
            QMessageBox.warning(None, "Error", "No se encontró una capa 'tempselectionb' visible")
            return

        tempselection_bounds = tempselection_layer.bounds()
        selected_bounds = selected_layer.bounds()

        new_layer = doc.createNode(f"{selected_layer.name()}_adjusted", "paintlayer")
        doc.rootNode().addChildNode(new_layer, selected_layer)

        selected_data = selected_layer.pixelData(0, 0, selected_bounds.width(), selected_bounds.height())

        scale_x = tempselection_bounds.width() / selected_bounds.width()
        scale_y = tempselection_bounds.height() / selected_bounds.height()

        for y in range(tempselection_bounds.height()):
            for x in range(tempselection_bounds.width()):
                src_x = int(x / scale_x)
                src_y = int(y / scale_y)
                if src_x < selected_bounds.width() and src_y < selected_bounds.height():
                    pixel_index = (src_y * selected_bounds.width() + src_x) * 4
                    pixel_data = selected_data[pixel_index:pixel_index+4]
                    new_layer.setPixelData(pixel_data, x, y, 1, 1)

        new_layer.move(tempselection_bounds.x(), tempselection_bounds.y())

        doc.rootNode().removeChildNode(selected_layer)

        new_layer.setName(selected_layer.name())

        doc.refreshProjection()

    def create_512x512(self):
        krita = Krita.instance()
        doc = krita.activeDocument()

        if not doc:
            print("No hay un documento activo.")
            return

        selection = Selection()
        selection.select(0, 0, 512, 512, 255)
        doc.setSelection(selection)

        color_info = InfoObject()
        color_info.setProperty("color", QColor(0, 239, 250))  # Color cian

        fill_layer = doc.createFillLayer("512x512", "color", color_info, selection)
        fill_layer.setOpacity(127)  # 50% de opacidad
        doc.rootNode().addChildNode(fill_layer, None)

        doc.setSelection(None)

        doc.refreshProjection()

    def create_512x512v(self):
        krita = Krita.instance()
        doc = krita.activeDocument()

        if not doc:
            QMessageBox.warning(None, "Error", "No hay un documento activo.")
            return

        vector_layer = doc.createVectorLayer("512x512v")
        if not vector_layer:
            QMessageBox.warning(None, "Error", "No se pudo crear la capa vectorial.")
            return

        fill_color = "#00EFFA"  
        svg_content = f'<svg><rect x="0" y="0" width="512" height="512" fill="{fill_color}" /></svg>'
        vector_layer.addShapesFromSvg(svg_content)

        vector_layer.setOpacity(127)

        doc.rootNode().addChildNode(vector_layer, None)
        doc.refreshProjection()
        doc.setActiveNode(vector_layer)

    def create_512x768(self):
        krita = Krita.instance()
        doc = krita.activeDocument()

        if not doc:
            print("No hay un documento activo.")
            return

        selection = Selection()
        selection.select(0, 0, 512, 768, 255)
        doc.setSelection(selection)

        color_info = InfoObject()
        color_info.setProperty("color", QColor(0, 239, 250))  # Color cian

        fill_layer = doc.createFillLayer("512x768", "color", color_info, selection)
        fill_layer.setOpacity(127)  # 50% de opacidad
        doc.rootNode().addChildNode(fill_layer, None)

        doc.setSelection(None)

        doc.refreshProjection()

    def create_512x768v(self):
        krita = Krita.instance()
        doc = krita.activeDocument()

        if not doc:
            QMessageBox.warning(None, "Error", "No hay un documento activo.")
            return

        vector_layer = doc.createVectorLayer("512x768v")
        if not vector_layer:
            QMessageBox.warning(None, "Error", "No se pudo crear la capa vectorial.")
            return

        fill_color = "#00EFFA"  
        svg_content = f'<svg><rect x="0" y="0" width="512" height="768" fill="{fill_color}" /></svg>'
        vector_layer.addShapesFromSvg(svg_content)

        vector_layer.setOpacity(127)

        doc.rootNode().addChildNode(vector_layer, None)
        doc.refreshProjection()
        doc.setActiveNode(vector_layer)

    def create_768x512(self):
        krita = Krita.instance()
        doc = krita.activeDocument()

        if not doc:
            print("No hay un documento activo.")
            return

        selection = Selection()
        selection.select(0, 0, 768, 512, 255)
        doc.setSelection(selection)

        color_info = InfoObject()
        color_info.setProperty("color", QColor(0, 239, 250))  # Color cian

        fill_layer = doc.createFillLayer("768x512", "color", color_info, selection)
        fill_layer.setOpacity(127)  # 50% de opacidad
        doc.rootNode().addChildNode(fill_layer, None)

        doc.setSelection(None)

        doc.refreshProjection()

    def trim_canvas(self):
        self.get_active_layer_bounds()
        self.TrimToCurrentLayerFunction()


    def get_active_layer_bounds(self):
        instance = Krita.instance()
        document = instance.activeDocument()
        
        if not document:
            return (False, None, 'No hay documento activo.')
        
        active_layer = document.activeNode()
        if not active_layer:
            return (False, None, 'No hay capa activa.')
        
        bounds = active_layer.bounds()
        return (True, bounds, '')

    def TrimToCurrentLayerFunction(self):
        instance = Krita.instance()
        document = instance.activeDocument()

        (success, bounds, message) = self.get_active_layer_bounds()  # Cambiado aquí
        if not success:
            return (False, message)

        # Comprueba si ya está recortado
        if all((
            document.xOffset() == bounds.x(),
            document.yOffset() == bounds.y(),
            document.width() == bounds.width(),
            document.height() == bounds.height(),
        )):
            return (False, 'El lienzo ya está recortado a la capa actual.')

        # Recorta el documento a los límites de la capa activa
        document.resizeImage(
            bounds.x(),
            bounds.y(),
            bounds.width(),
            bounds.height()
        )

        document.refreshProjection()
        return (True, 'Lienzo recortado según la capa actual.')

    class TrimToLayerExtension(Extension):
        def __init__(self, parent):
            super().__init__(parent)

        def setup(self):
            pass

        def createActions(self, window):
            action = window.createAction("trimToCurrentLayer", "Recortar según la capa actual")
            action.triggered.connect(self.trimToLayer)

        def trimToLayer(self):
            success, message = TrimToCurrentLayerFunction()
            if success:
                Krita.instance().activeWindow().activeView().canvas().update()
            print(message)

    # Instanciar y registrar la extensión
    Krita.instance().addExtension(TrimToLayerExtension(Krita.instance()))

    # Si el script se ejecuta directamente, llamar a la función de recorte
    if __name__ == '__main__':
        print(TrimToCurrentLayerFunction()[1])


    def find_selection(self):
        app = Krita.instance()
        doc = app.activeDocument()

        if not doc:
            print("No hay ningún documento activo.")
            return

        # Obtener la capa activa
        active_node = doc.activeNode()

        if not active_node:
            print("No se encontró una capa seleccionada.")
            return

        # Obtener los límites de la capa activa
        active_bounds = active_node.bounds()
        x, y, w, h = active_bounds.x(), active_bounds.y(), active_bounds.width(), active_bounds.height()

        if w == 0 or h == 0:
            print("La capa activa no tiene un contenido visible.")
            return

        # Crear una selección con los límites de la capa activa
        selection = Selection()
        selection.select(x, y, w, h, 255)
        doc.setSelection(selection)




    def get_next_available_name(self, doc, base_name):
        existing_names = [node.name() for node in doc.topLevelNodes()]
        if base_name not in existing_names:
            return base_name
        i = 1
        while f"{base_name}{i}" in existing_names:
            i += 1
        return f"{base_name}{i}"

Krita.instance().addExtension(SDZPasteExtension(Krita.instance()))
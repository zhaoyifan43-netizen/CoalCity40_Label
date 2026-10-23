# -*- coding: utf-8 -*-
"""
Build a Sentinel-2 true-colour preview in the current QGIS project.
Band order for RGB display: Red=B04, Green=B03, Blue=B02.
Does not modify source imagery or create semantic labels.

Run in QGIS Python Console:
exec(open(r"D:\CoalCity\qgis_tools\02_make_rgb_preview.py", encoding="utf-8").read())
"""
import os
import traceback
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer, QgsMultiBandColorRenderer
from qgis.core import QgsContrastEnhancement
from osgeo import gdal

INPUT_DIR = r"D:\CoalCity\input\CN01_Datong"
OUTPUT_DIR = r"D:\CoalCity\output"
VRT_PATH = os.path.join(OUTPUT_DIR, "CN01_Datong_truecolor_B04_B03_B02.vrt")
PROJECT_PATH = os.path.join(OUTPUT_DIR, "CoalCity40_CN01_Datong_working.qgz")

def log(s):
    print("[CoalCity-RGB] " + str(s))

def main():
    paths = [
        os.path.join(INPUT_DIR, "CN01_B04.tif"),  # Red
        os.path.join(INPUT_DIR, "CN01_B03.tif"),  # Green
        os.path.join(INPUT_DIR, "CN01_B02.tif"),  # Blue
    ]
    for p in paths:
        if not os.path.isfile(p):
            raise RuntimeError("找不到波段文件：" + p)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    vrt = gdal.BuildVRT(VRT_PATH, paths, options=gdal.BuildVRTOptions(separate=True))
    if vrt is None:
        raise RuntimeError("GDAL 创建 RGB VRT 失败。")
    vrt.FlushCache()
    vrt = None

    project = QgsProject.instance()
    rgb = QgsRasterLayer(VRT_PATH, "CN01_RGB_true_color_B04_B03_B02", "gdal")
    if not rgb.isValid():
        raise RuntimeError("RGB VRT 已生成，但 QGIS 无法打开：" + VRT_PATH)

    # Explicitly assign VRT band 1 to Red (B04), 2 to Green (B03), 3 to Blue (B02).
    renderer = QgsMultiBandColorRenderer(rgb.dataProvider(), 1, 2, 3)
    for band in (1, 2, 3):
        ce = QgsContrastEnhancement(rgb.dataProvider().dataType(band))
        stats = rgb.dataProvider().bandStatistics(band)
        # Percentile-like robust range is unavailable from this lightweight script;
        # use provider min/max and let QGIS render, without modifying source data.
        low = stats.minimumValue
        high = stats.maximumValue
        if high <= low:
            low, high = 0, 10000
        ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)
        ce.setMinimumValue(low)
        ce.setMaximumValue(high)
        if band == 1:
            renderer.setRedContrastEnhancement(ce)
        elif band == 2:
            renderer.setGreenContrastEnhancement(ce)
        else:
            renderer.setBlueContrastEnhancement(ce)
    rgb.setRenderer(renderer)
    project.addMapLayer(rgb)

    # Turn off the original individual bands and most indices to make RGB visible.
    for layer in project.mapLayers().values():
        nm = layer.name()
        node = project.layerTreeRoot().findLayer(layer.id())
        if node is None:
            continue
        if nm == rgb.name():
            node.setItemVisibilityChecked(True)
        elif nm in ("CN01_CUFR_circle_UTM", "label_polygons_review"):
            node.setItemVisibilityChecked(False)
        elif nm in ("CN01_B02", "CN01_B03", "CN01_B04", "CN01_B08", "CN01_B11",
                    "CN01_NDVI", "CN01_NDBI", "CN01_NDWI", "CN01_SCL",
                    "CN01_CUFR_circle_WGS84"):
            node.setItemVisibilityChecked(False)

    # Zoom to the RGB image extent.
    iface.setActiveLayer(rgb)
    iface.mapCanvas().setExtent(rgb.extent())
    iface.mapCanvas().refresh()

    project.setFileName(PROJECT_PATH)
    ok = project.write()
    log("RGB 预览图层已加载：B04=红、B03=绿、B02=蓝。")
    log("VRT 文件：" + VRT_PATH)
    log("工程保存：" + ("成功" if ok else "失败") + " -> " + PROJECT_PATH)
    log("这只是显示预览，不是分类结果。请目视确认影像清晰、颜色正常后再进行预标注。")

try:
    main()
except Exception:
    log(traceback.format_exc())

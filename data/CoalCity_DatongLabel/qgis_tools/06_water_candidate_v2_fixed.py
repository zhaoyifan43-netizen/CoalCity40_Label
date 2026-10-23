# -*- coding: utf-8 -*-
"""
Fixed v2 water candidate script.
Avoids removing/reusing a deleted QgsLayerTreeLayer node.
Run in QGIS Python Console:
exec(open(r"D:\CoalCity\qgis_tools\06_water_candidate_v2_fixed.py", encoding="utf-8").read())
"""
import os, traceback
import numpy as np
from osgeo import gdal
from qgis.core import QgsProject, QgsRasterLayer, QgsPalettedRasterRenderer
from qgis.PyQt.QtGui import QColor

INPUT_DIR = r"D:\CoalCity\input\CN01_Datong"
OUTPUT_DIR = r"D:\CoalCity\output\candidate_masks"
SCL_PATH = os.path.join(INPUT_DIR, "CN01_SCL.tif")
OUT_PATH = os.path.join(OUTPUT_DIR, "CN01_water_candidate_v2_scl6.tif")
LAYER_NAME = "CN01_water_candidate_v2_SCL6"

def log(msg):
    print("[CoalCity-Water-v2-Fixed] " + str(msg))

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    src = gdal.Open(SCL_PATH, gdal.GA_ReadOnly)
    if src is None:
        raise RuntimeError("无法读取 SCL 文件：" + SCL_PATH)

    scl = src.GetRasterBand(1).ReadAsArray()
    nodata = src.GetRasterBand(1).GetNoDataValue()
    if scl is None:
        raise RuntimeError("无法读取 SCL 像素数组。")

    mask = (scl == 6)
    if nodata is not None:
        mask &= (scl != nodata)

    driver = gdal.GetDriverByName("GTiff")
    if os.path.exists(OUT_PATH):
        driver.Delete(OUT_PATH)
    out = driver.Create(
        OUT_PATH, src.RasterXSize, src.RasterYSize, 1, gdal.GDT_Byte,
        options=["COMPRESS=LZW", "TILED=YES"]
    )
    if out is None:
        raise RuntimeError("无法创建输出 GeoTIFF：" + OUT_PATH)
    out.SetGeoTransform(src.GetGeoTransform())
    out.SetProjection(src.GetProjection())
    outband = out.GetRasterBand(1)
    outband.WriteArray(np.where(mask, 1, 0).astype(np.uint8))
    outband.SetNoDataValue(0)
    outband.FlushCache()
    out.FlushCache()
    out = None
    src = None

    project = QgsProject.instance()
    # Remove only any prior layer with this exact display name.
    for old_layer in list(project.mapLayers().values()):
        if old_layer.name() == LAYER_NAME:
            project.removeMapLayer(old_layer.id())

    layer = QgsRasterLayer(OUT_PATH, LAYER_NAME, "gdal")
    if not layer.isValid():
        raise RuntimeError("输出栅格无法在 QGIS 中打开：" + OUT_PATH)

    renderer = QgsPalettedRasterRenderer(
        layer.dataProvider(),
        1,
        [
            QgsPalettedRasterRenderer.Class(0, QColor(0, 0, 0, 0), "非水体"),
            QgsPalettedRasterRenderer.Class(1, QColor(0, 100, 255, 180), "SCL 水体候选")
        ]
    )
    layer.setRenderer(renderer)

    # addMapLayer places the new layer into the layer tree; no manual node
    # removal/reinsertion is needed.
    project.addMapLayer(layer)

    node = project.layerTreeRoot().findLayer(layer.id())
    if node is not None:
        node.setItemVisibilityChecked(True)

    log("成功生成并加载新版水体候选层。")
    log("水体候选像素数：" + str(int(np.count_nonzero(mask))))
    log("输出文件：" + OUT_PATH)
    log("请取消旧 CN01_water_candidate 的勾选，只保留 RGB 与 CN01_water_candidate_v2_SCL6。")
    if project.fileName():
        log("工程保存：" + ("成功" if project.write() else "失败"))

try:
    main()
except Exception:
    log(traceback.format_exc())

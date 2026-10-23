# -*- coding: utf-8 -*-
"""Create revised water candidate from SCL class 6 only. Source files unchanged."""
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

def log(s):
    print("[CoalCity-Water-v2] " + str(s))

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    src = gdal.Open(SCL_PATH, gdal.GA_ReadOnly)
    if src is None:
        raise RuntimeError("无法读取 SCL: " + SCL_PATH)
    band = src.GetRasterBand(1)
    scl = band.ReadAsArray()
    if scl is None:
        raise RuntimeError("无法读取 SCL 像素。")
    nodata = band.GetNoDataValue()
    mask = (scl == 6)
    if nodata is not None:
        mask &= (scl != nodata)

    driver = gdal.GetDriverByName("GTiff")
    if os.path.exists(OUT_PATH):
        driver.Delete(OUT_PATH)
    out = driver.Create(OUT_PATH, src.RasterXSize, src.RasterYSize, 1,
                        gdal.GDT_Byte, options=["COMPRESS=LZW", "TILED=YES"])
    out.SetGeoTransform(src.GetGeoTransform())
    out.SetProjection(src.GetProjection())
    ob = out.GetRasterBand(1)
    ob.WriteArray(np.where(mask, 1, 0).astype(np.uint8))
    ob.SetNoDataValue(0)
    ob.FlushCache()
    out.FlushCache()
    out = None
    src = None

    project = QgsProject.instance()
    for lyr in list(project.mapLayers().values()):
        if lyr.name() == LAYER_NAME:
            project.removeMapLayer(lyr.id())

    layer = QgsRasterLayer(OUT_PATH, LAYER_NAME, "gdal")
    if not layer.isValid():
        raise RuntimeError("输出水体栅格无法在 QGIS 中打开。")

    # Palette: class 0 transparent; class 1 semi-transparent blue.
    renderer = QgsPalettedRasterRenderer(
        layer.dataProvider(), 1,
        [
            QgsPalettedRasterRenderer.Class(0, QColor(0, 0, 0, 0), "非水体"),
            QgsPalettedRasterRenderer.Class(1, QColor(0, 100, 255, 180), "SCL 水体候选"),
        ]
    )
    layer.setRenderer(renderer)
    project.addMapLayer(layer)
    node = project.layerTreeRoot().findLayer(layer.id())
    node.setItemVisibilityChecked(True)
    root = project.layerTreeRoot()
    root.removeChildNode(node)
    root.insertChildNode(0, node)

    log("已生成新版水体候选层：仅采用 SCL 类别 6。")
    log("水体候选像素数：" + str(int(np.count_nonzero(mask))))
    log("输出：" + OUT_PATH)
    log("请关闭旧的 CN01_water_candidate，只保留 RGB + CN01_water_candidate_v2_SCL6 进行检查。")
    if project.fileName():
        project.write()

try:
    main()
except Exception:
    log(traceback.format_exc())

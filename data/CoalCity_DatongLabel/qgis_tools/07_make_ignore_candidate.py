# -*- coding: utf-8 -*-
"""
Create a unified Ignore candidate from Sentinel-2 SCL classes.
Classes: 0 no data, 1 saturated/defective, 3 cloud shadow,
8 medium-probability cloud, 9 high-probability cloud,
10 thin cirrus, 11 snow/ice.
This is a review candidate only; it does NOT write final labels.

Run in QGIS Python Console:
exec(open(r"D:\CoalCity\qgis_tools\07_make_ignore_candidate.py", encoding="utf-8").read())
"""
import os
import traceback
import numpy as np
from osgeo import gdal
from qgis.core import QgsProject, QgsRasterLayer, QgsPalettedRasterRenderer
from qgis.PyQt.QtGui import QColor

INPUT_DIR = r"D:\CoalCity\input\CN01_Datong"
OUTPUT_DIR = r"D:\CoalCity\output\candidate_masks"
SCL_PATH = os.path.join(INPUT_DIR, "CN01_SCL.tif")
OUT_PATH = os.path.join(OUTPUT_DIR, "CN01_ignore_candidate_v2_scl.tif")
LAYER_NAME = "CN01_ignore_candidate_v2_SCL"

IGNORE_CLASSES = {0, 1, 3, 8, 9, 10, 11}

def log(msg):
    print("[CoalCity-Ignore-v2] " + str(msg))

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    src = gdal.Open(SCL_PATH, gdal.GA_ReadOnly)
    if src is None:
        raise RuntimeError("无法读取 SCL 文件：" + SCL_PATH)

    band = src.GetRasterBand(1)
    scl = band.ReadAsArray()
    nodata = band.GetNoDataValue()
    if scl is None:
        raise RuntimeError("无法读取 SCL 像素数组。")

    mask = np.isin(scl, list(IGNORE_CLASSES))
    if nodata is not None:
        # SCL's explicit class 0 is no-data in many products; it remains Ignore.
        # Don't remove it just because the provider marks 0 as NoData.
        pass

    driver = gdal.GetDriverByName("GTiff")
    if os.path.exists(OUT_PATH):
        driver.Delete(OUT_PATH)
    out = driver.Create(
        OUT_PATH, src.RasterXSize, src.RasterYSize, 1, gdal.GDT_Byte,
        options=["COMPRESS=LZW", "TILED=YES"]
    )
    if out is None:
        raise RuntimeError("无法创建 Ignore 候选栅格：" + OUT_PATH)
    out.SetGeoTransform(src.GetGeoTransform())
    out.SetProjection(src.GetProjection())
    outband = out.GetRasterBand(1)
    # 255 means Ignore candidate; 0 is transparent background.
    outband.WriteArray(np.where(mask, 255, 0).astype(np.uint8))
    outband.SetNoDataValue(0)
    outband.FlushCache()
    out.FlushCache()
    out = None
    src = None

    project = QgsProject.instance()
    for old_layer in list(project.mapLayers().values()):
        if old_layer.name() == LAYER_NAME:
            project.removeMapLayer(old_layer.id())

    layer = QgsRasterLayer(OUT_PATH, LAYER_NAME, "gdal")
    if not layer.isValid():
        raise RuntimeError("输出 Ignore 候选栅格无法在 QGIS 中打开。")

    renderer = QgsPalettedRasterRenderer(
        layer.dataProvider(),
        1,
        [
            QgsPalettedRasterRenderer.Class(0, QColor(0, 0, 0, 0), "非 Ignore"),
            QgsPalettedRasterRenderer.Class(255, QColor(255, 80, 0, 170), "Ignore 候选 (255)")
        ]
    )
    layer.setRenderer(renderer)
    project.addMapLayer(layer)

    node = project.layerTreeRoot().findLayer(layer.id())
    if node is not None:
        node.setItemVisibilityChecked(True)

    # Set visibility to only the combined Ignore candidate + RGB.
    visible_names = {LAYER_NAME, "CN01_RGB_true_color_B04_B03_B02"}
    root = project.layerTreeRoot()
    for lyr in project.mapLayers().values():
        node = root.findLayer(lyr.id())
        if node is not None:
            node.setItemVisibilityChecked(lyr.name() in visible_names)

    log("Ignore 候选层生成并加载成功。")
    log("Ignore 候选像素数：" + str(int(np.count_nonzero(mask))))
    log("覆盖的 SCL 类别：" + ", ".join(str(x) for x in sorted(IGNORE_CLASSES)))
    log("输出文件：" + OUT_PATH)
    log("请目视复核橙红色区域；这不是最终标注。")
    if project.fileName():
        log("工程保存：" + ("成功" if project.write() else "失败"))

try:
    main()
except Exception:
    log(traceback.format_exc())

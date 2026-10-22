# -*- coding: utf-8 -*-
"""
Improve Sentinel-2 RGB display using robust percentile stretch.
Does not alter original TIFF data or create labels.

Run in QGIS Python Console:
exec(open(r"D:\CoalCity\qgis_tools\03_fix_rgb_brightness.py", encoding="utf-8").read())
"""
import os
import traceback
import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsProject, QgsRasterLayer, QgsMultiBandColorRenderer,
    QgsContrastEnhancement
)

INPUT_DIR = r"D:\CoalCity\input\CN01_Datong"
OUTPUT_DIR = r"D:\CoalCity\output"
VRT_PATH = os.path.join(OUTPUT_DIR, "CN01_Datong_truecolor_B04_B03_B02.vrt")
LAYER_NAME = "CN01_RGB_true_color_B04_B03_B02"

BANDS = [
    ("CN01_B04.tif", "Red (B04)"),
    ("CN01_B03.tif", "Green (B03)"),
    ("CN01_B02.tif", "Blue (B02)"),
]

def log(s):
    print("[CoalCity-RGB-Stretch] " + str(s))

def percentile_range(path, lower=2, upper=98):
    ds = gdal.Open(path, gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError("GDAL 无法读取：" + path)
    band = ds.GetRasterBand(1)
    xsize, ysize = ds.RasterXSize, ds.RasterYSize

    # Sample at most roughly 800k pixels to keep memory/time reasonable.
    stride = max(1, int(max(xsize, ysize) / 1000))
    arr = band.ReadAsArray(0, 0, xsize, ysize, max(1, xsize // stride), max(1, ysize // stride))
    if arr is None:
        raise RuntimeError("无法读取栅格像素：" + path)
    arr = np.asarray(arr, dtype=np.float32).ravel()

    nodata = band.GetNoDataValue()
    valid = np.isfinite(arr)
    if nodata is not None:
        valid &= (arr != nodata)
    # Sentinel reflectance often has zero/background pixels; exclude zeros only
    # when enough nonzero values remain, to avoid stretching against black borders.
    nonzero = valid & (arr != 0)
    if np.count_nonzero(nonzero) > max(100, int(0.01 * arr.size)):
        valid = nonzero
    values = arr[valid]
    ds = None
    if values.size < 100:
        raise RuntimeError("有效像素太少，无法计算显示拉伸范围：" + path)
    lo, hi = np.percentile(values, [lower, upper])
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        lo, hi = float(np.min(values)), float(np.max(values))
    if hi <= lo:
        raise RuntimeError("像素范围无效：" + path)
    return float(lo), float(hi), int(values.size)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    paths = [os.path.join(INPUT_DIR, fn) for fn, _ in BANDS]
    for p in paths:
        if not os.path.isfile(p):
            raise RuntimeError("找不到波段文件：" + p)

    # Rebuild the three-band VRT in Red, Green, Blue order.
    vrt = gdal.BuildVRT(VRT_PATH, paths, options=gdal.BuildVRTOptions(separate=True))
    if vrt is None:
        raise RuntimeError("无法创建 RGB VRT。")
    vrt.FlushCache()
    vrt = None

    project = QgsProject.instance()
    old = [lyr for lyr in project.mapLayers().values() if lyr.name() == LAYER_NAME]
    for lyr in old:
        project.removeMapLayer(lyr.id())

    rgb = QgsRasterLayer(VRT_PATH, LAYER_NAME, "gdal")
    if not rgb.isValid():
        raise RuntimeError("RGB VRT 无法在 QGIS 中打开。")

    renderer = QgsMultiBandColorRenderer(rgb.dataProvider(), 1, 2, 3)
    ranges = []
    for idx, (path, label) in enumerate(zip(paths, [b[1] for b in BANDS]), start=1):
        lo, hi, n = percentile_range(path, 2, 98)
        ranges.append((label, lo, hi, n))
        ce = QgsContrastEnhancement(rgb.dataProvider().dataType(idx))
        ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)
        ce.setMinimumValue(lo)
        ce.setMaximumValue(hi)
        if idx == 1:
            renderer.setRedContrastEnhancement(ce)
        elif idx == 2:
            renderer.setGreenContrastEnhancement(ce)
        else:
            renderer.setBlueContrastEnhancement(ce)

    rgb.setRenderer(renderer)
    project.addMapLayer(rgb)

    # Keep RGB visible; hide single-band layers to avoid confusion.
    for lyr in project.mapLayers().values():
        node = project.layerTreeRoot().findLayer(lyr.id())
        if node is None:
            continue
        if lyr.name() == LAYER_NAME:
            node.setItemVisibilityChecked(True)
        elif lyr.name() in (
            "CN01_B02", "CN01_B03", "CN01_B04", "CN01_B08", "CN01_B11",
            "CN01_NDVI", "CN01_NDBI", "CN01_NDWI", "CN01_SCL",
            "CN01_CUFR_circle_UTM", "CN01_CUFR_circle_WGS84",
            "label_polygons_review"
        ):
            node.setItemVisibilityChecked(False)

    iface.setActiveLayer(rgb)
    iface.mapCanvas().setExtent(rgb.extent())
    iface.mapCanvas().refresh()

    project_path = os.path.join(OUTPUT_DIR, "CoalCity40_CN01_Datong_working.qgz")
    project.setFileName(project_path)
    ok = project.write()

    log("已应用每个波段的 2%-98% 分位数显示拉伸。")
    for label, lo, hi, n in ranges:
        log(f"{label}: min={lo:.3f}, max={hi:.3f}, valid_sample={n}")
    log("已保存工程：" + ("成功" if ok else "失败") + " -> " + project_path)
    log("这是显示增强，不改变源影像，也不代表自动分类结果。")

try:
    main()
except Exception:
    log(traceback.format_exc())

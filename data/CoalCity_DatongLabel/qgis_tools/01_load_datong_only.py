# -*- coding: utf-8 -*-
"""
CoalCity-40 | Datong-only QGIS project loader
Run in QGIS Python Console:
exec(open(r"D:\CoalCity\qgis_tools\01_load_datong_only.py", encoding="utf-8").read())

This script does not create semantic labels. It loads only CN01_Datong rasters
and its CUFR boundaries into a clean project and saves a separate project file.
"""
import os
import traceback
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer, QgsMapLayer

INPUT_DIR = r"D:\CoalCity\input"
DATONG_DIR = os.path.join(INPUT_DIR, "CN01_Datong")
OUTPUT_DIR = r"D:\CoalCity\output"
PROJECT_PATH = os.path.join(OUTPUT_DIR, "CoalCity40_CN01_Datong_working.qgz")

RASTER_NAMES = [
    "CN01_B02.tif",
    "CN01_B03.tif",
    "CN01_B04.tif",
    "CN01_B08.tif",
    "CN01_B11.tif",
    "CN01_NDVI.tif",
    "CN01_NDBI.tif",
    "CN01_NDWI.tif",
    "CN01_SCL.tif",
]
VECTOR_NAMES = [
    "CN01_CUFR_circle_UTM.geojson",
    "CN01_CUFR_circle_WGS84.geojson",
]

def log(s):
    print("[CoalCity-Datong] " + str(s))

def main():
    if not os.path.isdir(DATONG_DIR):
        raise RuntimeError("未找到大同数据目录：" + DATONG_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    project = QgsProject.instance()
    # This only clears the current project's layer list, not source files.
    # Save any other unsaved project before running.
    project.clear()
    project.setTitle("CoalCity-40 | CN01 Datong")

    added = []
    missing = []
    invalid = []

    # Add rasters in a useful display order; true color is B04/B03/B02.
    for fn in RASTER_NAMES:
        path = os.path.join(DATONG_DIR, fn)
        if not os.path.isfile(path):
            missing.append(path)
            continue
        layer = QgsRasterLayer(path, os.path.splitext(fn)[0])
        if not layer.isValid():
            invalid.append(path)
            continue
        project.addMapLayer(layer)
        added.append(layer.name())

    for fn in VECTOR_NAMES:
        path = os.path.join(DATONG_DIR, fn)
        if not os.path.isfile(path):
            missing.append(path)
            continue
        layer = QgsVectorLayer(path, os.path.splitext(fn)[0], "ogr")
        if not layer.isValid():
            invalid.append(path)
            continue
        project.addMapLayer(layer)
        added.append(layer.name())

    # If the existing review layer is present, load it; otherwise skip it.
    gpkg = os.path.join(OUTPUT_DIR, "CoalCity40_CN01_Datong_review.gpkg")
    if os.path.isfile(gpkg):
        review = QgsVectorLayer(gpkg + "|layername=label_polygons", "label_polygons_review", "ogr")
        if review.isValid():
            project.addMapLayer(review)
            added.append(review.name())

    project.setCrs(next(
        (lyr.crs() for lyr in project.mapLayers().values()
         if isinstance(lyr, QgsRasterLayer) and lyr.isValid()),
        project.crs()
    ))
    project.setFileName(PROJECT_PATH)
    ok = project.write()

    log("加载完成。")
    log("成功加载图层数：" + str(len(added)))
    for n in added:
        log("  + " + n)
    if missing:
        log("缺失文件（请核对路径/文件名）：")
        for p in missing:
            log("  - " + p)
    if invalid:
        log("无法打开的文件：")
        for p in invalid:
            log("  ! " + p)
    log("工程保存：" + ("成功" if ok else "失败") + " -> " + PROJECT_PATH)
    log("此步骤只整理大同工作工程，不会自动生成类别标签。")

try:
    main()
except Exception:
    log(traceback.format_exc())

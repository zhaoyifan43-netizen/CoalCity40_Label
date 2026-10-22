# -*- coding: utf-8 -*-
"""
CoalCity-40 PyQGIS starter
Run inside the QGIS Python Console on Windows:
exec(open(r"D:\CoalCity\qgis_tools\00_prepare_workspace.py", encoding="utf-8").read())

This script prepares a review workspace only. It does NOT invent semantic labels.
Unreviewed features must remain verified=0. class_id may be NULL until reviewed.
Use class_id=255 only for explicitly reviewed Ignore polygons.
"""
import os
import csv
import traceback
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsField,
    QgsVectorFileWriter, QgsCoordinateReferenceSystem,
    QgsDefaultValue, QgsWkbTypes
)
from qgis.PyQt.QtCore import QVariant

INPUT_DIR = r"D:\CoalCity\input"
OUTPUT_DIR = r"D:\CoalCity\output"
TOOLS_DIR = r"D:\CoalCity\qgis_tools"
CITY_ID = "CN01_Datong"  # Change this for another city if needed.
GPKG_NAME = f"CoalCity40_{CITY_ID}_review.gpkg"
PROJECT_NAME = f"CoalCity40_{CITY_ID}_review.qgz"

RASTER_EXTS = (".tif", ".tiff", ".vrt", ".img")
VECTOR_EXTS = (".gpkg", ".shp", ".geojson", ".json", ".gml", ".kml")
SKIP_DIRS = {".git", "__pycache__", "output", "qgis_tools"}

def log(msg):
    print("[CoalCity] " + str(msg))

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def list_data_files(root):
    found = []
    for cur, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext in RASTER_EXTS or ext in VECTOR_EXTS:
                found.append(os.path.join(cur, fn))
    return sorted(found)

def create_gpkg_layer(gpkg_path, layer_name, crs_authid):
    """Create a polygon layer in a GeoPackage with review fields."""
    if os.path.exists(gpkg_path):
        uri = gpkg_path + "|layername=" + layer_name
        existing = QgsVectorLayer(uri, layer_name, "ogr")
        if existing.isValid():
            return existing
    crs = QgsCoordinateReferenceSystem(crs_authid) if crs_authid else QgsCoordinateReferenceSystem("EPSG:4326")
    layer = QgsVectorLayer("MultiPolygon?crs=" + crs.authid(), layer_name, "memory")
    provider = layer.dataProvider()
    fields = [
        QgsField("class_id", QVariant.Int),
        QgsField("verified", QVariant.Int),
        QgsField("evidence", QVariant.String, len=254),
        QgsField("note", QVariant.String, len=1000),
    ]
    provider.addAttributes(fields)
    layer.updateFields()

    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = "GPKG"
    opts.layerName = layer_name
    opts.fileEncoding = "UTF-8"
    if os.path.exists(gpkg_path):
        opts.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
    result = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, gpkg_path, QgsProject.instance().transformContext(), opts
    )
    # QGIS versions return tuples; first item is error code.
    if result[0] != QgsVectorFileWriter.NoError:
        raise RuntimeError("创建 GeoPackage 图层失败: " + repr(result))
    out = QgsVectorLayer(gpkg_path + "|layername=" + layer_name, layer_name, "ogr")
    if not out.isValid():
        raise RuntimeError("创建后无法重新打开图层: " + layer_name)
    return out

def main():
    if not os.path.isdir(INPUT_DIR):
        raise RuntimeError(
            "找不到输入目录: " + INPUT_DIR +
            "\n请确认路径存在；如果数据在其他位置，请修改脚本顶部 INPUT_DIR。"
        )
    ensure_dir(OUTPUT_DIR)
    ensure_dir(TOOLS_DIR)

    project = QgsProject.instance()
    project.clear()
    project.setTitle(f"CoalCity-40 review workspace - {CITY_ID}")

    files = list_data_files(INPUT_DIR)
    inventory_path = os.path.join(OUTPUT_DIR, f"{CITY_ID}_input_inventory.csv")
    gpkg_path = os.path.join(OUTPUT_DIR, GPKG_NAME)
    project_path = os.path.join(OUTPUT_DIR, PROJECT_NAME)

    inventory_rows = []
    loaded_count = 0
    first_valid_raster_crs = None

    for path in files:
        ext = os.path.splitext(path)[1].lower()
        name = os.path.basename(path)
        kind = "raster" if ext in RASTER_EXTS else "vector"
        layer = None
        crs_text = ""
        extent_text = ""
        resolution_text = ""
        band_count = ""
        status = "not_loaded"

        try:
            if kind == "raster":
                layer = QgsRasterLayer(path, name)
                if layer.isValid():
                    crs_text = layer.crs().authid()
                    extent_text = layer.extent().toString()
                    provider = layer.dataProvider()
                    resolution_text = f"{provider.xSize()}x{provider.ySize()}; px={layer.rasterUnitsPerPixelX():.6g},{layer.rasterUnitsPerPixelY():.6g}"
                    band_count = provider.bandCount()
                    status = "loaded"
                    if not first_valid_raster_crs and crs_text:
                        first_valid_raster_crs = crs_text
                else:
                    status = "invalid_raster"
            else:
                # For GeoPackage, load each file's default/first layer.
                layer = QgsVectorLayer(path, name, "ogr")
                if layer.isValid():
                    crs_text = layer.crs().authid()
                    extent_text = layer.extent().toString()
                    status = "loaded"
                else:
                    status = "invalid_vector"

            if layer and layer.isValid():
                project.addMapLayer(layer, False)
                # Keep source layers grouped together in the layer tree.
                project.layerTreeRoot().addLayer(layer)
                loaded_count += 1
        except Exception as e:
            status = "error: " + str(e)

        inventory_rows.append({
            "path": path,
            "kind": kind,
            "status": status,
            "crs": crs_text,
            "extent": extent_text,
            "raster_dimensions_resolution": resolution_text,
            "band_count": band_count,
        })

    with open(inventory_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["path", "kind", "status", "crs", "extent",
                        "raster_dimensions_resolution", "band_count"]
        )
        writer.writeheader()
        writer.writerows(inventory_rows)

    # Review layer CRS follows the first valid raster CRS where available.
    review_crs = first_valid_raster_crs or "EPSG:4326"
    review_layer = create_gpkg_layer(gpkg_path, "label_polygons", review_crs)
    project.addMapLayer(review_layer, False)
    project.layerTreeRoot().insertLayer(0, review_layer)

    # Make verified default to 0 for newly created features (unreviewed).
    idx = review_layer.fields().indexFromName("verified")
    if idx >= 0:
        review_layer.setDefaultValueDefinition(idx, QgsDefaultValue("0"))
    review_layer.setDisplayExpression(
        "coalesce(to_string(\"class_id\"), 'UNASSIGNED') || ' | verified=' || "
        "coalesce(to_string(\"verified\"), '0')"
    )

    # Save project and make the review layer active if interface is available.
    project.setFileName(project_path)
    if not project.write():
        log("警告：QGIS 项目保存失败，请检查输出目录权限。")

    log("初始化完成。")
    log(f"扫描到数据文件: {len(files)}")
    log(f"成功加载图层: {loaded_count}")
    log(f"数据清单: {inventory_path}")
    log(f"标注 GeoPackage: {gpkg_path}")
    log(f"QGIS 项目: {project_path}")
    log("注意：当前只创建空白复核图层，不会自动填入类别。")
    log("字段规则：verified=0 未复核，verified=1 已人工确认；class_id=255 表示显式 Ignore。")
    log("下一步请把 input_inventory.csv 发回，以便按真实数据波段和命名配置预标注。")

try:
    main()
except Exception:
    log("执行失败：")
    log(traceback.format_exc())

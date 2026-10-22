# -*- coding: utf-8 -*-
"""
CoalCity-40 | CN01 Datong batch pre-annotation v1
For Windows QGIS Python Console. Does NOT claim to produce final verified labels.

Run:
exec(open(r"D:\CoalCity\qgis_tools\08_auto_prelabel_datong.py", encoding="utf-8").read())

Inputs expected in D:\CoalCity\input\CN01_Datong:
  CN01_B02.tif, CN01_B03.tif, CN01_B04.tif, CN01_B08.tif, CN01_B11.tif
  CN01_NDVI.tif, CN01_NDBI.tif, CN01_NDWI.tif, CN01_SCL.tif
  CN01_CUFR_circle_UTM.geojson or CN01_CUFR_circle_WGS84.geojson

Outputs:
  D:\CoalCity\output\CoalCity40_CN01_Datong_prelabel_v1\
    CoalCity40_CN01_Datong_prelabel_v1.tif       provisional label raster, values 0-13/255
    candidate_masks\class_*.tif                  category candidate masks
    confidence.tif                               0 unresolved, 1 tentative, 2 relatively stronger
    prelabel_counts.csv                          pixel counts/area summary
    review_queue.csv                             categories requiring review/evidence
    run_report.txt                               input checks and limitations

IMPORTANT:
- 255 means Ignore/unresolved in the provisional raster; this is not a finished label.
- Generic land-cover categories are only provisionally assigned where rules allow.
- Built density, cropland, roads, coal classes 8-12, and other class 13 are emitted as candidates/review tasks, not auto-confirmed.
- Original rasters and previous outputs are not overwritten.
"""
import os
import csv
import traceback
import numpy as np
from osgeo import gdal, ogr, osr
from qgis.core import (
    QgsProject, QgsRasterLayer, QgsPalettedRasterRenderer
)
from qgis.PyQt.QtGui import QColor

INPUT_DIR = r"D:\CoalCity\input\CN01_Datong"
OUTPUT_ROOT = r"D:\CoalCity\output"
OUT_DIR = os.path.join(OUTPUT_ROOT, "CoalCity40_CN01_Datong_prelabel_v1")
MASK_DIR = os.path.join(OUT_DIR, "candidate_masks")

RASTER_FILES = {
    "B02": "CN01_B02.tif",
    "B03": "CN01_B03.tif",
    "B04": "CN01_B04.tif",
    "B08": "CN01_B08.tif",
    "B11": "CN01_B11.tif",
    "NDVI": "CN01_NDVI.tif",
    "NDBI": "CN01_NDBI.tif",
    "NDWI": "CN01_NDWI.tif",
    "SCL": "CN01_SCL.tif",
}

# SCL classes used as Ignore candidates. These are standard Sentinel-2 SCL codes.
IGNORE_SCL = {0, 1, 3, 8, 9, 10, 11}
CLASS_NAMES = {
    0: "高密度建成区", 1: "低密度建成区", 2: "农田",
    3: "林木或高密度植被", 4: "草地或稀疏植被",
    5: "裸地", 6: "水体", 7: "道路",
    8: "可观测活跃采掘区", 9: "煤矿废弃物堆场或排土场",
    10: "采煤沉陷水体", 11: "煤炭加工与电力设施",
    12: "煤炭物流基础设施", 13: "其他", 255: "Ignore/待判读"
}

def log(msg):
    print("[CoalCity-AutoPrelabel] " + str(msg))

def read_raster(path):
    ds = gdal.Open(path, gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError("无法读取输入栅格: " + path)
    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray()
    if arr is None:
        raise RuntimeError("无法读取像素: " + path)
    info = {
        "path": path, "gt": ds.GetGeoTransform(), "proj": ds.GetProjection(),
        "width": ds.RasterXSize, "height": ds.RasterYSize,
        "nodata": band.GetNoDataValue(), "dtype": band.DataType
    }
    return ds, arr, info

def same_grid(a, b):
    if a["width"] != b["width"] or a["height"] != b["height"]:
        return False
    if a["gt"] != b["gt"]:
        return False
    # WKT strings can differ in formatting; compare normalized spatial refs.
    sa, sb = osr.SpatialReference(), osr.SpatialReference()
    if a["proj"]:
        sa.ImportFromWkt(a["proj"])
    if b["proj"]:
        sb.ImportFromWkt(b["proj"])
    try:
        return bool(sa.IsSame(sb))
    except Exception:
        return a["proj"] == b["proj"]

def find_cufr_file():
    candidates = [
        os.path.join(INPUT_DIR, "CN01_CUFR_circle_UTM.geojson"),
        os.path.join(INPUT_DIR, "CN01_CUFR_circle_WGS84.geojson"),
        os.path.join(r"D:\CoalCity\input", "CN01_CUFR_circle_UTM.geojson"),
        os.path.join(r"D:\CoalCity\input", "CN01_CUFR_circle_WGS84.geojson"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    # Search only shallow folders for an exact CN01 CUFR file.
    for root in [INPUT_DIR, r"D:\CoalCity\input"]:
        if os.path.isdir(root):
            for name in os.listdir(root):
                if name.lower().startswith("cn01_cufr_circle") and name.lower().endswith(".geojson"):
                    p = os.path.join(root, name)
                    if os.path.isfile(p):
                        return p
    return None

def rasterize_cufr(vector_path, ref_ds):
    """Rasterize CUFR polygon to reference raster grid, transforming geometry if needed."""
    src_ds = ogr.Open(vector_path, 0)
    if src_ds is None:
        raise RuntimeError("无法打开 CUFR 边界: " + vector_path)
    src_layer = src_ds.GetLayer(0)
    if src_layer is None:
        raise RuntimeError("CUFR GeoJSON 中没有图层。")
    src_srs = src_layer.GetSpatialRef()
    target_srs = osr.SpatialReference()
    target_srs.ImportFromWkt(ref_ds.GetProjection())
    if src_srs is None:
        raise RuntimeError("CUFR 边界缺少坐标系，不能安全栅格化。")
    transform = None
    if not src_srs.IsSame(target_srs):
        transform = osr.CoordinateTransformation(src_srs, target_srs)

    mem_drv = ogr.GetDriverByName("Memory")
    mem_vec = mem_drv.CreateDataSource("cufr_memory")
    mem_layer = mem_vec.CreateLayer("cufr", srs=target_srs, geom_type=ogr.wkbUnknown)
    for feat in src_layer:
        geom = feat.GetGeometryRef()
        if geom is None:
            continue
        geom2 = geom.Clone()
        if transform is not None:
            geom2.Transform(transform)
        out_feat = ogr.Feature(mem_layer.GetLayerDefn())
        out_feat.SetGeometry(geom2)
        mem_layer.CreateFeature(out_feat)
        out_feat = None
        geom2 = None

    mem_raster = gdal.GetDriverByName("MEM").Create(
        "", ref_ds.RasterXSize, ref_ds.RasterYSize, 1, gdal.GDT_Byte
    )
    mem_raster.SetGeoTransform(ref_ds.GetGeoTransform())
    mem_raster.SetProjection(ref_ds.GetProjection())
    rb = mem_raster.GetRasterBand(1)
    rb.Fill(0)
    gdal.RasterizeLayer(mem_raster, [1], mem_layer, burn_values=[1], options=["ALL_TOUCHED=TRUE"])
    arr = rb.ReadAsArray().astype(bool)
    mem_raster = None
    mem_vec = None
    src_ds = None
    return arr

def write_byte_tif(ref_ds, path, arr, nodata=None):
    driver = gdal.GetDriverByName("GTiff")
    if os.path.exists(path):
        driver.Delete(path)
    out = driver.Create(
        path, ref_ds.RasterXSize, ref_ds.RasterYSize, 1, gdal.GDT_Byte,
        options=["COMPRESS=LZW", "TILED=YES"]
    )
    if out is None:
        raise RuntimeError("无法创建输出栅格: " + path)
    out.SetGeoTransform(ref_ds.GetGeoTransform())
    out.SetProjection(ref_ds.GetProjection())
    b = out.GetRasterBand(1)
    b.WriteArray(arr.astype(np.uint8))
    if nodata is not None:
        b.SetNoDataValue(int(nodata))
    b.FlushCache()
    out.FlushCache()
    out = None

def write_csv(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)

def main():
    os.makedirs(MASK_DIR, exist_ok=True)
    missing = [os.path.join(INPUT_DIR, fn) for fn in RASTER_FILES.values()
               if not os.path.isfile(os.path.join(INPUT_DIR, fn))]
    if missing:
        raise RuntimeError("缺少必需输入文件：\n" + "\n".join(missing))

    datasets, arrays, infos = {}, {}, {}
    try:
        for key, fn in RASTER_FILES.items():
            ds, arr, info = read_raster(os.path.join(INPUT_DIR, fn))
            datasets[key], arrays[key], infos[key] = ds, arr, info

        ref_ds = datasets["B04"]
        ref_info = infos["B04"]
        for key in RASTER_FILES:
            if not same_grid(ref_info, infos[key]):
                raise RuntimeError(
                    "栅格网格不一致: B04 与 " + key +
                    " 的尺寸/仿射变换/坐标系不一致。请先对齐数据，脚本已停止，避免错位标注。"
                )

        cufr_path = find_cufr_file()
        if not cufr_path:
            raise RuntimeError(
                "找不到 CN01 CUFR GeoJSON 边界。请将 CN01_CUFR_circle_UTM.geojson "
                "或 CN01_CUFR_circle_WGS84.geojson 放入 " + INPUT_DIR
            )
        cufr = rasterize_cufr(cufr_path, ref_ds)
        ndvi = arrays["NDVI"].astype(np.float32)
        ndbi = arrays["NDBI"].astype(np.float32)
        ndwi = arrays["NDWI"].astype(np.float32)
        scl = arrays["SCL"]
        b04 = arrays["B04"].astype(np.float32)
        b08 = arrays["B08"].astype(np.float32)
        b11 = arrays["B11"].astype(np.float32)

        # Scale integer indices if stored as scaled integers (e.g. 10000).
        if np.nanpercentile(np.abs(ndvi), 99) > 2.0:
            ndvi = ndvi / 10000.0
        if np.nanpercentile(np.abs(ndbi), 99) > 2.0:
            ndbi = ndbi / 10000.0
        if np.nanpercentile(np.abs(ndwi), 99) > 2.0:
            ndwi = ndwi / 10000.0

        valid = np.isfinite(ndvi) & np.isfinite(ndbi) & np.isfinite(ndwi)
        for key, arr in [("NDVI", arrays["NDVI"]), ("NDBI", arrays["NDBI"]), ("NDWI", arrays["NDWI"])]:
            nd = infos[key]["nodata"]
            if nd is not None:
                valid &= (arr != nd)
        # A finite SCL code must be within the usual SCL code range.
        valid &= np.isfinite(scl) & (scl >= 0) & (scl <= 11)
        inside = cufr & valid
        ignore = inside & np.isin(scl, list(IGNORE_SCL))
        clear = inside & (~np.isin(scl, list(IGNORE_SCL)))

        # Candidate masks for visual review. These are not all promoted to semantic labels.
        water_cand = clear & (scl == 6)
        veg3_cand = clear & (scl == 4) & (ndvi >= 0.55)
        veg4_cand = clear & (scl == 4) & (ndvi >= 0.25) & (ndvi < 0.55)
        bare_cand = clear & (scl == 5) & (ndvi < 0.20) & (ndwi < 0.10)
        # Urban candidates are heuristic only; never auto-confirm high/low density.
        built_any = clear & (ndbi >= 0.08) & (ndvi < 0.30) & (scl != 6)
        built_dense_cand = built_any & (ndbi >= 0.15) & (ndvi < 0.15)
        built_sparse_cand = built_any & (~built_dense_cand) & (ndbi >= 0.08)
        # Cropland candidate deliberately broad: SCL vegetation with intermediate NDVI.
        # It is a review hint only because one-date spectra cannot prove agricultural use.
        crop_cand = clear & (scl == 4) & (ndvi >= 0.20) & (ndvi < 0.65)
        # Bright/dark bare and mining-related shapes are not assigned coal semantics automatically.
        coal_review = clear & (scl == 5) & (ndvi < 0.20) & (ndbi >= 0.08)

        # Provisional composite. High-confidence water and tentative SCL-guided cover only.
        # Everything unresolved remains 255, including built density, cropland, roads,
        # coal-specific classes 8-12 and "other" class 13.
        pre = np.full(scl.shape, 255, dtype=np.uint8)
        confidence = np.zeros(scl.shape, dtype=np.uint8)  # 0 unresolved, 1 tentative, 2 stronger
        pre[water_cand] = 6
        confidence[water_cand] = 2
        pre[veg3_cand] = 3
        confidence[veg3_cand] = 1
        pre[veg4_cand] = 4
        confidence[veg4_cand] = 1
        pre[bare_cand] = 5
        confidence[bare_cand] = 1
        # Explicit Ignore takes priority over any candidate assignment.
        pre[ignore] = 255
        confidence[ignore] = 0
        pre[~cufr] = 255
        confidence[~cufr] = 0

        out_label = os.path.join(OUT_DIR, "CoalCity40_CN01_Datong_prelabel_v1.tif")
        out_conf = os.path.join(OUT_DIR, "confidence.tif")
        write_byte_tif(ref_ds, out_label, pre, nodata=None)
        write_byte_tif(ref_ds, out_conf, confidence, nodata=None)

        candidate_arrays = {
            "class_0_high_density_built_candidate": built_dense_cand,
            "class_1_low_density_built_candidate": built_sparse_cand,
            "class_2_cropland_candidate": crop_cand,
            "class_3_tree_dense_vegetation_candidate": veg3_cand,
            "class_4_grass_sparse_vegetation_candidate": veg4_cand,
            "class_5_bare_ground_candidate": bare_cand,
            "class_6_water_candidate": water_cand,
            "coal_functional_review_candidate_not_label": coal_review,
            "ignore_candidate": ignore,
            "unresolved_inside_cufr": inside & (pre == 255) & (~ignore),
        }
        for name, mask in candidate_arrays.items():
            out_path = os.path.join(MASK_DIR, name + ".tif")
            write_byte_tif(ref_ds, out_path, np.where(mask, 1, 0).astype(np.uint8), nodata=0)

        total_cufr = int(np.count_nonzero(cufr))
        count_rows = []
        for code in range(14):
            n = int(np.count_nonzero((pre == code) & cufr))
            count_rows.append([code, CLASS_NAMES[code], n, round(n * 100 / total_cufr, 3) if total_cufr else 0,
                               round(n * 100 / 1_000_000, 4)])
        n_ignore = int(np.count_nonzero((pre == 255) & cufr))
        count_rows.append([255, CLASS_NAMES[255], n_ignore,
                           round(n_ignore * 100 / total_cufr, 3) if total_cufr else 0,
                           round(n_ignore * 100 / 1_000_000, 4)])
        write_csv(os.path.join(OUT_DIR, "prelabel_counts.csv"),
                  ["pixel_value", "class_name", "pixel_count", "percent_of_CUFR", "area_km2_at_10m"],
                  count_rows)

        review_rows = [
            [0, CLASS_NAMES[0], "候选掩膜已生成", "需根据局部建筑连续性/纹理人工确认；不能仅凭 NDBI 阈值定类"],
            [1, CLASS_NAMES[1], "候选掩膜已生成", "需人工区分低密度建成区与农田/村落/裸地混合区"],
            [2, CLASS_NAMES[2], "候选掩膜已生成", "需核对规则田块、时相和农业用途；未自动写入复合标签"],
            [3, CLASS_NAMES[3], "暂定写入复合栅格", "SCL=4 且 NDVI>=0.55；须核验林木/高密度植被"],
            [4, CLASS_NAMES[4], "暂定写入复合栅格", "SCL=4 且 0.25<=NDVI<0.55；须核验草地/稀疏植被"],
            [5, CLASS_NAMES[5], "暂定写入复合栅格", "SCL=5 且低 NDVI/NDWI；须排除矿区排土场等特殊类别"],
            [6, CLASS_NAMES[6], "暂定写入复合栅格", "SCL=6 水体候选；须核验岸线与云影混淆"],
            [7, CLASS_NAMES[7], "未自动赋类", "需按可见道路宽度、连续性和 10m 网格人工/线性特征复核"],
            [8, CLASS_NAMES[8], "未自动赋类", "需要已确认的活跃采掘证据；不得只凭裸地形态"],
            [9, CLASS_NAMES[9], "未自动赋类", "需要煤矸石/排土场辅助证据"],
            [10, CLASS_NAMES[10], "未自动赋类", "需要采煤沉陷区历史证据"],
            [11, CLASS_NAMES[11], "未自动赋类", "需要选煤厂/焦化厂/燃煤电厂等功能证据"],
            [12, CLASS_NAMES[12], "未自动赋类", "需要煤炭物流/装卸/堆场等功能证据"],
            [13, CLASS_NAMES[13], "未自动赋类", "只在明确可识别且不属于0-12时使用；不能作为模糊区域兜底"],
            [255, CLASS_NAMES[255], "显式写入", "包括云、云影、边界/混合不确定区及暂未可靠判定区域"]
        ]
        write_csv(os.path.join(OUT_DIR, "review_queue.csv"),
                  ["class_id", "class_name", "status", "review_notes"], review_rows)

        report = [
            "CoalCity-40 Datong batch pre-annotation v1",
            "Status: PROVISIONAL ONLY — NOT FINAL GROUND TRUTH",
            "Input directory: " + INPUT_DIR,
            "CUFR boundary: " + cufr_path,
            "Reference grid: {} x {}; CRS={}".format(ref_info["width"], ref_info["height"], ref_info["proj"][:120]),
            "CUFR pixels: {}".format(total_cufr),
            "Ignore SCL classes: {}".format(sorted(IGNORE_SCL)),
            "SCL=6 water candidates: {}".format(int(np.count_nonzero(water_cand))),
            "SCL=4 vegetation candidates: {}".format(int(np.count_nonzero(veg3_cand | veg4_cand))),
            "SCL=5 bare candidates: {}".format(int(np.count_nonzero(bare_cand))),
            "Built candidates (not auto-confirmed): {}".format(int(np.count_nonzero(built_any))),
            "Cropland candidates (not auto-confirmed): {}".format(int(np.count_nonzero(crop_cand))),
            "Unresolved pixels inside CUFR: {}".format(int(np.count_nonzero((pre == 255) & cufr))),
            "",
            "Limitations:",
            "- The label raster only tentatively assigns classes 3, 4, 5 and 6 where rule conditions match.",
            "- Classes 0, 1, 2, 7, 8-13 are not auto-confirmed; review masks/tasks are provided where feasible.",
            "- Coal functional classes 8-12 require independent evidence and are deliberately not auto-assigned.",
            "- NDVI thresholds are heuristic and need visual review; they do not replace expert annotation.",
            "- Ignore=255 is an explicit provisional value, not a claim that every remaining pixel is truly invalid.",
            "- Verify output alignment and inspect candidate layers before using any result as final labels."
        ]
        with open(os.path.join(OUT_DIR, "run_report.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(report))

        # Load outputs into the current QGIS project without clearing existing layers.
        project = QgsProject.instance()
        to_load = [
            (out_label, "CN01_prelabel_v1_provisional"),
            (out_conf, "CN01_prelabel_confidence"),
            (os.path.join(MASK_DIR, "class_0_high_density_built_candidate.tif"), "candidate_class_0_high_density_built"),
            (os.path.join(MASK_DIR, "class_1_low_density_built_candidate.tif"), "candidate_class_1_low_density_built"),
            (os.path.join(MASK_DIR, "class_2_cropland_candidate.tif"), "candidate_class_2_cropland"),
            (os.path.join(MASK_DIR, "class_3_tree_dense_vegetation_candidate.tif"), "candidate_class_3_vegetation"),
            (os.path.join(MASK_DIR, "class_4_grass_sparse_vegetation_candidate.tif"), "candidate_class_4_grass_sparse"),
            (os.path.join(MASK_DIR, "class_5_bare_ground_candidate.tif"), "candidate_class_5_bare"),
            (os.path.join(MASK_DIR, "class_6_water_candidate.tif"), "candidate_class_6_water"),
            (os.path.join(MASK_DIR, "coal_functional_review_candidate_not_label.tif"), "coal_functional_review_candidate_NOT_LABEL"),
            (os.path.join(MASK_DIR, "ignore_candidate.tif"), "candidate_ignore"),
        ]
        loaded_output_layers = []
        for path, name in to_load:
            for old_layer in list(project.mapLayers().values()):
                if old_layer.name() == name:
                    project.removeMapLayer(old_layer.id())
            layer = QgsRasterLayer(path, name, "gdal")
            if layer.isValid():
                project.addMapLayer(layer)
                loaded_output_layers.append(layer)

        # Make only the provisional composite visible by default.
        # Candidate layers are loaded for later inspection but remain unchecked,
        # preventing them from stacking over the RGB image.
        composite = project.mapLayersByName("CN01_prelabel_v1_provisional")
        if composite:
            layer = composite[0]
            classes = [
                QgsPalettedRasterRenderer.Class(3, QColor(20, 130, 50, 190), "3 林木/高密度植被（暂定）"),
                QgsPalettedRasterRenderer.Class(4, QColor(140, 200, 80, 190), "4 草地/稀疏植被（暂定）"),
                QgsPalettedRasterRenderer.Class(5, QColor(190, 150, 95, 190), "5 裸地（暂定）"),
                QgsPalettedRasterRenderer.Class(6, QColor(0, 100, 255, 190), "6 水体（暂定）"),
                QgsPalettedRasterRenderer.Class(255, QColor(0, 0, 0, 0), "255 Ignore/待判读（透明显示）"),
            ]
            layer.setRenderer(QgsPalettedRasterRenderer(layer.dataProvider(), 1, classes))
            root = project.layerTreeRoot()
            for lyr in project.mapLayers().values():
                node = root.findLayer(lyr.id())
                if node is None:
                    continue
                if lyr.name() == "CN01_prelabel_v1_provisional":
                    node.setItemVisibilityChecked(True)
                elif lyr.name() in ("CN01_RGB_true_color_B04_B03_B02",):
                    node.setItemVisibilityChecked(True)
                elif lyr.name() in (
                    "CN01_prelabel_confidence", "candidate_class_0_high_density_built",
                    "candidate_class_1_low_density_built", "candidate_class_2_cropland",
                    "candidate_class_3_vegetation", "candidate_class_4_grass_sparse",
                    "candidate_class_5_bare", "candidate_class_6_water",
                    "coal_functional_review_candidate_NOT_LABEL", "candidate_ignore",
                    "CN01_water_candidate_v2_SCL6", "SCL_class6_water", "NDWI_only_suspect",
                    "SCL_ignore_classes", "SCL_nodata_defect_classes0_1",
                    "SCL_cloud_cirrus_classes8_9_10", "SCL_cloud_shadow_class3",
                    "CN01_water_candidate", "CN01_ignore_candidate_v2_SCL",
                    "CN01_ignore_candidate", "CN01_bare_candidate", "CN01_built_candidate",
                    "CN01_vegetation_candidate", "CN01_ignore_candidate"
                ):
                    node.setItemVisibilityChecked(False)
                elif lyr in loaded_output_layers and lyr.name() != "CN01_prelabel_v1_provisional":
                    node.setItemVisibilityChecked(False)
            layer.triggerRepaint()
            if project.fileName():
                project.write()

        log("批量预标注完成。")
        log("输出目录: " + OUT_DIR)
        log("复合预标注栅格: " + out_label)
        log("候选类别掩膜数量: " + str(len(candidate_arrays)))
        log("请查看 run_report.txt、prelabel_counts.csv、review_queue.csv。")
        log("注意：这是预标注草稿，不是可直接提交的最终标签。")

    finally:
        for ds in datasets.values():
            try:
                ds = None
            except Exception:
                pass

try:
    main()
except Exception:
    log(traceback.format_exc())

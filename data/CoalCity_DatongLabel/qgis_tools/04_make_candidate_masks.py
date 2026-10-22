# -*- coding: utf-8 -*-
"""
CoalCity-40 Datong candidate masks from NDVI/NDBI/NDWI/SCL.
This creates review-only candidate layers. It does NOT write final semantic labels.

Run in QGIS Python Console:
exec(open(r"D:\CoalCity\qgis_tools\04_make_candidate_masks.py", encoding="utf-8").read())
"""
import os
import traceback
import numpy as np
from osgeo import gdal, ogr, osr
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer

INPUT_DIR = r"D:\CoalCity\input\CN01_Datong"
OUTPUT_DIR = r"D:\CoalCity\output\candidate_masks"

NDVI_PATH = os.path.join(INPUT_DIR, "CN01_NDVI.tif")
NDBI_PATH = os.path.join(INPUT_DIR, "CN01_NDBI.tif")
NDWI_PATH = os.path.join(INPUT_DIR, "CN01_NDWI.tif")
SCL_PATH  = os.path.join(INPUT_DIR, "CN01_SCL.tif")

IGNORE_TIF = os.path.join(OUTPUT_DIR, "CN01_ignore_candidate.tif")
VEG_TIF    = os.path.join(OUTPUT_DIR, "CN01_vegetation_candidate.tif")
WATER_TIF  = os.path.join(OUTPUT_DIR, "CN01_water_candidate.tif")
BUILT_TIF  = os.path.join(OUTPUT_DIR, "CN01_built_candidate.tif")
BARE_TIF   = os.path.join(OUTPUT_DIR, "CN01_bare_candidate.tif")
IGNORE_GPKG= os.path.join(OUTPUT_DIR, "CN01_ignore_candidate.gpkg")

# Sentinel-2 Scene Classification Layer classes to ignore for review:
# 0 No data, 1 Saturated/defective, 3 Cloud shadow,
# 8 Cloud medium probability, 9 Cloud high probability,
# 10 Thin cirrus, 11 Snow/ice
IGNORE_SCL = {0, 1, 3, 8, 9, 10, 11}

def log(msg):
    print("[CoalCity-Candidates] " + str(msg))

def read_array(path):
    ds = gdal.Open(path, gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError("无法读取文件: " + path)
    arr = ds.GetRasterBand(1).ReadAsArray()
    gt = ds.GetGeoTransform()
    prj = ds.GetProjection()
    nodata = ds.GetRasterBand(1).GetNoDataValue()
    return ds, arr, gt, prj, nodata

def write_mask(reference_ds, out_path, arr, nodata=0, dtype=gdal.GDT_Byte):
    driver = gdal.GetDriverByName("GTiff")
    if os.path.exists(out_path):
        driver.Delete(out_path)
    out = driver.Create(
        out_path,
        reference_ds.RasterXSize,
        reference_ds.RasterYSize,
        1,
        dtype,
        options=["COMPRESS=LZW", "TILED=YES"]
    )
    out.SetGeoTransform(reference_ds.GetGeoTransform())
    out.SetProjection(reference_ds.GetProjection())
    band = out.GetRasterBand(1)
    band.WriteArray(arr)
    band.SetNoDataValue(nodata)
    band.FlushCache()
    out.FlushCache()
    out = None

def polygonize_mask(mask_tif, gpkg_path, layer_name):
    src = gdal.Open(mask_tif)
    srcband = src.GetRasterBand(1)

    drv = ogr.GetDriverByName("GPKG")
    if os.path.exists(gpkg_path):
        drv.DeleteDataSource(gpkg_path)
    ds = drv.CreateDataSource(gpkg_path)
    srs = osr.SpatialReference()
    prj = src.GetProjection()
    if prj:
        srs.ImportFromWkt(prj)
    layer = ds.CreateLayer(layer_name, srs=srs, geom_type=ogr.wkbMultiPolygon)
    fd = ogr.FieldDefn("value", ogr.OFTInteger)
    layer.CreateField(fd)

    gdal.Polygonize(srcband, None, layer, 0, [], callback=None)

    # Remove polygons where value == 0 (background).
    layer.ResetReading()
    delete_ids = []
    for feat in layer:
        if feat.GetField("value") == 0:
            delete_ids.append(feat.GetFID())
    for fid in delete_ids:
        layer.DeleteFeature(fid)

    ds = None
    src = None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ndvi_ds, ndvi, gt, prj, ndvi_nodata = read_array(NDVI_PATH)
    _, ndbi, _, _, ndbi_nodata = read_array(NDBI_PATH)
    _, ndwi, _, _, ndwi_nodata = read_array(NDWI_PATH)
    _, scl,  _, _, scl_nodata  = read_array(SCL_PATH)

    if not (ndvi.shape == ndbi.shape == ndwi.shape == scl.shape):
        raise RuntimeError("NDVI/NDBI/NDWI/SCL 栅格尺寸不一致。")

    # Valid pixels: finite + not nodata + not ignored SCL.
    valid = np.isfinite(ndvi) & np.isfinite(ndbi) & np.isfinite(ndwi)
    if ndvi_nodata is not None:
        valid &= (ndvi != ndvi_nodata)
    if ndbi_nodata is not None:
        valid &= (ndbi != ndbi_nodata)
    if ndwi_nodata is not None:
        valid &= (ndwi != ndwi_nodata)
    if scl_nodata is not None:
        valid &= (scl != scl_nodata)

    ignore = np.isin(scl, list(IGNORE_SCL))
    valid &= ~ignore

    # Candidate rules (review only; tune after visual inspection).
    water = valid & (((scl == 6)) | ((ndwi >= 0.12) & (ndvi < 0.20)))
    vegetation = valid & (ndvi >= 0.35) & (~water)
    built = valid & (ndbi >= 0.08) & (ndvi < 0.30) & (ndwi < 0.10) & (~water)
    bare = valid & (ndvi < 0.20) & (ndwi < 0.00) & (ndbi < 0.08) & (~water) & (~built)

    ignore_u8 = np.where(ignore, 255, 0).astype(np.uint8)
    veg_u8    = np.where(vegetation, 1, 0).astype(np.uint8)
    water_u8  = np.where(water, 1, 0).astype(np.uint8)
    built_u8  = np.where(built, 1, 0).astype(np.uint8)
    bare_u8   = np.where(bare, 1, 0).astype(np.uint8)

    write_mask(ndvi_ds, IGNORE_TIF, ignore_u8, nodata=0)
    write_mask(ndvi_ds, VEG_TIF, veg_u8, nodata=0)
    write_mask(ndvi_ds, WATER_TIF, water_u8, nodata=0)
    write_mask(ndvi_ds, BUILT_TIF, built_u8, nodata=0)
    write_mask(ndvi_ds, BARE_TIF, bare_u8, nodata=0)

    polygonize_mask(IGNORE_TIF, IGNORE_GPKG, "ignore_candidate")

    # Load layers into current QGIS project for review.
    project = QgsProject.instance()
    for path, name in [
        (IGNORE_TIF, "CN01_ignore_candidate"),
        (VEG_TIF, "CN01_vegetation_candidate"),
        (WATER_TIF, "CN01_water_candidate"),
        (BUILT_TIF, "CN01_built_candidate"),
        (BARE_TIF, "CN01_bare_candidate"),
    ]:
        lyr = QgsRasterLayer(path, name)
        if lyr.isValid():
            project.addMapLayer(lyr)

    vlyr = QgsVectorLayer(IGNORE_GPKG + "|layername=ignore_candidate", "ignore_candidate_polygons", "ogr")
    if vlyr.isValid():
        project.addMapLayer(vlyr)

    # Save project if already set.
    if project.fileName():
        project.write()

    total = ndvi.size
    valid_n = int(np.count_nonzero(valid))
    stats = {
        "ignore_pixels": int(np.count_nonzero(ignore)),
        "water_pixels": int(np.count_nonzero(water)),
        "vegetation_pixels": int(np.count_nonzero(vegetation)),
        "built_pixels": int(np.count_nonzero(built)),
        "bare_pixels": int(np.count_nonzero(bare)),
        "valid_pixels": valid_n,
        "total_pixels": int(total),
    }

    log("候选层已生成。")
    for k, v in stats.items():
        log(f"{k}: {v}")
    log("输出目录: " + OUTPUT_DIR)
    log("说明：这些只是候选区域，不能直接当成最终标签。")
    log("建议先检查 ignore、水体、植被三类是否合理，再决定是否继续自动转为复核草稿。")

try:
    main()
except Exception:
    log(traceback.format_exc())

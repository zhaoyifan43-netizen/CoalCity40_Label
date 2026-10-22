# -*- coding: utf-8 -*-
"""
CoalCity-40 | CN01 Datong batch pre-annotation v2.3
Windows + QGIS Python Console; writes to a NEW v2 folder and preserves v1.

Run in QGIS Python Console:
exec(open(r"D:\CoalCity\qgis_tools\12_auto_prelabel_datong_v2_3.py", encoding="utf-8").read())

Required rasters in D:\CoalCity\input\CN01_Datong:
  CN01_B02.tif, CN01_B03.tif, CN01_B04.tif, CN01_B08.tif, CN01_B11.tif,
  CN01_NDVI.tif, CN01_NDBI.tif, CN01_NDWI.tif, CN01_SCL.tif
  plus CN01_CUFR_circle_UTM.geojson or CN01_CUFR_circle_WGS84.geojson.

Coal-specific automatic confirmation:
  The annotation specification requires independent functional evidence for classes 8-12.
  Put evidence polygons in:
    D:\CoalCity\input\CN01_Datong\evidence\
  with exact filenames:
    class8_active_mining.geojson
    class9_waste_dump.geojson
    class10_subsidence_water.geojson
    class11_coal_processing_power.geojson
    class12_coal_logistics.geojson
  These polygons must be independently verified evidence. Where present, the script rasterizes
  them to the imagery grid and assigns the corresponding class with confidence=3.
  If no evidence file exists, classes 8-12 are only candidate masks/review tasks; the script
  will NOT invent a coal-function label from spectral appearance alone.

Outputs in D:\CoalCity\output\CoalCity40_CN01_Datong_prelabel_v2_3\
  CoalCity40_CN01_Datong_prelabel_v2_3.tif
  confidence.tif
  candidate_masks\class_*.tif
  prelabel_counts_v2_3.csv
  candidate_counts_v2_3.csv
  review_queue_v2_3.csv
  conflict_report_v2_3.csv
  run_report_v2_3.txt

Label raster:
  0-13 = provisional class IDs per annotation spec
  255 = Ignore / uncertain / review required
Confidence:
  0 = unresolved/review
  1 = heuristic provisional
  2 = stronger multi-condition generic class
  3 = assigned from supplied independently verified coal evidence polygon
  4 = facility-function evidence + image-derived class-11 candidate; automated prelabel, not human verified
"""
import os, csv, traceback
import numpy as np
from osgeo import gdal, ogr, osr
from qgis.core import QgsProject, QgsRasterLayer, QgsPalettedRasterRenderer
from qgis.PyQt.QtGui import QColor

try:
    from scipy import ndimage as ndi
    HAVE_SCIPY = True
except Exception:
    ndi = None
    HAVE_SCIPY = False

INPUT_DIR = r"D:\CoalCity\input\CN01_Datong"
EVIDENCE_DIR = os.path.join(INPUT_DIR, "evidence")
OUT_DIR = r"D:\CoalCity\output\CoalCity40_CN01_Datong_prelabel_v2_3"
MASK_DIR = os.path.join(OUT_DIR, "candidate_masks")
RASTER_FILES = {
    "B02": "CN01_B02.tif", "B03": "CN01_B03.tif",
    "B04": "CN01_B04.tif", "B08": "CN01_B08.tif",
    "B11": "CN01_B11.tif", "NDVI": "CN01_NDVI.tif",
    "NDBI": "CN01_NDBI.tif", "NDWI": "CN01_NDWI.tif",
    "SCL": "CN01_SCL.tif",
}
IGNORE_SCL = {0, 1, 3, 8, 9, 10, 11}
CLASS_NAMES = {
    0:"高密度建成区", 1:"低密度建成区", 2:"农田",
    3:"林木或高密度植被", 4:"草地或稀疏植被", 5:"裸地",
    6:"水体", 7:"道路", 8:"可观测活跃采掘区",
    9:"煤矿废弃物堆场或排土场", 10:"采煤沉陷水体",
    11:"煤炭加工与电力设施", 12:"煤炭物流基础设施",
    13:"其他", 255:"Ignore/待判读"
}
# Facilities extracted from the user's library survey for CN01 Datong.
# Coordinates are context locators, not verified semantic boundaries.
DATONG_FACILITIES = [
    ("Tongxin Coal Mine", 40.013182, 113.103349, 8, "GEM exact", "2023 operating"),
    ("Zhongmei Tashan Coal Mine", 39.950913, 113.086860, 8, "OSM-village checked; not GEM exact", "2023 operating"),
    ("Yungang Mine", 40.119770, 113.079910, 8, "OSM industrial parcel", "2023 operating"),
    ("Jinhua Gong Mine", 40.099630, 113.152520, 8, "OSM industrial parcel", "2023 operating"),
    ("Meiyukou Mine", 40.030580, 113.131360, 8, "OSM industrial parcel", "2023 operating"),
    ("Xinzhouyao Mine", 40.046710, 113.117600, 8, "OSM station vicinity", "closed 2023-04; image date matters"),
    ("Tashan Baidong Shaft", 40.000860, 113.055660, 8, "OSM station vicinity", "2023 operating"),
    ("Datong No.2 Power Plant", 40.028160, 113.294170, 11, "OSM industrial parcel", "2023 operating"),
    ("Tongmei Datang Tashan Mine", 39.924229, 113.070254, 8, "GEM exact; outside 20km CUFR by survey", "2023 operating"),
    ("Tashan Power Plant Phase I", 39.925200, 113.081900, 11, "OSM industrial parcel; outside 20km CUFR by survey", "2023 operating"),
    ("Sujin Tashan Power Plant Phase II", 39.924970, 113.085630, 11, "OSM industrial parcel; outside 20km CUFR by survey", "2023 operating"),
]
EVIDENCE_FILES = {
    8: ("class8_active_mining.geojson", "可观测活跃采掘区"),
    9: ("class9_waste_dump.geojson", "煤矿废弃物堆场或排土场"),
    10: ("class10_subsidence_water.geojson", "采煤沉陷水体"),
    11: ("class11_coal_processing_power.geojson", "煤炭加工与电力设施"),
    12: ("class12_coal_logistics.geojson", "煤炭物流基础设施"),
}
MIN_COMPONENT_PIXELS = 9  # 9 pixels = 900 m² at 10 m resolution; tiny patches go to review.
NEIGHBORHOOD_SIZE = 5

def log(s):
    print("[CoalCity-AutoPrelabel-v2.3] " + str(s))

def read_raster(path):
    ds = gdal.Open(path, gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError("无法读取栅格: " + path)
    b = ds.GetRasterBand(1)
    arr = b.ReadAsArray()
    if arr is None:
        raise RuntimeError("无法读取像素数组: " + path)
    info = {"path":path, "gt":ds.GetGeoTransform(), "proj":ds.GetProjection(),
            "width":ds.RasterXSize, "height":ds.RasterYSize, "nodata":b.GetNoDataValue()}
    return ds, arr, info

def same_grid(a, b):
    if a["width"] != b["width"] or a["height"] != b["height"] or a["gt"] != b["gt"]:
        return False
    sa, sb = osr.SpatialReference(), osr.SpatialReference()
    try:
        sa.ImportFromWkt(a["proj"]); sb.ImportFromWkt(b["proj"])
        return bool(sa.IsSame(sb))
    except Exception:
        return a["proj"] == b["proj"]

def find_boundary():
    names = ["CN01_CUFR_circle_UTM.geojson", "CN01_CUFR_circle_WGS84.geojson"]
    for root in [INPUT_DIR, r"D:\CoalCity\input"]:
        for n in names:
            p = os.path.join(root, n)
            if os.path.isfile(p):
                return p
    raise RuntimeError("找不到 CUFR 边界 GeoJSON，请放入 " + INPUT_DIR)

def rasterize_vector(path, ref_ds):
    src = ogr.Open(path, 0)
    if src is None:
        raise RuntimeError("无法打开矢量证据: " + path)
    src_layer = src.GetLayer(0)
    src_srs = src_layer.GetSpatialRef()
    if src_srs is None:
        raise RuntimeError("矢量文件缺少坐标系: " + path)
    target_srs = osr.SpatialReference()
    target_srs.ImportFromWkt(ref_ds.GetProjection())
    transform = None if src_srs.IsSame(target_srs) else osr.CoordinateTransformation(src_srs, target_srs)
    mem_drv = ogr.GetDriverByName("Memory")
    mem_vec = mem_drv.CreateDataSource("vector_mem")
    mem_layer = mem_vec.CreateLayer("evidence", srs=target_srs, geom_type=ogr.wkbUnknown)
    src_layer.ResetReading()
    for feat in src_layer:
        geom = feat.GetGeometryRef()
        if geom is None: continue
        g = geom.Clone()
        if transform is not None: g.Transform(transform)
        out_feat = ogr.Feature(mem_layer.GetLayerDefn())
        out_feat.SetGeometry(g); mem_layer.CreateFeature(out_feat)
        out_feat = None; g = None
    mem_r = gdal.GetDriverByName("MEM").Create("", ref_ds.RasterXSize, ref_ds.RasterYSize, 1, gdal.GDT_Byte)
    mem_r.SetGeoTransform(ref_ds.GetGeoTransform()); mem_r.SetProjection(ref_ds.GetProjection())
    mem_r.GetRasterBand(1).Fill(0)
    gdal.RasterizeLayer(mem_r, [1], mem_layer, burn_values=[1], options=["ALL_TOUCHED=TRUE"])
    arr = mem_r.GetRasterBand(1).ReadAsArray().astype(bool)
    src = None; mem_vec = None; mem_r = None
    return arr

def facility_context_masks(ref_ds, inside, out_dir):
    """Build facility locator review masks; never burn point buffers into semantic labels."""
    gt = ref_ds.GetGeoTransform()
    target = osr.SpatialReference(); target.ImportFromWkt(ref_ds.GetProjection())
    wgs = osr.SpatialReference(); wgs.ImportFromEPSG(4326)
    transform = osr.CoordinateTransformation(wgs, target)
    h, w = inside.shape
    union = np.zeros((h,w), dtype=bool)
    class_masks = {8:np.zeros((h,w),bool), 11:np.zeros((h,w),bool), 12:np.zeros((h,w),bool)}
    rows = []
    radius_m = 1200.0  # search/review radius only, not an output label boundary
    for name, lat, lon, hint, grade, status in DATONG_FACILITIES:
        p = ogr.Geometry(ogr.wkbPoint); p.AddPoint(float(lon), float(lat)); p.Transform(transform)
        px = int((p.GetX()-gt[0])/gt[1]); py = int((p.GetY()-gt[3])/gt[5])
        if 0 <= px < w and 0 <= py < h:
            rx = max(1,int(radius_m/max(abs(gt[1]),1))); ry = max(1,int(radius_m/max(abs(gt[5]),1)))
            y0,y1=max(0,py-ry),min(h,py+ry+1); x0,x1=max(0,px-rx),min(w,px+rx+1)
            ly,lx=np.ogrid[y0:y1,x0:x1]
            local=(((lx-px)*gt[1])**2+((ly-py)*gt[5])**2 <= radius_m**2)
            local &= inside[y0:y1,x0:x1]
            union[y0:y1,x0:x1] |= local
            if hint in class_masks: class_masks[hint][y0:y1,x0:x1] |= local
        else:
            px,py="",""
        rows.append([name,lat,lon,hint,grade,status,px,py,
                     "locator buffer only; image-visible boundary required"])
    write_csv(os.path.join(out_dir,"facility_context_v2_3.csv"),
              ["facility","latitude_wgs84","longitude_wgs84","class_hint","coordinate_grade","status_2023","pixel_x","pixel_y","limitation"],rows)
    return union,class_masks

def facility_supported_class11_mask(ref_ds, inside, clear, ignore, class11_candidate, evidence_conflicts, out_dir):
    """Conservative class-11 auto-assignment: known coal-power facility + image-visible built candidate.

    The facility point supplies functional identity; spectral/local built candidate supplies
    image-visible pixels. A limited 250 m search window is NOT itself burned into labels.
    This is automated evidence-supported prelabeling (confidence=4), not human verification.
    """
    gt = ref_ds.GetGeoTransform()
    target = osr.SpatialReference(); target.ImportFromWkt(ref_ds.GetProjection())
    wgs = osr.SpatialReference(); wgs.ImportFromEPSG(4326)
    transform = osr.CoordinateTransformation(wgs, target)
    h, w = inside.shape
    result = np.zeros((h, w), dtype=bool)
    rows = []
    radius_m = 250.0
    for name, lat, lon, hint, grade, status in DATONG_FACILITIES:
        if hint != 11:
            continue
        p = ogr.Geometry(ogr.wkbPoint); p.AddPoint(float(lon), float(lat)); p.Transform(transform)
        px = int((p.GetX()-gt[0])/gt[1]); py = int((p.GetY()-gt[3])/gt[5])
        if not (0 <= px < w and 0 <= py < h) or not inside[py, px]:
            rows.append([name, lat, lon, grade, status, "outside CUFR or raster", 0,
                         "No class-11 assignment; facility is not within this CUFR grid"])
            continue
        rx = max(1, int(radius_m / max(abs(gt[1]), 1)))
        ry = max(1, int(radius_m / max(abs(gt[5]), 1)))
        y0, y1 = max(0, py-ry), min(h, py+ry+1)
        x0, x1 = max(0, px-rx), min(w, px+rx+1)
        yy, xx = np.ogrid[y0:y1, x0:x1]
        circle = (((xx-px)*gt[1])**2 + ((yy-py)*gt[5])**2 <= radius_m**2)
        local = circle & inside[y0:y1, x0:x1] & clear[y0:y1, x0:x1]
        local &= (~ignore[y0:y1, x0:x1]) & class11_candidate[y0:y1, x0:x1]
        local &= (~evidence_conflicts[y0:y1, x0:x1])
        result[y0:y1, x0:x1] |= local
        rows.append([name, lat, lon, grade, status, "inside CUFR", int(np.count_nonzero(local)),
                     "Class 11 assigned only to image-derived built/industrial candidate pixels within 250 m; inspect boundary"])
    write_csv(os.path.join(out_dir, "coal_facility_auto_assignment_v2_3.csv"),
              ["facility", "latitude_wgs84", "longitude_wgs84", "coordinate_grade", "status_2023",
               "location_status", "assigned_candidate_pixels", "decision_note"], rows)
    return result

def write_tif(ref_ds, path, arr, dtype=gdal.GDT_Byte, nodata=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    drv = gdal.GetDriverByName("GTiff")
    if os.path.exists(path): drv.Delete(path)
    out = drv.Create(path, ref_ds.RasterXSize, ref_ds.RasterYSize, 1, dtype,
                     options=["COMPRESS=LZW", "TILED=YES"])
    if out is None: raise RuntimeError("无法创建输出: " + path)
    out.SetGeoTransform(ref_ds.GetGeoTransform()); out.SetProjection(ref_ds.GetProjection())
    b = out.GetRasterBand(1); b.WriteArray(arr)
    if nodata is not None: b.SetNoDataValue(nodata)
    b.FlushCache(); out.FlushCache(); out = None

def write_csv(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(headers); w.writerows(rows)

def scaled_index(arr):
    x = arr.astype(np.float32)
    good = np.isfinite(x)
    if np.any(good) and np.nanpercentile(np.abs(x[good]), 99) > 2.0:
        x = x / 10000.0
    return x

def local_fraction(mask, size=5):
    if HAVE_SCIPY:
        return ndi.uniform_filter(mask.astype(np.float32), size=size, mode="nearest")
    # Fast deterministic fallback; if scipy is absent, use integral image.
    x = mask.astype(np.float32)
    pad = size // 2
    x = np.pad(x, ((pad,pad),(pad,pad)), mode="edge")
    integ = np.pad(x, ((1,0),(1,0)), mode="constant").cumsum(0).cumsum(1)
    sums = integ[size:,size:] - integ[:-size,size:] - integ[size:,:-size] + integ[:-size,:-size]
    return sums / float(size*size)

def remove_small_components(mask, min_pixels=MIN_COMPONENT_PIXELS):
    if not HAVE_SCIPY:
        return mask.copy(), np.zeros(mask.shape, dtype=bool), "scipy unavailable; component filtering skipped"
    labels, n = ndi.label(mask, structure=np.ones((3,3), dtype=np.uint8))
    if n == 0: return mask.copy(), np.zeros(mask.shape, dtype=bool), "no components"
    counts = np.bincount(labels.ravel())
    keep = counts >= min_pixels
    keep[0] = False
    cleaned = keep[labels]
    removed = mask & (~cleaned)
    return cleaned, removed, "removed components smaller than {} pixels".format(min_pixels)

def save_mask(ref_ds, name, mask):
    path = os.path.join(MASK_DIR, name + ".tif")
    write_tif(ref_ds, path, mask.astype(np.uint8))
    return path

def main():
    os.makedirs(MASK_DIR, exist_ok=True)
    missing = [os.path.join(INPUT_DIR, f) for f in RASTER_FILES.values()
               if not os.path.isfile(os.path.join(INPUT_DIR, f))]
    if missing:
        raise RuntimeError("缺少输入文件：\n" + "\n".join(missing))
    dss, arrs, infos = {}, {}, {}
    try:
        for k, fn in RASTER_FILES.items():
            dss[k], arrs[k], infos[k] = read_raster(os.path.join(INPUT_DIR, fn))
        ref = dss["B04"]; refinfo = infos["B04"]
        for k in RASTER_FILES:
            if not same_grid(refinfo, infos[k]):
                raise RuntimeError("栅格网格不一致：B04 与 {} 不匹配。为避免错位，已停止。".format(k))

        boundary_path = find_boundary()
        inside = rasterize_vector(boundary_path, ref)
        ndvi, ndbi, ndwi = (scaled_index(arrs[k]) for k in ("NDVI","NDBI","NDWI"))
        b02, b03, b04, b08, b11 = (arrs[k].astype(np.float32) for k in ("B02","B03","B04","B08","B11"))
        scl = arrs["SCL"].astype(np.int16)

        valid = np.isfinite(ndvi) & np.isfinite(ndbi) & np.isfinite(ndwi) & np.isin(scl, np.arange(0,12))
        for k in ("NDVI","NDBI","NDWI"):
            nd = infos[k]["nodata"]
            if nd is not None: valid &= (arrs[k] != nd)
        inside &= valid
        ignore = inside & np.isin(scl, list(IGNORE_SCL))
        clear = inside & (~ignore)

        facility_context, facility_class_context = facility_context_masks(ref, inside, OUT_DIR)

        # General land-cover candidates, multi-condition and spatially regularized.
        water_raw = clear & (scl == 6) & (ndwi > -0.15)
        water, water_small, water_msg = remove_small_components(water_raw, 4)

        veg_scl = clear & (scl == 4)
        veg_fraction = local_fraction(veg_scl, NEIGHBORHOOD_SIZE)
        ndvi_fraction = local_fraction(veg_scl & (ndvi >= 0.45), NEIGHBORHOOD_SIZE)
        # High confidence tree/dense vegetation requires strong NDVI and locally coherent SCL vegetation.
        tree_raw = veg_scl & (ndvi >= 0.62) & (ndvi_fraction >= 0.55)
        tree, tree_small, tree_msg = remove_small_components(tree_raw)
        # Sparse/herbaceous vegetation remains a candidate unless local cover is coherent.
        grass_raw = veg_scl & (ndvi >= 0.25) & (ndvi < 0.62) & (veg_fraction >= 0.55)
        grass, grass_small, grass_msg = remove_small_components(grass_raw)
        veg_uncertain = veg_scl & (~tree) & (~grass)

        # Bare ground: strict composite label only for low vegetation, low water index,
        # low NDBI and SCL bare. Potential industrial/mining bare surfaces remain review candidates.
        bare_raw = clear & (scl == 5) & (ndvi < 0.12) & (ndwi < 0.0) & (ndbi < 0.05)
        bare, bare_small, bare_msg = remove_small_components(bare_raw)
        bare_broad = clear & (scl == 5) & (ndvi < 0.20) & (ndwi < 0.10)
        bare_uncertain = bare_broad & (~bare)

        # Built-up: heuristic candidate + local density consistency; do not treat NDBI alone as proof.
        built_seed = clear & (ndbi >= 0.08) & (ndvi < 0.30) & (scl != 6)
        built_fraction = local_fraction(built_seed, NEIGHBORHOOD_SIZE)
        dense_built = built_seed & (built_fraction >= 0.65)
        sparse_built = built_seed & (built_fraction >= 0.25) & (built_fraction < 0.65)
        built_uncertain = built_seed & (built_fraction < 0.25)
        dense_built, dense_small, dense_msg = remove_small_components(dense_built)
        sparse_built, sparse_small, sparse_msg = remove_small_components(sparse_built)

        # Cropland candidate: coherent SCL vegetation fields; spectral values alone cannot prove agriculture.
        # Cropland remains review-only. Require coherent larger patches to reduce
        # the tendency to label all vegetation as agriculture.
        crop_raw = veg_scl & (ndvi >= 0.20) & (ndvi < 0.70) & (veg_fraction >= 0.70)
        crop, crop_small, crop_msg = remove_small_components(crop_raw, 50)

        # Road candidates: linear-ish components extracted from non-vegetated built/bright surfaces.
        # This is only a review layer; not automatically written as class 7.
        road_seed = clear & (ndvi < 0.25) & (ndbi >= 0.00) & (scl != 6) & (~ignore)
        road_local = local_fraction(road_seed, 3)
        road_raw = road_seed & (road_local >= 0.18) & (road_local <= 0.75)
        road, road_small, road_msg = remove_small_components(road_raw, 12)

        # Coal-function candidates are conservative hints, not semantic confirmation.
        # Actual class IDs 8-12 are assigned only where verified evidence polygons exist.
        # Coal-function masks are conservative investigation candidates only.
        # They are not semantic labels; no class 8-12 assignment occurs without
        # independently verified evidence polygons.
        class8_candidate = clear & (scl == 5) & (ndvi < 0.15) & (ndwi < 0.05) & (ndbi >= 0.08)
        class9_candidate = clear & (scl == 5) & (ndvi < 0.15) & (ndwi < 0.10) & (ndbi >= 0.02) & (local_fraction(bare_broad, 5) >= 0.55)
        class10_candidate = water.copy()  # possible water only; subsidence function is unconfirmed
        class11_candidate = clear & (dense_built | (sparse_built & (built_fraction >= 0.40))) & (ndvi < 0.25)
        class12_candidate = clear & (road | (dense_built & (ndvi < 0.20)))

        # Known-facility context raises review priority only; it is not enough to confirm function.
        class8_candidate |= facility_class_context[8] & clear & (scl == 5) & (ndvi < 0.25)
        class9_candidate |= facility_context & clear & (scl == 5) & (ndvi < 0.20)
        class11_candidate |= facility_class_context[11] & clear & (built_seed | (scl == 5)) & (ndvi < 0.35)
        class12_candidate |= facility_context & clear & (road | built_seed) & (ndvi < 0.35)
        # Conflict mask: pixels hit by two or more competing generic candidate families.
        # Conflicts are counted only among masks eligible to assign provisional labels.
        # Broad bare-ground review areas, cropland, roads and coal-function hints are
        # review-only layers and must not erase otherwise valid labels.
        families = np.stack([
            water, tree, grass, bare, dense_built, sparse_built
        ], axis=0)
        conflict = np.sum(families, axis=0) >= 2

        # Rasterize independent functional evidence polygons when present.
        evidence_masks = {}
        evidence_files_used = {}
        for cid, (fn, desc) in EVIDENCE_FILES.items():
            p = os.path.join(EVIDENCE_DIR, fn)
            if os.path.isfile(p):
                evidence_masks[cid] = rasterize_vector(p, ref) & inside
                evidence_files_used[cid] = p
            else:
                evidence_masks[cid] = np.zeros(scl.shape, dtype=bool)

        # Composite provisional raster: 255 = review/Ignore. Never force uncertain bare/vegetation into a class.
        labels = np.full(scl.shape, 255, dtype=np.uint8)
        conf = np.zeros(scl.shape, dtype=np.uint8)
        # Only confident generic classes are assigned automatically.
        labels[water] = 6; conf[water] = 2
        labels[tree] = 3; conf[tree] = 2
        labels[grass] = 4; conf[grass] = 1
        labels[bare] = 5; conf[bare] = 2
        # Built classes are tentative because local NDBI density is not a definitive building classifier.
        labels[dense_built] = 0; conf[dense_built] = 1
        labels[sparse_built] = 1; conf[sparse_built] = 1
        # Candidate conflicts revert to review unless an evidence polygon assigns coal category.
        labels[conflict] = 255; conf[conflict] = 0
        # SCL Ignore and pixels outside CUFR always remain 255.
        labels[ignore] = 255; conf[ignore] = 0
        labels[~inside] = 255; conf[~inside] = 0

        # Evidence-backed coal labels take precedence over generic classes.
        evidence_conflicts = np.zeros(scl.shape, dtype=bool)
        evidence_count = np.zeros(scl.shape, dtype=np.uint8)
        for cid, mask in evidence_masks.items():
            evidence_count += mask.astype(np.uint8)
        evidence_conflicts = evidence_count > 1
        for cid, mask in evidence_masks.items():
            labels[mask & (~evidence_conflicts)] = cid
            conf[mask & (~evidence_conflicts)] = 3
        labels[evidence_conflicts] = 255; conf[evidence_conflicts] = 0
        conflict |= evidence_conflicts

        # v2.3: functional evidence from the documented coal-power facility is paired
        # with image-derived built candidates. Only class 11 gets this conservative
        # evidence-supported automatic assignment; point buffers are never burned as labels.
        class11_facility_auto = facility_supported_class11_mask(
            ref, inside, clear, ignore, class11_candidate, evidence_conflicts, OUT_DIR)
        labels[class11_facility_auto] = 11
        conf[class11_facility_auto] = 4  # documented facility + image candidate; not human verified

        label_path = os.path.join(OUT_DIR, "CoalCity40_CN01_Datong_prelabel_v2_3.tif")
        conf_path = os.path.join(OUT_DIR, "confidence.tif")
        write_tif(ref, label_path, labels)
        write_tif(ref, conf_path, conf)

        masks = {
            "candidate_class_0_high_density_built": dense_built,
            "candidate_class_1_low_density_built": sparse_built,
            "candidate_class_2_cropland_review_only": crop,
            "candidate_class_3_tree_dense_vegetation": tree,
            "candidate_class_4_grass_sparse_vegetation": grass,
            "candidate_class_5_strict_bare_ground": bare,
            "candidate_class_5_uncertain_bare_review": bare_uncertain,
            "candidate_class_6_water": water,
            "candidate_class_7_road_review_only": road,
            "candidate_class_8_active_mining_review_only": class8_candidate,
            "candidate_class_9_waste_dump_review_only": class9_candidate,
            "candidate_class_10_subsidence_water_review_only": class10_candidate,
            "candidate_class_11_processing_power_review_only": class11_candidate,
            "evidence_supported_class_11_auto_assignment": class11_facility_auto,
            "candidate_class_12_coal_logistics_review_only": class12_candidate,
            "candidate_documented_facility_context_review_only": facility_context,
            "candidate_vegetation_uncertain": veg_uncertain,
            "candidate_built_uncertain": built_uncertain,
            "candidate_ignore": ignore,
            "candidate_class_conflict": conflict,
            "candidate_removed_small_components": water_small | tree_small | grass_small | bare_small | dense_small | sparse_small | crop_small,
            "candidate_unclassified_clear_review": clear & (labels == 255) & (~ignore),
        }
        for name, mask in masks.items():
            save_mask(ref, name, mask)

        # Per-label area report, 10 m pixel area is 100 m² = 0.0001 km².
        total_inside = int(np.count_nonzero(inside))
        count_rows = []
        for cid in list(range(14)) + [255]:
            n = int(np.count_nonzero((labels == cid) & inside)) if cid != 255 else int(np.count_nonzero((labels == 255) & inside))
            count_rows.append([cid, CLASS_NAMES[cid], n, round(n*0.0001,4),
                               round((n/total_inside*100) if total_inside else 0,3)])
        write_csv(os.path.join(OUT_DIR, "prelabel_counts_v2_3.csv"),
                  ["class_id","class_name","pixel_count","area_km2_estimate","percent_of_CUFR"], count_rows)

        cand_rows = []
        for name, mask in masks.items():
            n = int(np.count_nonzero(mask & inside))
            cand_rows.append([name, n, round(n*0.0001,4),
                              round(n/total_inside*100,3) if total_inside else 0])
        write_csv(os.path.join(OUT_DIR, "candidate_counts_v2_3.csv"),
                  ["candidate_layer","pixel_count","area_km2_estimate","percent_of_CUFR"], cand_rows)

        review_rows = [
            [0,CLASS_NAMES[0],"启发式暂定","NDBI + 局部候选密度；需核验是否建筑连续占主导"],
            [1,CLASS_NAMES[1],"启发式暂定","建筑与植被/庭院混合；需排除农田与裸地"],
            [2,CLASS_NAMES[2],"仅候选","需要规则田块结构/农业用途证据，不由 NDVI 单独确认"],
            [3,CLASS_NAMES[3],"多条件暂定","SCL 植被 + 高 NDVI + 局部连续性；仍需核验树木/高覆盖植被"],
            [4,CLASS_NAMES[4],"多条件暂定","SCL 植被 + 中等 NDVI + 局部连续性；边界和混合像元需复核"],
            [5,CLASS_NAMES[5],"严格规则暂定","仅低 NDVI、低 NDWI、低 NDBI 且 SCL 裸地；其他裸露地表留复核"],
            [6,CLASS_NAMES[6],"多条件暂定","SCL 水体并结合 NDWI；需核验云影/沉陷水体"],
            [7,CLASS_NAMES[7],"仅候选","线性连续性弱代理；仅标注宽度/连续性达标的主要道路，需复核"],
        ]
        for cid, (fn, desc) in EVIDENCE_FILES.items():
            status = "辅助证据矢量已加载并赋类" if cid in evidence_files_used else "仅候选；缺少独立功能证据"
            note = evidence_files_used.get(cid, "如需自动赋类，请提供经过独立核验的 " + fn)
            review_rows.append([cid, desc, status, note])
        review_rows += [
            [8, "已知矿山周边可见采掘空间", "设施调研 + 影像候选；非自动确认", "点位缓冲只用于定位；类别8边界必须从影像识别"],
            [9, "已知矿区附近疑似堆场/排土场", "影像候选；非自动确认", "不得将矿区附近所有裸地赋为类别9，需堆积形态和功能证据"],
            [10, "疑似采煤沉陷水体", "需沉陷历史/空间证据", "水体形状或矿区邻近本身不足以确认类别10"],
            [11, "煤炭加工与电力设施", "证据支持的自动预赋类（置信度4）+边界复核", "大同第二发电厂功能证据 + 250m范围内影像建成候选；不是人工核验，需检查厂界并排除无关道路/绿地"],
            [12, "疑似煤炭物流设施", "设施调研 + 影像候选；非自动确认", "需确认煤场、装车站、输煤带或转运功能"],
            [255,CLASS_NAMES[255],"待复核/Ignore","包含 SCL Ignore、规则冲突、低置信度及未判定区域"],
        ]
        write_csv(os.path.join(OUT_DIR, "review_queue_v2_3.csv"),
                  ["class_id","class_name","status","review_notes"], review_rows)

        conflict_rows = [
            ["generic_candidate_overlap", int(np.count_nonzero(conflict & inside)), "两个或更多通用候选家族重叠；复合标签回退为 255"],
            ["evidence_polygon_overlap", int(np.count_nonzero(evidence_conflicts & inside)), "多个煤炭功能证据多边形重叠；回退为 255，需解决证据冲突"],
            ["uncertain_bare", int(np.count_nonzero(bare_uncertain & inside)), "可能为普通裸地、施工地或煤炭相关裸露地表，未强制定类"],
            ["unclassified_clear_review", int(np.count_nonzero(masks["candidate_unclassified_clear_review"] & inside)), "有效且非 SCL Ignore 像素仍未进入可靠标签；供集中复核，不自动写为其他类别"],
            ["uncertain_vegetation", int(np.count_nonzero(veg_uncertain & inside)), "植被类型无法仅靠当前影像可靠细分"],
            ["small_components_removed", int(np.count_nonzero(masks["candidate_removed_small_components"] & inside)), "小斑块从部分候选类别中移出，供复核；未直接改写原始数据"],
        ]
        write_csv(os.path.join(OUT_DIR, "conflict_report_v2_3.csv"),
                  ["issue","pixel_count","handling"], conflict_rows)

        report = [
            "CoalCity-40 Datong batch pre-annotation v2.3",
            "STATUS: provisional only; not final ground truth",
            "Input: " + INPUT_DIR,
            "CUFR boundary: " + boundary_path,
            "Grid: {} x {}; CUFR pixels={}".format(refinfo["width"], refinfo["height"], total_inside),
            "Scipy connected-component filtering: " + str(HAVE_SCIPY),
            "Minimum component pixels: {}".format(MIN_COMPONENT_PIXELS),
            "Evidence polygons used:",
        ]
        if evidence_files_used:
            report += ["  class {}: {}".format(k,v) for k,v in evidence_files_used.items()]
        else:
            report.append("  Facility survey coordinates from the library were used as candidate context only. No verified facility polygons were supplied by this script run.")
        report += [
            "",
            "Component filter notes:",
            "  water: " + water_msg, "  tree vegetation: " + tree_msg,
            "  grass vegetation: " + grass_msg, "  strict bare: " + bare_msg,
            "  dense built: " + dense_msg, "  sparse built: " + sparse_msg,
            "",
            "Rules/limitations:",
            "- Bare-ground class 5 is strict; ambiguous exposed land remains review candidate.",
            "- Vegetation labels require SCL + NDVI + local neighborhood consistency; ambiguous vegetation remains 255.",
            "- Built-up classes 0/1 are heuristic provisional, not verified building extraction.",
            "- Cropland and roads are candidate-only; spectral data alone cannot establish land use/linear road boundaries robustly.",
            "- v2.3 class 11: documented Datong No.2 Power Plant function evidence is combined with image-derived built candidates in a 250m search window; confidence=4 means evidence-supported automatic prelabel, NOT human-verified.",
            "- Classes 8, 9, 10 and 12 remain review-only unless class-specific independent evidence polygons are supplied; point proximity/spectral appearance alone is insufficient under the annotation spec.",
            "- Facility locator buffers are not directly burned as labels; class 11 only assigns candidate pixels derived from the image inside the bounded search window.",
            "- Class 10 requires documented subsidence spatial/history evidence; water shape alone is insufficient.",
            "- v2.1 conflict detection only uses masks eligible for provisional label assignment; broad bare, crop, road and coal candidate masks do not erase labels.",
            "- Coal candidate rules were narrowed; they are still investigation hints, not automatic coal-function confirmation.",
            "- Class conflicts are set to 255. SCL Ignore classes remain 255.",
            "- Output does not overwrite prior versions. Confidence 4 is automated evidence-supported prelabel only, not human verification."
        ]
        with open(os.path.join(OUT_DIR, "run_report_v2_3.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(report))

        # Load outputs in QGIS; show composite over RGB, leave candidate masks off.
        project = QgsProject.instance()
        output_layers = []
        load_items = [(label_path,"CN01_prelabel_v2_3_provisional"),(conf_path,"CN01_prelabel_v2_3_confidence")]
        load_items += [(os.path.join(MASK_DIR,n+".tif"),n) for n in masks]
        for path, name in load_items:
            for old in list(project.mapLayers().values()):
                if old.name() == name:
                    project.removeMapLayer(old.id())
            lyr = QgsRasterLayer(path, name, "gdal")
            if lyr.isValid():
                project.addMapLayer(lyr); output_layers.append(lyr)

        composite = project.mapLayersByName("CN01_prelabel_v2_3_provisional")
        root = project.layerTreeRoot()
        for lyr in project.mapLayers().values():
            node = root.findLayer(lyr.id())
            if node is None: continue
            if lyr.name() == "CN01_prelabel_v2_3_provisional":
                node.setItemVisibilityChecked(True)
            elif lyr.name() == "CN01_RGB_true_color_B04_B03_B02":
                node.setItemVisibilityChecked(True)
            elif lyr in output_layers:
                node.setItemVisibilityChecked(False)
        if composite:
            lyr = composite[0]
            palette = [
                QgsPalettedRasterRenderer.Class(0,QColor(190,60,60,175),"0 高密度建成区（暂定）"),
                QgsPalettedRasterRenderer.Class(1,QColor(215,135,75,175),"1 低密度建成区（暂定）"),
                QgsPalettedRasterRenderer.Class(3,QColor(25,125,45,190),"3 林木/高覆盖植被（暂定）"),
                QgsPalettedRasterRenderer.Class(4,QColor(135,195,80,175),"4 草地/稀疏植被（暂定）"),
                QgsPalettedRasterRenderer.Class(5,QColor(180,145,100,175),"5 严格裸地（暂定）"),
                QgsPalettedRasterRenderer.Class(6,QColor(0,100,255,210),"6 水体（暂定）"),
                QgsPalettedRasterRenderer.Class(8,QColor(150,0,0,210),"8 活跃采掘区（证据赋类）"),
                QgsPalettedRasterRenderer.Class(9,QColor(190,50,0,210),"9 排土/废弃物堆场（证据赋类）"),
                QgsPalettedRasterRenderer.Class(10,QColor(0,170,230,210),"10 沉陷水体（证据赋类）"),
                QgsPalettedRasterRenderer.Class(11,QColor(200,0,180,210),"11 加工/电力设施（证据支持自动预标）"),
                QgsPalettedRasterRenderer.Class(12,QColor(230,120,0,210),"12 煤炭物流（证据赋类）"),
                QgsPalettedRasterRenderer.Class(255,QColor(0,0,0,0),"255 Ignore/待判读（透明）"),
            ]
            lyr.setRenderer(QgsPalettedRasterRenderer(lyr.dataProvider(),1,palette))
            lyr.triggerRepaint()
        if project.fileName():
            project.write()

        log("v2.3 批量预标注完成。")
        log("输出目录: " + OUT_DIR)
        log("新版标签栅格: " + label_path)
        log("候选图层数: " + str(len(masks)))
        log("独立煤炭证据文件数: " + str(len(evidence_files_used)))
        log("请查看 prelabel_counts_v2_3.csv、candidate_counts_v2_3.csv、review_queue_v2_3.csv、conflict_report_v2_3.csv、run_report_v2_3.txt")
        log("类别11已尝试使用大同第二发电厂功能证据+影像候选自动预赋类（置信度4，仍需边界核验）；类别8/9/10/12缺少类别专属边界证据时仍为候选。")
    finally:
        for k in list(dss.keys()):
            dss[k] = None

try:
    main()
except Exception:
    log(traceback.format_exc())
